import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import socket
import struct
import sys
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class FrameType(Enum):
    DATA = 0x01
    ACK = 0x02
    NACK = 0x03
    PING = 0x04
    PONG = 0x05
    CLOSE = 0x06
    HANDSHAKE = 0x07


MAGIC = b"NFG1"
HEADER_FMT = "!4sBIIH"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_PAYLOAD = 60000


@dataclass
class Frame:
    ftype: FrameType
    seq: int
    ack: int
    payload: bytes = b""
    flags: int = 0

    def encode(self) -> bytes:
        crc = zlib.crc32(self.payload) & 0xFFFFFFFF
        header = struct.pack(HEADER_FMT, MAGIC, self.ftype.value, self.seq,
                             self.ack, len(self.payload))
        return header + self.payload + struct.pack("!I", crc)

    @classmethod
    def decode(cls, raw: bytes) -> "Frame":
        if len(raw) < HEADER_SIZE + 4:
            raise ValueError("frame too short")
        magic, ftype, seq, ack, plen = struct.unpack(HEADER_FMT, raw[:HEADER_SIZE])
        if magic != MAGIC:
            raise ValueError("bad magic")
        if len(raw) < HEADER_SIZE + plen + 4:
            raise ValueError("truncated frame")
        payload = raw[HEADER_SIZE:HEADER_SIZE + plen]
        crc = struct.unpack("!I", raw[HEADER_SIZE + plen:HEADER_SIZE + plen + 4])[0]
        if zlib.crc32(payload) & 0xFFFFFFFF != crc:
            raise ValueError("crc mismatch")
        return cls(ftype=FrameType(ftype), seq=seq, ack=ack, payload=payload)


