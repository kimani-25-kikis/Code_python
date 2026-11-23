import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class KDF:
    @staticmethod
    def pbkdf2(password: str, salt: bytes, iterations: int = 600_000,
               length: int = 32) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt,
                                   iterations, length)

    @staticmethod
    def scrypt(password: str, salt: bytes, n: int = 2**15, r: int = 8,
               p: int = 1, length: int = 32) -> bytes:
        return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p,
                              dklen=length)

    @staticmethod
    def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
        prk = hmac.new(salt, ikm, hashlib.sha256).digest()
        out = b""
        t = b""
        i = 1
        while len(out) < length:
            t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
            out += t
            i += 1
        return out[:length]


class AEAD:
    def __init__(self, key: bytes):
        if len(key) < 16:
            raise ValueError("key too short")
        self.key = key

    def _expand(self, nonce: bytes) -> Tuple[bytes, bytes]:
        enc_key = KDF.hkdf(self.key, nonce, b"aead-encrypt", 32)
        mac_key = KDF.hkdf(self.key, nonce, b"aead-mac", 32)
        return enc_key, mac_key

    def _keystream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        out = b""
        counter = 0
        while len(out) < length:
            out += hmac.new(key, nonce + struct.pack("!Q", counter),
                            hashlib.sha256).digest()
            counter += 1
        return out[:length]

    def seal(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        nonce = secrets.token_bytes(16)
        enc_key, mac_key = self._expand(nonce)
        stream = self._keystream(enc_key, nonce, len(plaintext))
        ct = bytes(a ^ b for a, b in zip(plaintext, stream))
        tag = hmac.new(mac_key, nonce + aad + ct, hashlib.sha256).digest()
        return nonce + tag + ct

    def open(self, blob: bytes, aad: bytes = b"") -> bytes:
        if len(blob) < 48:
            raise ValueError("blob too short")
        nonce, tag, ct = blob[:16], blob[16:48], blob[48:]
        enc_key, mac_key = self._expand(nonce)
        expected = hmac.new(mac_key, nonce + aad + ct, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("authentication failed")
        stream = self._keystream(enc_key, nonce, len(ct))
        return bytes(a ^ b for a, b in zip(ct, stream))


class Shamir:
    PRIME = 2**521 - 1

    @classmethod
    def split(cls, secret: int, n: int, k: int) -> List[Tuple[int, int]]:
        if k > n:
            raise ValueError("k must be <= n")
        coeffs = [secret] + [secrets.randbelow(cls.PRIME) for _ in range(k - 1)]
        shares = []
        for x in range(1, n + 1):
            y = 0
            for c in reversed(coeffs):
                y = (y * x + c) % cls.PRIME
            shares.append((x, y))
        return shares

    @classmethod
    def combine(cls, shares: List[Tuple[int, int]]) -> int:
        total = 0
        for i, (xi, yi) in enumerate(shares):
            num = 1
            den = 1
            for j, (xj, _) in enumerate(shares):
                if i == j:
                    continue
                num = (num * -xj) % cls.PRIME
                den = (den * (xi - xj)) % cls.PRIME
            total = (total + yi * num * pow(den, -1, cls.PRIME)) % cls.PRIME
        return total


class Keyring:
    def __init__(self):
        self.keys: Dict[str, Dict[str, Any]] = {}
        self.audit: List[Dict[str, Any]] = []

    def _log(self, action: str, key_id: str, **extra: Any) -> None:
        self.audit.append({
            "action": action,
            "key_id": key_id,
            "at": datetime.now(timezone.utc).isoformat(),
            **extra,
        })

    def create(self, key_id: str, purpose: str, ttl: Optional[float] = None,
               metadata: Optional[Dict[str, Any]] = None) -> bytes:
        key = secrets.token_bytes(32)
        created = time.monotonic()
        self.keys[key_id] = {
            "material": key,
            "purpose": purpose,
            "created": created,
            "expires": created + ttl if ttl else None,
            "metadata": metadata or {},
            "revoked": False,
        }
        self._log("create", key_id, purpose=purpose)
        return key

    def get(self, key_id: str) -> bytes:
        entry = self.keys.get(key_id)
        if not entry:
            raise KeyError(key_id)
        if entry["revoked"]:
            raise PermissionError("key revoked")
        if entry["expires"] and time.monotonic() > entry["expires"]:
            raise PermissionError("key expired")
        return entry["material"]

    def rotate(self, key_id: str) -> bytes:
        entry = self.keys[key_id]
        entry["material"] = secrets.token_bytes(32)
        entry["created"] = time.monotonic()
        self._log("rotate", key_id)
        return entry["material"]

    def revoke(self, key_id: str) -> None:
        if key_id in self.keys:
            self.keys[key_id]["revoked"] = True
            self._log("revoke", key_id)

    def list_keys(self) -> List[str]:
        return list(self.keys.keys())


class VaultEntry:
    def __init__(self, name: str, ciphertext: bytes, nonce_id: bytes,
                 tags: List[str], created: str):
        self.name = name
        self.ciphertext = ciphertext
        self.nonce_id = nonce_id
        self.tags = tags
        self.created = created

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "nonce_id": base64.b64encode(self.nonce_id).decode(),
            "tags": self.tags,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VaultEntry":
        return cls(
            name=d["name"],
            ciphertext=base64.b64decode(d["ciphertext"]),
            nonce_id=base64.b64decode(d["nonce_id"]),
            tags=d.get("tags", []),
            created=d["created"],
        )


class Vault:
    def __init__(self, master_password: str, path: str = "vault.bin"):
        self.path = path
        self.keyring = Keyring()
        self.entries: Dict[str, VaultEntry] = {}
        self.master_salt = secrets.token_bytes(32)
        self.master_key = KDF.scrypt(master_password, self.master_salt,
                                     n=2**14, length=32)
        self.integrity_key = KDF.hkdf(self.master_key, self.master_salt,
                                      b"integrity", 32)
        self.data_key_id = "primary"
        self.keyring.create(self.data_key_id, "data")
        self._audit_chain: List[Tuple[bytes, bytes]] = []

    def _audit_entry(self, message: bytes) -> bytes:
        prev = self._audit_chain[-1][1] if self._audit_chain else b"\x00" * 32
        h = hmac.new(self.integrity_key, prev + message, hashlib.sha256).digest()
        self._audit_chain.append((message, h))
        return h

    def verify_audit(self) -> bool:
        prev = b"\x00" * 32
        for message, h in self._audit_chain:
            expected = hmac.new(self.integrity_key, prev + message,
                                hashlib.sha256).digest()
            if not hmac.compare_digest(h, expected):
                return False
            prev = h
        return True

    def put(self, name: str, plaintext: bytes, tags: Optional[List[str]] = None
            ) -> None:
        key = self.keyring.get(self.data_key_id)
        aead = AEAD(key)
        aad = name.encode() + b"|" + b",".join(t.encode() for t in (tags or []))
        ciphertext = aead.seal(plaintext, aad)
        nonce_id = hashlib.sha256(ciphertext[:16]).digest()[:16]
        entry = VaultEntry(name, ciphertext, nonce_id, tags or [],
                           datetime.now(timezone.utc).isoformat())
        self.entries[name] = entry
        self._audit_entry(b"put:" + name.encode())

    def get(self, name: str) -> Optional[bytes]:
        entry = self.entries.get(name)
        if not entry:
            return None
        key = self.keyring.get(self.data_key_id)
        aead = AEAD(key)
        aad = name.encode() + b"|" + b",".join(t.encode() for t in entry.tags)
        return aead.open(entry.ciphertext, aad)

    def delete(self, name: str) -> bool:
        if name in self.entries:
            del self.entries[name]
            self._audit_entry(b"del:" + name.encode())
            return True
        return False

    def search(self, tag: str) -> List[str]:
        return [name for name, e in self.entries.items() if tag in e.tags]

    def save(self) -> None:
        payload = json.dumps({
            "entries": {n: e.to_dict() for n, e in self.entries.items()},
            "audit": [(base64.b64encode(m).decode(), base64.b64encode(h).decode())
                     for m, h in self._audit_chain],
        }).encode()
        aead = AEAD(self.master_key)
        blob = self.master_salt + aead.seal(payload, b"vault-root")
        with open(self.path, "wb") as f:
            f.write(blob)

    def load(self, master_password: str) -> bool:
        if not os.path.exists(self.path):
            return False
        with open(self.path, "rb") as f:
            blob = f.read()
        salt = blob[:32]
        candidate = KDF.scrypt(master_password, salt, n=2**14, length=32)
        try:
            aead = AEAD(candidate)
            payload = aead.open(blob[32:], b"vault-root")
        except ValueError:
            return False
        data = json.loads(payload)
        self.master_salt = salt
        self.master_key = candidate
        self.integrity_key = KDF.hkdf(candidate, salt, b"integrity", 32)
        self.entries = {n: VaultEntry.from_dict(d) for n, d in data["entries"].items()}
        self._audit_chain = [
            (base64.b64decode(m), base64.b64decode(h))
            for m, h in data.get("audit", [])
        ]
        return True


class SecretSharing:
    @staticmethod
    def split_text(text: str, n: int, k: int) -> List[Dict[str, Any]]:
        data = text.encode()
        shares_by_byte = [Shamir.split(b, n, k) for b in data]
        result = []
        for i in range(n):
            share = bytes(shares_by_byte[j][i][1] % 256 for j in range(len(data)))
            result.append({"x": i + 1, "data": base64.b64encode(share).decode()})
        return result

    @staticmethod
    def combine_text(shares: List[Dict[str, Any]]) -> str:
        n_bytes = len(base64.b64decode(shares[0]["data"]))
        out = bytearray()
        for b in range(n_bytes):
            points = []
            for s in shares:
                data = base64.b64decode(s["data"])
                points.append((s["x"], data[b]))
            out.append(Shamir.combine(points) % 256)
        return out.decode()


class PasswordAuditor:
    COMMON = {
        "password", "123456", "qwerty", "admin", "letmein", "welcome",
        "monkey", "dragon", "master", "sunshine", "princess", "football",
    }

    @classmethod
    def entropy(cls, password: str) -> float:
        import math
        pool = 0
        if any(c.islower() for c in password):
            pool += 26
        if any(c.isupper() for c in password):
            pool += 26
        if any(c.isdigit() for c in password):
            pool += 10
        if any(not c.isalnum() for c in password):
            pool += 32
        if pool == 0:
            return 0.0
        return len(password) * math.log2(pool)

    @classmethod
    def audit(cls, password: str) -> Dict[str, Any]:
        score = 0
        issues = []
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            issues.append("too short")
        if any(c.isupper() for c in password) and any(c.islower() for c in password):
            score += 1
        else:
            issues.append("missing case variety")
        if any(c.isdigit() for c in password):
            score += 1
        else:
            issues.append("missing digits")
        if any(not c.isalnum() for c in password):
            score += 1
        else:
            issues.append("missing symbols")
        if password.lower() in cls.COMMON:
            issues.append("common password")
            score = 0
        entropy = cls.entropy(password)
        return {
            "score": min(score, 5),
            "entropy": round(entropy, 2),
            "issues": issues,
            "strength": "strong" if score >= 4 else "medium" if score >= 2 else "weak",
        }


class Demo:
    @staticmethod
    def run_kdf() -> Dict[str, Any]:
        salt = b"demo-salt-12345"
        pbk = KDF.pbkdf2("password", salt, iterations=10_000, length=32)
        scr = KDF.scrypt("password", salt, n=2**14, length=32)
        hk = KDF.hkdf(b"input-key", b"salt", b"info", 32)
        return {
            "pbkdf2_len": len(pbk),
            "scrypt_len": len(scr),
            "hkdf_len": len(hk),
            "distinct": len({pbk, scr, hk}) == 3,
        }

    @staticmethod
    def run_aead() -> Dict[str, Any]:
        key = secrets.token_bytes(32)
        aead = AEAD(key)
        pt = b"sensitive payload " * 50
        blob = aead.seal(pt, b"context")
        recovered = aead.open(blob, b"context")
        wrong_ctx = False
        try:
            aead.open(blob, b"other")
        except ValueError:
            wrong_ctx = True
        corrupt = bytearray(blob)
        corrupt[-1] ^= 0xFF
        corrupt_rejected = False
        try:
            aead.open(bytes(corrupt), b"context")
        except ValueError:
            corrupt_rejected = True
        return {
            "roundtrip": recovered == pt,
            "wrong_aad_rejected": wrong_ctx,
            "corruption_rejected": corrupt_rejected,
        }

    @staticmethod
    def run_shamir() -> Dict[str, Any]:
        secret = secrets.randbelow(Shamir.PRIME)
        shares = Shamir.split(secret, 5, 3)
        recon3 = Shamir.combine(shares[:3])
        recon_other = Shamir.combine([shares[0], shares[2], shares[4]])
        recon2 = Shamir.combine(shares[:2])
        return {
            "recovered_ok": recon3 == secret and recon_other == secret,
            "wrong_k_fails": recon2 != secret,
            "share_count": len(shares),
        }

    @staticmethod
    def run_text_sharing() -> Dict[str, Any]:
        msg = "top secret netforge message"
        shares = SecretSharing.split_text(msg, 4, 2)
        recon = SecretSharing.combine_text([shares[0], shares[3]])
        return {"text_match": recon == msg, "shares": len(shares)}

    @staticmethod
    def run_vault() -> Dict[str, Any]:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.bin")
            v = Vault("hunter2", path)
            v.put("api_key", b"sk-1234567890", tags=["prod", "api"])
            v.put("db_url", b"postgres://localhost/db", tags=["prod"])
            v.put("backup_key", b"\x00\xff\x01\x02binary", tags=["backup"])
            retrieved = v.get("api_key")
            search = v.search("prod")
            v.save()
            v2 = Vault("hunter2", path)
            load_ok = v2.load("hunter2")
            v3 = Vault("hunter2", path)
            bad_load = v3.load("wrongpass")
            audit_ok = v2.verify_audit()
            return {
                "retrieved_ok": retrieved == b"sk-1234567890",
                "search_hits": len(search),
                "load_ok": load_ok,
                "bad_password_rejected": not bad_load,
                "audit_chain_ok": audit_ok,
                "reloaded_retrieval": v2.get("db_url") == b"postgres://localhost/db",
            }

    @staticmethod
    def run_auditor() -> Dict[str, Any]:
        results = {}
        for pw in ["password", "abc", "Tr0ub4dor&3", "correct horse battery staple"]:
            results[pw] = PasswordAuditor.audit(pw)
        return results

    @staticmethod
    def run_keyring() -> Dict[str, Any]:
        kr = Keyring()
        kr.create("k1", "data", ttl=3600, metadata={"owner": "svc"})
        kr.create("k2", "signing")
        material1 = kr.get("k1")
        kr.rotate("k1")
        material2 = kr.get("k1")
        kr.revoke("k2")
        revoked_blocked = False
        try:
            kr.get("k2")
        except PermissionError:
            revoked_blocked = True
        return {
            "rotation_changed_key": material1 != material2,
            "revoked_blocked": revoked_blocked,
            "audit_events": len(kr.audit),
        }


def render(name: str, data: Dict[str, Any]) -> str:
    lines = ["=" * 64, f"  CRYPTOVAULT :: {name.upper()}", "=" * 64]
    for k, v in data.items():
        lines.append(f"  {k}: {v}")
    lines.append("=" * 64)
    return "\n".join(lines)


def main() -> None:
    print(render("kdf", Demo.run_kdf()))
    print(render("aead", Demo.run_aead()))
    print(render("shamir", Demo.run_shamir()))
    print(render("text sharing", Demo.run_text_sharing()))
    print(render("keyring", Demo.run_keyring()))
    print(render("vault", Demo.run_vault()))
    print(render("password auditor", Demo.run_auditor()))


if __name__ == "__main__":
    main()