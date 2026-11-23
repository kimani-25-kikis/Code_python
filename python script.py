import asyncio
import aiohttp
import hashlib
import hmac
import json
import os
import random
import secrets
import socket
import ssl
import string
import struct
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Packet:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    payload: bytes
    timestamp: float = field(default_factory=time.time)
    flags: str = ""


class PacketCraft:
    @staticmethod
    def checksum(data: bytes) -> int:
        if len(data) % 2:
            data += b"\x00"
        total = 0
        for i in range(0, len(data), 2):
            total += (data[i] << 8) + data[i + 1]
        total = (total >> 16) + (total & 0xFFFF)
        total += total >> 16
        return ~total & 0xFFFF

    @staticmethod
    def ip_header(src: str, dst: str, proto: int, payload_len: int) -> bytes:
        version_ihl = 0x45
        tos = 0
        total_len = 20 + payload_len
        ident = random.randint(0, 65535)
        flags_frag = 0x4000
        ttl = 64
        src_bytes = socket.inet_aton(src)
        dst_bytes = socket.inet_aton(dst)
        header = struct.pack("!BBHHHBBH4s4s", version_ihl, tos, total_len,
                             ident, flags_frag, ttl, proto, 0, src_bytes, dst_bytes)
        chk = PacketCraft.checksum(header)
        header = struct.pack("!BBHHHBBH4s4s", version_ihl, tos, total_len,
                             ident, flags_frag, ttl, proto, chk, src_bytes, dst_bytes)
        return header

    @staticmethod
    def tcp_header(src_port: int, dst_port: int, seq: int, ack: int,
                   flags: int, window: int = 65535) -> bytes:
        offset_res = 0x50
        header = struct.pack("!HHIIBBHHH", src_port, dst_port, seq, ack,
                             offset_res, flags, window, 0, 0)
        return header

    @staticmethod
    def udp_header(src_port: int, dst_port: int, length: int) -> bytes:
        return struct.pack("!HHHH", src_port, dst_port, length, 0)

    @staticmethod
    def syn_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int) -> bytes:
        tcp = PacketCraft.tcp_header(src_port, dst_port, random.randint(0, 2**32 - 1),
                                     0, 0x02)
        ip = PacketCraft.ip_header(src_ip, dst_ip, 6, len(tcp))
        return ip + tcp

    @staticmethod
    def udp_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                   payload: bytes) -> bytes:
        udp = PacketCraft.udp_header(src_port, dst_port, 8 + len(payload))
        ip = PacketCraft.ip_header(src_ip, dst_ip, 17, len(udp) + len(payload))
        return ip + udp + payload