class Cipher:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("key must be 32 bytes")
        self.key = key

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        out = bytearray()
        counter = 0
        while len(out) < length:
            block = hmac.new(self.key, nonce + struct.pack("!Q", counter),
                             hashlib.sha256).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:length])

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = secrets.token_bytes(16)
        stream = self._keystream(nonce, len(plaintext))
        ct = bytes(a ^ b for a, b in zip(plaintext, stream))
        tag = hmac.new(self.key, nonce + ct, hashlib.sha256).digest()[:16]
        return nonce + ct + tag

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < 32:
            raise ValueError("ciphertext too short")
        nonce, ct, tag = blob[:16], blob[16:-16], blob[-16:]
        expected = hmac.new(self.key, nonce + ct, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            raise ValueError("authentication failed")
        stream = self._keystream(nonce, len(ct))
        return bytes(a ^ b for a, b in zip(ct, stream))


class SlidingWindow:
    def __init__(self, size: int = 64):
        self.size = size
        self.base = 0
        self.next_seq = 0
        self.outstanding: Dict[int, Tuple[Frame, float]] = {}
        self.buffered: Dict[int, Frame] = {}

    def can_send(self) -> bool:
        return self.next_seq < self.base + self.size

    def register(self, frame: Frame) -> int:
        seq = self.next_seq
        frame.seq = seq
        self.outstanding[seq] = (frame, time.monotonic())
        self.next_seq += 1
        return seq

    def ack(self, ack_num: int) -> List[int]:
        acked = []
        for seq in list(self.outstanding.keys()):
            if seq <= ack_num:
                del self.outstanding[seq]
                acked.append(seq)
        while self.base in self.buffered:
            del self.buffered[self.base]
            self.base += 1
        return acked

    def receive(self, frame: Frame) -> Optional[bytes]:
        if frame.seq < self.base:
            return None
        if frame.seq == self.base:
            data = frame.payload
            self.base += 1
            while self.base in self.buffered:
                data += self.buffered.pop(self.base).payload
                self.base += 1
            return data
        self.buffered[frame.seq] = frame
        return None

    def retransmit_due(self, timeout: float) -> List[Frame]:
        now = time.monotonic()
        due = []
        for seq, (frame, ts) in list(self.outstanding.items()):
            if now - ts > timeout:
                due.append(frame)
                self.outstanding[seq] = (frame, now)
        return due

    def stats(self) -> Dict[str, int]:
        return {
            "base": self.base,
            "next_seq": self.next_seq,
            "outstanding": len(self.outstanding),
            "buffered": len(self.buffered),
        }


class ReliableChannel:
    def __init__(self, sock: socket.socket, key: bytes, window: int = 64,
                 retransmit_timeout: float = 0.5):
        self.sock = sock
        self.cipher = Cipher(key)
        self.window = SlidingWindow(window)
        self.retransmit_timeout = retransmit_timeout
        self.running = False
        self.send_queue: asyncio.Queue = asyncio.Queue()
        self.recv_queue: asyncio.Queue = asyncio.Queue()

    async def start(self) -> None:
        self.running = True
        asyncio.create_task(self._sender())
        asyncio.create_task(self._receiver())
        asyncio.create_task(self._retransmitter())

    async def stop(self) -> None:
        self.running = False
        await self.send_frame(Frame(FrameType.CLOSE, 0, 0))

    async def send_frame(self, frame: Frame) -> None:
        await self.send_queue.put(frame)

    async def send_data(self, data: bytes) -> None:
        for i in range(0, len(data), MAX_PAYLOAD):
            chunk = data[i:i + MAX_PAYLOAD]
            await self.send_frame(Frame(FrameType.DATA, 0, 0, chunk))

    async def receive(self, timeout: Optional[float] = None) -> Optional[bytes]:
        try:
            return await asyncio.wait_for(self.recv_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    async def _sender(self) -> None:
        while self.running:
            frame = await self.send_queue.get()
            while not self.window.can_send() and self.running:
                await asyncio.sleep(0.001)
            self.window.register(frame)
            await self._transmit(frame)

    async def _transmit(self, frame: Frame) -> None:
        loop = asyncio.get_event_loop()
        encrypted = self.cipher.encrypt(frame.encode())
        await loop.sock_sendall(self.sock, encrypted)

    async def _receiver(self) -> None:
        loop = asyncio.get_event_loop()
        buffer = b""
        while self.running:
            try:
                chunk = await asyncio.wait_for(loop.sock_recv(self.sock, 65536), 1.0)
                if not chunk:
                    break
                buffer += chunk
                while len(buffer) >= 4:
                    try:
                        frame = Frame.decode(self.cipher.decrypt(buffer))
                    except (ValueError, struct.error):
                        buffer = buffer[1:]
                        continue
                    consumed = self._frame_size(buffer)
                    if consumed == 0:
                        break
                    buffer = buffer[consumed:]
                    self._handle_frame(frame)
            except asyncio.TimeoutError:
                continue
            except (OSError, ConnectionError):
                break

    def _frame_size(self, raw: bytes) -> int:
        try:
            decrypted = self.cipher.decrypt(raw)
            if len(decrypted) < HEADER_SIZE:
                return 0
            _, _, _, _, plen = struct.unpack(HEADER_FMT, decrypted[:HEADER_SIZE])
            return HEADER_SIZE + plen + 4 + 32
        except ValueError:
            return 0

    def _handle_frame(self, frame: Frame) -> None:
        if frame.ftype == FrameType.DATA:
            data = self.window.receive(frame)
            if data is not None:
                self.recv_queue.put_nowait(data)
            ack_frame = Frame(FrameType.ACK, 0, self.window.base - 1)
            asyncio.create_task(self.send_frame(ack_frame))
        elif frame.ftype == FrameType.ACK:
            self.window.ack(frame.ack)
        elif frame.ftype == FrameType.CLOSE:
            self.running = False

    async def _retransmitter(self) -> None:
        while self.running:
            await asyncio.sleep(self.retransmit_timeout / 2)
            for frame in self.window.retransmit_due(self.retransmit_timeout):
                await self._transmit(frame)


class Handshake:
    @staticmethod
    def derive_key(shared: bytes, client_nonce: bytes, server_nonce: bytes) -> bytes:
        return hashlib.sha256(shared + client_nonce + server_nonce + b"netforge").digest()

    @staticmethod
    def client_hello() -> Tuple[bytes, bytes]:
        nonce = secrets.token_bytes(32)
        shared = secrets.token_bytes(32)
        return nonce, shared

    @staticmethod
    def server_hello(client_nonce: bytes, server_shared: bytes) -> Tuple[bytes, bytes]:
        nonce = secrets.token_bytes(32)
        return nonce, Handshake.derive_key(server_shared, client_nonce, nonce)


class FileTransfer:
    def __init__(self, channel: ReliableChannel):
        self.channel = channel
        self.received: Dict[str, bytearray] = {}
        self.manifests: Dict[str, Dict[str, Any]] = {}

    async def send_file(self, path: str) -> None:
        with open(path, "rb") as f:
            data = f.read()
        manifest = {
            "name": os.path.basename(path),
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        header = json.dumps({"type": "manifest", **manifest}).encode()
        await self.channel.send_data(b"M" + struct.pack("!I", len(header)) + header)
        for i in range(0, len(data), MAX_PAYLOAD - 64):
            chunk = data[i:i + MAX_PAYLOAD - 64]
            await self.channel.send_data(b"D" + struct.pack("!I", i) + chunk)

    async def handle_incoming(self) -> None:
        while True:
            data = await self.channel.receive()
            if data is None:
                continue
            kind = data[:1]
            if kind == b"M":
                length = struct.unpack("!I", data[1:5])[0]
                manifest = json.loads(data[5:5 + length])
                self.manifests[manifest["name"]] = manifest
                self.received[manifest["name"]] = bytearray(manifest["size"])
            elif kind == b"D":
                offset = struct.unpack("!I", data[1:5])[0]
                chunk = data[5:]
                for name, manifest in self.manifests.items():
                    if offset < manifest["size"]:
                        end = min(offset + len(chunk), manifest["size"])
                        self.received[name][offset:end] = chunk[:end - offset]
                        break

    def verify(self, name: str) -> bool:
        if name not in self.received or name not in self.manifests:
            return False
        data = bytes(self.received[name])
        return hashlib.sha256(data).hexdigest() == self.manifests[name]["sha256"]


class PeerRegistry:
    def __init__(self):
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, Dict[str, float]] = {}

    def register(self, peer_id: str, addr: Tuple[str, int]) -> None:
        self.peers[peer_id] = {
            "addr": addr,
            "connected": time.monotonic(),
            "last_seen": time.monotonic(),
        }
        self.metrics[peer_id] = {"sent": 0, "received": 0, "rtt": 0.0}

    def touch(self, peer_id: str) -> None:
        if peer_id in self.peers:
            self.peers[peer_id]["last_seen"] = time.monotonic()

    def record(self, peer_id: str, direction: str, size: int) -> None:
        if peer_id in self.metrics:
            self.metrics[peer_id][direction] += size

    def update_rtt(self, peer_id: str, rtt: float) -> None:
        if peer_id in self.metrics:
            old = self.metrics[peer_id]["rtt"]
            self.metrics[peer_id]["rtt"] = old * 0.8 + rtt * 0.2 if old else rtt

    def snapshot(self) -> Dict[str, Any]:
        return {
            "peers": dict(self.peers),
            "metrics": dict(self.metrics),
            "count": len(self.peers),
        }


class ChunkStore:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, digest: str) -> str:
        return os.path.join(self.root, digest[:2], digest)

    def put(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        path = self._path(digest)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(data)
        return digest

    def get(self, digest: str) -> Optional[bytes]:
        path = self._path(digest)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def has(self, digest: str) -> bool:
        return os.path.exists(self._path(digest))

    def stats(self) -> Dict[str, int]:
        count = 0
        size = 0
        for dirpath, _, files in os.walk(self.root):
            for name in files:
                count += 1
                size += os.path.getsize(os.path.join(dirpath, name))
        return {"chunks": count, "bytes": size}


class Demo:
    @staticmethod
    def run_cipher_demo() -> Dict[str, Any]:
        key = secrets.token_bytes(32)
        cipher = Cipher(key)
        plaintext = b"netforge secure transport demo " * 100
        blob = cipher.encrypt(plaintext)
        recovered = cipher.decrypt(blob)
        tampered = bytearray(blob)
        tampered[40] ^= 0xFF
        tamper_detected = False
        try:
            cipher.decrypt(bytes(tampered))
        except ValueError:
            tamper_detected = True
        return {
            "roundtrip_ok": recovered == plaintext,
            "ciphertext_size": len(blob),
            "tamper_detected": tamper_detected,
        }

    @staticmethod
    def run_window_demo() -> Dict[str, Any]:
        w = SlidingWindow(size=8)
        for i in range(8):
            w.register(Frame(FrameType.DATA, 0, 0, b"x"))
        full = not w.can_send()
        w.ack(4)
        after_ack = w.stats()
        received = []
        for seq in (0, 2, 1, 3):
            f = Frame(FrameType.DATA, seq, 0, bytes([seq]))
            data = w.receive(f)
            if data:
                received.append(data)
        return {
            "window_full": full,
            "after_ack": after_ack,
            "delivered": received,
            "final": w.stats(),
        }

    @staticmethod
    def run_handshake_demo() -> Dict[str, Any]:
        client_nonce, client_shared = Handshake.client_hello()
        server_nonce, key_server = Handshake.server_hello(client_nonce, client_shared)
        key_client = Handshake.derive_key(client_shared, client_nonce, server_nonce)
        return {
            "keys_match": key_client == key_server,
            "key_len": len(key_client),
        }

    @staticmethod
    def run_frame_demo() -> Dict[str, Any]:
        original = Frame(FrameType.DATA, 42, 17, b"payload bytes here")
        encoded = original.encode()
        decoded = Frame.decode(encoded)
        corrupt = bytearray(encoded)
        corrupt[-1] ^= 0xFF
        corrupt_rejected = False
        try:
            Frame.decode(bytes(corrupt))
        except ValueError:
            corrupt_rejected = True
        return {
            "roundtrip_ok": decoded.payload == original.payload and
                            decoded.seq == original.seq,
            "encoded_size": len(encoded),
            "corrupt_rejected": corrupt_rejected,
        }

    @staticmethod
    def run_chunk_store_demo() -> Dict[str, Any]:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            store = ChunkStore(tmp)
            d1 = store.put(b"alpha")
            d2 = store.put(b"beta")
            d3 = store.put(b"alpha")
            return {
                "dedup": d1 == d3,
                "retrieved": store.get(d1) == b"alpha",
                "stats": store.stats(),
            }


def render_report(name: str, report: Dict[str, Any]) -> str:
    lines = ["=" * 64, f"  NETFORGE :: {name.upper()}", "=" * 64]
    for k, v in report.items():
        lines.append(f"  {k}: {v}")
    lines.append("=" * 64)
    return "\n".join(lines)


async def simulate_transfer() -> Dict[str, Any]:
    a, b = socket.socketpair()
    a.setblocking(False)
    b.setblocking(False)
    key = secrets.token_bytes(32)
    sender = ReliableChannel(a, key)
    receiver = ReliableChannel(b, key)
    await sender.start()
    await receiver.start()

    payload = os.urandom(200_000)
    transfer = FileTransfer(sender)
    recv_task = asyncio.create_task(receiver.receive())
    await sender.send_data(payload)
    received = b""
    deadline = time.monotonic() + 5.0
    while len(received) < len(payload) and time.monotonic() < deadline:
        chunk = await receiver.receive(timeout=0.5)
        if chunk:
            received += chunk

    await sender.stop()
    await receiver.stop()
    recv_task.cancel()
    a.close()
    b.close()

    return {
        "bytes_sent": len(payload),
        "bytes_received": len(received),
        "intact": hashlib.sha256(payload).hexdigest() ==
                  hashlib.sha256(received).hexdigest(),
        "sender_stats": sender.window.stats(),
        "receiver_stats": receiver.window.stats(),
    }


def main() -> None:
    print(render_report("frame codec", Demo.run_frame_demo()))
    print(render_report("cipher", Demo.run_cipher_demo()))
    print(render_report("handshake", Demo.run_handshake_demo()))
    print(render_report("sliding window", Demo.run_window_demo()))
    print(render_report("chunk store", Demo.run_chunk_store_demo()))
    transfer = asyncio.run(simulate_transfer())
    print(render_report("reliable transfer", transfer))

    registry = PeerRegistry()
    registry.register("peer-a", ("127.0.0.1", 9001))
    registry.record("peer-a", "sent", 2048)
    registry.record("peer-a", "received", 1024)
    registry.update_rtt("peer-a", 12.5)
    print(render_report("peer registry", registry.snapshot()))


if __name__ == "__main__":
    main()