class RawSocket:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout

    def __enter__(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            self.sock.settimeout(self.timeout)
        except PermissionError:
            self.sock = None
        return self

    def __exit__(self, *args):
        if self.sock:
            self.sock.close()

    def send(self, packet: bytes, dst: str) -> bool:
        if not self.sock:
            return False
        try:
            self.sock.sendto(packet, (dst, 0))
            return True
        except OSError:
            return False


class SYNScanner:
    def __init__(self, target: str, ports: List[int], timeout: float = 1.5,
                 concurrency: int = 200):
        self.target = socket.gethostbyname(target)
        self.ports = ports
        self.timeout = timeout
        self.concurrency = concurrency
        self.results: Dict[int, str] = {}
        self.semaphore = asyncio.Semaphore(concurrency)

    async def probe(self, port: int) -> Tuple[int, str]:
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._probe_sync, port)

    def _probe_sync(self, port: int) -> Tuple[int, str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            start = time.perf_counter()
            result = s.connect_ex((self.target, port))
            elapsed = time.perf_counter() - start
            s.close()
            if result == 0:
                return port, "open"
            elif result in (111, 61):
                return port, "closed"
            else:
                return port, "filtered"
        except socket.timeout:
            return port, "filtered"
        except OSError:
            return port, "error"

    async def run(self) -> Dict[int, str]:
        tasks = [self.probe(p) for p in self.ports]
        for coro in asyncio.as_completed(tasks):
            port, status = await coro
            self.results[port] = status
        return dict(sorted(self.results.items()))


class BannerGrabber:
    PROBES = {
        21: b"",
        22: b"",
        25: b"EHLO probe\r\n",
        80: b"HEAD / HTTP/1.0\r\nHost: target\r\n\r\n",
        110: b"",
        143: b"",
        443: b"",
        3306: b"",
        5432: b"",
        6379: b"PING\r\n",
        8080: b"HEAD / HTTP/1.0\r\n\r\n",
    }

    def __init__(self, target: str, timeout: float = 3.0):
        self.target = target
        self.timeout = timeout

    async def grab(self, port: int) -> Optional[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._grab_sync, port)

    def _grab_sync(self, port: int) -> Optional[str]:
        try:
            with socket.create_connection((self.target, port), timeout=self.timeout) as s:
                s.settimeout(self.timeout)
                if port in self.PROBES and self.PROBES[port]:
                    s.sendall(self.PROBES[port])
                try:
                    data = s.recv(4096)
                    return data.decode("utf-8", errors="replace").strip()[:512] or None
                except socket.timeout:
                    return None
        except (socket.error, OSError):
            return None

    async def grab_many(self, ports: List[int]) -> Dict[int, Optional[str]]:
        tasks = {p: asyncio.create_task(self.grab(p)) for p in ports}
        results = {}
        for p, task in tasks.items():
            try:
                results[p] = await task
            except Exception:
                results[p] = None
        return results


class PassiveOSFingerprint:
    TTL_MAP = {
        range(1, 65): "Linux/Unix",
        range(65, 129): "Windows",
        range(129, 200): "Cisco/Network",
    }
    WINDOW_MAP = {
        5840: "Linux 2.4",
        65535: "Windows XP/2003",
        8192: "Windows 7/2008",
        14600: "Windows 10/2019",
        29200: "Linux 4.x/5.x",
    }

    @classmethod
    def from_ttl(cls, ttl: int) -> str:
        for rng, os_name in cls.TTL_MAP.items():
            if ttl in rng:
                return os_name
        return "Unknown"

    @classmethod
    def from_window(cls, window: int) -> str:
        return cls.WINDOW_MAP.get(window, "Unknown")


class Traceroute:
    def __init__(self, target: str, max_hops: int = 30, timeout: float = 2.0):
        self.target = socket.gethostbyname(target)
        self.max_hops = max_hops
        self.timeout = timeout

    def trace(self) -> List[Tuple[int, str, float]]:
        hops = []
        for ttl in range(1, self.max_hops + 1):
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            probe.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
            probe.settimeout(self.timeout)
            start = time.perf_counter()
            try:
                probe.sendto(b"\x00" * 32, (self.target, 33434 + ttl))
            except OSError:
                probe.close()
                break
            icmp = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            icmp.settimeout(self.timeout)
            try:
                _, addr = icmp.recvfrom(512)
                elapsed = (time.perf_counter() - start) * 1000
                hops.append((ttl, addr[0], elapsed))
                if addr[0] == self.target:
                    icmp.close()
                    probe.close()
                    break
            except socket.timeout:
                hops.append((ttl, "*", -1.0))
            finally:
                icmp.close()
                probe.close()
        return hops


class HashVault:
    def __init__(self):
        self.salt = secrets.token_bytes(32)
        self.records: Dict[str, Dict[str, Any]] = {}
        self.key = secrets.token_bytes(32)

    def _hash(self, data: str) -> str:
        return hashlib.sha256(self.salt + data.encode()).hexdigest()

    def _hmac(self, data: str) -> str:
        return hmac.new(self.key, data.encode(), hashlib.sha256).hexdigest()

    def add(self, identifier: str, payload: Dict[str, Any]) -> None:
        record = {
            "id_hash": self._hash(identifier),
            "integrity": self._hmac(json.dumps(payload, sort_keys=True)),
            "payload": payload,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        self.records[record["id_hash"]] = record

    def verify(self, identifier: str) -> bool:
        rec = self.records.get(self._hash(identifier))
        if not rec:
            return False
        expected = self._hmac(json.dumps(rec["payload"], sort_keys=True))
        return hmac.compare_digest(expected, rec["integrity"])


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, amount: int = 1) -> bool:
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    async def wait(self, amount: int = 1) -> None:
        while not self.consume(amount):
            await asyncio.sleep(0.01)


class RingBuffer:
    def __init__(self, size: int):
        self.size = size
        self.buffer: List[Any] = []
        self.index = 0

    def push(self, item: Any) -> None:
        if len(self.buffer) < self.size:
            self.buffer.append(item)
        else:
            self.buffer[self.index] = item
            self.index = (self.index + 1) % self.size

    def snapshot(self) -> List[Any]:
        return list(self.buffer)


class ServiceFingerprint:
    SIGNATURES = {
        "ssh": [b"SSH-2.0-", b"SSH-1."],
        "http": [b"HTTP/1.", b"HTTP/2"],
        "ftp": [b"220", b"FTP"],
        "smtp": [b"220", b"SMTP", b"ESMTP"],
        "mysql": [b"mysql_native_password", b"5.7.", b"8.0."],
        "redis": [b"REDIS", b"+PONG"],
        "postgresql": [b"PostgreSQL", b"FATAL"],
        "mongodb": [b"MongoDB", b"ismaster"],
        "rdp": [b"\x03\x00\x00"],
        "smtps": [b"220"],
        "imap": [b"* OK"],
        "pop3": [b"+OK"],
    }

    @classmethod
    def identify(cls, port: int, banner: Optional[str]) -> str:
        if not banner:
            return "unknown"
        raw = banner.encode("utf-8", errors="replace")
        for service, sigs in cls.SIGNATURES.items():
            for sig in sigs:
                if sig in raw:
                    return service
        return "unknown"


class AsyncOrchestrator:
    def __init__(self, target: str):
        self.target = target
        self.ip = socket.gethostbyname(target)
        self.rate_limiter = TokenBucket(capacity=500, refill_rate=1000.0)
        self.history = RingBuffer(1000)
        self.vault = HashVault()
        self.report: Dict[str, Any] = {
            "target": target,
            "ip": self.ip,
            "started": datetime.now(timezone.utc).isoformat(),
            "phases": {},
        }

    async def phase_scan(self, ports: List[int]) -> Dict[int, str]:
        scanner = SYNScanner(self.target, ports, concurrency=200)
        results = await scanner.run()
        self.report["phases"]["port_scan"] = {
            "total": len(results),
            "open": [p for p, s in results.items() if s == "open"],
            "filtered": [p for p, s in results.items() if s == "filtered"],
        }
        self.history.push({"phase": "scan", "results": results})
        return results

    async def phase_banner(self, ports: List[int]) -> Dict[int, Optional[str]]:
        grabber = BannerGrabber(self.target)
        banners = await grabber.grab_many(ports)
        self.report["phases"]["banners"] = {
            str(p): {"banner": b[:200] if b else None,
                     "service": ServiceFingerprint.identify(p, b)}
            for p, b in banners.items()
        }
        self.history.push({"phase": "banner", "results": banners})
        return banners

    async def phase_ratelimit(self, count: int) -> List[float]:
        timestamps = []
        for _ in range(count):
            await self.rate_limiter.wait()
            timestamps.append(time.monotonic())
        gaps = [round((timestamps[i + 1] - timestamps[i]) * 1000, 2)
                for i in range(len(timestamps) - 1)]
        self.report["phases"]["ratelimit"] = {
            "requests": count,
            "avg_gap_ms": round(sum(gaps) / len(gaps), 2) if gaps else 0.0,
        }
        return gaps

    def phase_traceroute(self) -> List[Tuple[int, str, float]]:
        tracer = Traceroute(self.target)
        hops = tracer.trace()
        self.report["phases"]["traceroute"] = [
            {"hop": h, "ip": ip, "rtt_ms": round(rtt, 2)} for h, ip, rtt in hops
        ]
        self.history.push({"phase": "traceroute", "hops": hops})
        return hops

    def phase_vault(self) -> bool:
        self.vault.add("scan_record_1", {"target": self.target, "scan": "port"})
        self.vault.add("scan_record_2", {"target": self.target, "scan": "banner"})
        ok1 = self.vault.verify("scan_record_1")
        ok2 = self.vault.verify("scan_record_2")
        tampered = self.vault.records.get(list(self.vault.records)[0])
        if tampered:
            tampered["payload"]["scan"] = "tampered"
            ok3 = self.vault.verify("scan_record_1")
        else:
            ok3 = True
        self.report["phases"]["integrity"] = {
            "valid": ok1 and ok2,
            "tamper_detected": not ok3,
        }
        return ok1 and ok2 and not ok3

    def finalize(self) -> Dict[str, Any]:
        self.report["finished"] = datetime.now(timezone.utc).isoformat()
        self.report["history_size"] = len(self.history.snapshot())
        return self.report


def render(report: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 64)
    lines.append(f"  TARGET  {report['target']}  ({report['ip']})")
    lines.append("=" * 64)
    for phase, data in report.get("phases", {}).items():
        lines.append(f"\n[{phase.upper()}]")
        if isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"  {k}: {v}")
        elif isinstance(data, list):
            for item in data:
                lines.append(f"  {item}")
    lines.append("\n" + "=" * 64)
    return "\n".join(lines)


async def main(target: str, ports: List[int]) -> None:
    orchestrator = AsyncOrchestrator(target)

    scan = await orchestrator.phase_scan(ports)

    open_ports = [p for p, s in scan.items() if s == "open"]

    if open_ports:
        await orchestrator.phase_banner(open_ports)

    await orchestrator.phase_ratelimit(50)

    orchestrator.phase_traceroute()

    orchestrator.phase_vault()

    report = orchestrator.finalize()

    print(render(report))


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port_spec = sys.argv[2] if len(sys.argv) > 2 else "1-1024"
    if "-" in port_spec:
        a, b = port_spec.split("-")
        port_list = list(range(int(a), int(b) + 1))
    else:
        port_list = [int(p) for p in port_spec.split(",")]
    asyncio.run(main(target, port_list))