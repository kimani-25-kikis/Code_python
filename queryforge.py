import asyncio
import hashlib
import json
import os
import re
import sqlite3
import struct
import sys
import time
import uuid
import zlib
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


class ColumnType(Enum):
    INT = "INTEGER"
    TEXT = "TEXT"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOL = "INTEGER"


@dataclass
class Column:
    name: str
    type: ColumnType
    primary_key: bool = False
    not_null: bool = False
    unique: bool = False
    default: Any = None
    indexed: bool = False

    def ddl(self) -> str:
        parts = [self.name, self.type.value]
        if self.primary_key:
            parts.append("PRIMARY KEY")
        if self.not_null:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        if self.default is not None:
            parts.append(f"DEFAULT {self._literal(self.default)}")
        return " ".join(parts)

    @staticmethod
    def _literal(value: Any) -> str:
        if isinstance(value, str):
            return "'" + value.replace("'", "''") + "'"
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)


@dataclass
class Index:
    name: str
    columns: List[str]
    unique: bool = False

    def ddl(self, table: str) -> str:
        kind = "UNIQUE INDEX" if self.unique else "INDEX"
        return f"CREATE {kind} IF NOT EXISTS {self.name} ON {table} ({', '.join(self.columns)})"


@dataclass
class Table:
    name: str
    columns: List[Column] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)

    def ddl(self) -> str:
        cols = ", ".join(c.ddl() for c in self.columns)
        return f"CREATE TABLE IF NOT EXISTS {self.name} ({cols})"

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Optional[Column]:
        for c in self.columns:
            if c.name == name:
                return c
        return None


class QueryBuilder:
    def __init__(self, table: str):
        self._table = table
        self._select: List[str] = ["*"]
        self._where: List[Tuple[str, Any]] = []
        self._joins: List[Tuple[str, str, str, str]] = []
        self._group: List[str] = []
        self._having: List[Tuple[str, Any]] = []
        self._order: List[Tuple[str, str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._params: List[Any] = []
        self._distinct = False

    def select(self, *cols: str) -> "QueryBuilder":
        self._select = list(cols) if cols else ["*"]
        return self

    def distinct(self) -> "QueryBuilder":
        self._distinct = True
        return self

    def join(self, table: str, on_left: str, on_right: str,
             kind: str = "INNER") -> "QueryBuilder":
        self._joins.append((kind, table, on_left, on_right))
        return self

    def where(self, column: str, value: Any, op: str = "=") -> "QueryBuilder":
        self._where.append((f"{column} {op} ?", value))
        self._params.append(value)
        return self

    def where_in(self, column: str, values: Iterable[Any]) -> "QueryBuilder":
        vals = list(values)
        placeholders = ", ".join("?" * len(vals))
        self._where.append((f"{column} IN ({placeholders})", tuple(vals)))
        self._params.extend(vals)
        return self

    def where_like(self, column: str, pattern: str) -> "QueryBuilder":
        self._where.append((f"{column} LIKE ?", pattern))
        self._params.append(pattern)
        return self

    def group_by(self, *cols: str) -> "QueryBuilder":
        self._group = list(cols)
        return self

    def having(self, expr: str, value: Any) -> "QueryBuilder":
        self._having.append((expr, value))
        self._params.append(value)
        return self

    def order_by(self, column: str, direction: str = "ASC") -> "QueryBuilder":
        self._order.append((column, direction.upper()))
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit = n
        return self

    def offset(self, n: int) -> "QueryBuilder":
        self._offset = n
        return self

    def build(self) -> Tuple[str, List[Any]]:
        parts = ["SELECT"]
        if self._distinct:
            parts.append("DISTINCT")
        parts.append(", ".join(self._select))
        parts.append(f"FROM {self._table}")
        for kind, tbl, l, r in self._joins:
            parts.append(f"{kind} JOIN {tbl} ON {l} = {r}")
        if self._where:
            parts.append("WHERE " + " AND ".join(c for c, _ in self._where))
        if self._group:
            parts.append("GROUP BY " + ", ".join(self._group))
        if self._having:
            parts.append("HAVING " + " AND ".join(h for h, _ in self._having))
        if self._order:
            parts.append("ORDER BY " + ", ".join(f"{c} {d}" for c, d in self._order))
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")
        if self._offset is not None:
            parts.append(f"OFFSET {self._offset}")
        return " ".join(parts), list(self._params)


class Connection:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self._transaction_depth = 0

    @contextmanager
    def transaction(self):
        self._transaction_depth += 1
        try:
            self.conn.execute("SAVEPOINT sp" + str(self._transaction_depth))
            yield self
            self.conn.execute("RELEASE sp" + str(self._transaction_depth))
        except Exception:
            self.conn.execute("ROLLBACK TO sp" + str(self._transaction_depth))
            self.conn.execute("RELEASE sp" + str(self._transaction_depth))
            raise
        finally:
            self._transaction_depth -= 1

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, tuple(params))

    def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
        return self.conn.executemany(sql, [tuple(r) for r in rows])

    def fetch_all(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        cur = self.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def fetch_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetch_scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self.conn.close()


class SchemaManager:
    def __init__(self, conn: Connection):
        self.conn = conn
        self.tables: Dict[str, Table] = {}
        self.migrations: List[Tuple[str, Callable[[Connection], None]]] = []
        self._ensure_migration_table()

    def _ensure_migration_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        self.conn.conn.commit()

    def register_table(self, table: Table) -> None:
        self.tables[table.name] = table
        self.conn.execute(table.ddl())
        for idx in table.indexes:
            self.conn.execute(idx.ddl(table.name))
        self.conn.conn.commit()

    def register_migration(self, name: str, fn: Callable[[Connection], None]) -> None:
        self.migrations.append((name, fn))

    def applied_migrations(self) -> List[str]:
        rows = self.conn.fetch_all("SELECT name FROM _migrations ORDER BY id")
        return [r["name"] for r in rows]

    def migrate(self) -> List[str]:
        applied = set(self.applied_migrations())
        newly_applied = []
        for name, fn in self.migrations:
            if name in applied:
                continue
            with self.conn.transaction():
                fn(self.conn)
                self.conn.execute(
                    "INSERT INTO _migrations (name, applied_at) VALUES (?, ?)",
                    (name, datetime.now(timezone.utc).isoformat())
                )
            newly_applied.append(name)
        return newly_applied

    def table_exists(self, name: str) -> bool:
        row = self.conn.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return row is not None

    def table_info(self, name: str) -> List[Dict[str, Any]]:
        return self.conn.fetch_all(f"PRAGMA table_info({name})")

    def table_columns(self, name: str) -> List[str]:
        return [c["name"] for c in self.table_info(name)]


class Repository:
    def __init__(self, conn: Connection, table: Table):
        self.conn = conn
        self.table = table
        self._validate_schema()

    def _validate_schema(self) -> None:
        actual = set(self.conn.fetch_scalar(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (self.table.name,)
        ) and SchemaManager(self.conn).table_columns(self.table.name) or [])
        expected = set(self.table.column_names())
        if actual and not expected.issubset(actual):
            missing = expected - actual
            raise ValueError(f"missing columns in {self.table.name}: {missing}")

    def insert(self, **values: Any) -> int:
        cols = ", ".join(values.keys())
        placeholders = ", ".join("?" * len(values))
        sql = f"INSERT INTO {self.table.name} ({cols}) VALUES ({placeholders})"
        cur = self.conn.execute(sql, values.values())
        self.conn.conn.commit()
        return cur.lastrowid

    def insert_many(self, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        placeholders = ", ".join("?" * len(cols))
        sql = f"INSERT INTO {self.table.name} ({', '.join(cols)}) VALUES ({placeholders})"
        data = [[row.get(c) for c in cols] for row in rows]
        self.conn.executemany(sql, data)
        self.conn.conn.commit()
        return len(rows)

    def update(self, pk_value: Any, **values: Any) -> int:
        pk = self._primary_key()
        sets = ", ".join(f"{c} = ?" for c in values.keys())
        sql = f"UPDATE {self.table.name} SET {sets} WHERE {pk} = ?"
        cur = self.conn.execute(sql, list(values.values()) + [pk_value])
        self.conn.conn.commit()
        return cur.rowcount

    def delete(self, pk_value: Any) -> int:
        pk = self._primary_key()
        sql = f"DELETE FROM {self.table.name} WHERE {pk} = ?"
        cur = self.conn.execute(sql, (pk_value,))
        self.conn.conn.commit()
        return cur.rowcount

    def get(self, pk_value: Any) -> Optional[Dict[str, Any]]:
        pk = self._primary_key()
        return self.conn.fetch_one(
            f"SELECT * FROM {self.table.name} WHERE {pk} = ?", (pk_value,)
        )

    def all(self) -> List[Dict[str, Any]]:
        return self.conn.fetch_all(f"SELECT * FROM {self.table.name}")

    def count(self) -> int:
        return self.conn.fetch_scalar(f"SELECT COUNT(*) FROM {self.table.name}") or 0

    def query(self) -> QueryBuilder:
        return QueryBuilder(self.table.name)

    def execute_query(self, qb: QueryBuilder) -> List[Dict[str, Any]]:
        sql, params = qb.build()
        return self.conn.fetch_all(sql, params)

    def exists(self, **criteria: Any) -> bool:
        conditions = " AND ".join(f"{k} = ?" for k in criteria.keys())
        sql = f"SELECT 1 FROM {self.table.name} WHERE {conditions} LIMIT 1"
        return self.conn.fetch_one(sql, list(criteria.values())) is not None

    def find(self, **criteria: Any) -> List[Dict[str, Any]]:
        conditions = " AND ".join(f"{k} = ?" for k in criteria.keys())
        sql = f"SELECT * FROM {self.table.name} WHERE {conditions}"
        return self.conn.fetch_all(sql, list(criteria.values()))

    def _primary_key(self) -> str:
        for c in self.table.columns:
            if c.primary_key:
                return c.name
        return "id"


class Migration:
    def __init__(self, schema: SchemaManager):
        self.schema = schema
        self._steps: List[Tuple[str, Callable[[Connection], None]]] = []

    def step(self, name: str, fn: Callable[[Connection], None]) -> "Migration":
        self._steps.append((name, fn))
        return self

    def apply(self) -> List[str]:
        for name, fn in self._steps:
            self.schema.register_migration(name, fn)
        return self.schema.migrate()


class RowHasher:
    def __init__(self, key: bytes):
        self.key = key

    def hash_row(self, row: Dict[str, Any]) -> str:
        payload = json.dumps(row, sort_keys=True, default=str).encode()
        return hashlib.blake2b(self.key + payload, digest_size=16).hexdigest()

    def find_duplicates(self, rows: List[Dict[str, Any]]) -> List[Tuple[str, List[int]]]:
        groups: Dict[str, List[int]] = defaultdict(list)
        for i, row in enumerate(rows):
            groups[self.hash_row(row)].append(i)
        return [(h, idx) for h, idx in groups.items() if len(idx) > 1]


class Backup:
    def __init__(self, conn: Connection):
        self.conn = conn

    def dump(self, path: str) -> Dict[str, Any]:
        tables = self.conn.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_%'"
        )
        snapshot = {"tables": {}, "created": datetime.now(timezone.utc).isoformat()}
        for t in tables:
            name = t["name"]
            rows = self.conn.fetch_all(f"SELECT * FROM {name}")
            snapshot["tables"][name] = rows
        payload = json.dumps(snapshot, default=str).encode()
        compressed = zlib.compress(payload)
        checksum = hashlib.sha256(compressed).hexdigest()
        blob = struct.pack("!I", len(compressed)) + compressed + checksum.encode()
        with open(path, "wb") as f:
            f.write(blob)
        return {"tables": list(snapshot["tables"].keys()),
                "rows": sum(len(r) for r in snapshot["tables"].values()),
                "bytes": len(blob), "checksum": checksum[:16]}

    def restore(self, path: str) -> Dict[str, Any]:
        with open(path, "rb") as f:
            blob = f.read()
        length = struct.unpack("!I", blob[:4])[0]
        compressed = blob[4:4 + length]
        checksum = blob[4 + length:].decode()
        if hashlib.sha256(compressed).hexdigest() != checksum:
            raise ValueError("backup checksum mismatch")
        snapshot = json.loads(zlib.decompress(compressed))
        restored = {}
        for table_name, rows in snapshot["tables"].items():
            if not rows:
                continue
            cols = list(rows[0].keys())
            placeholders = ", ".join("?" * len(cols))
            sql = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
            data = [[row.get(c) for c in cols] for row in rows]
            with self.conn.transaction():
                self.conn.executemany(sql, data)
            restored[table_name] = len(rows)
        return {"restored": restored, "total_rows": sum(restored.values())}


class QueryCache:
    def __init__(self, ttl: float = 60.0, max_size: int = 256):
        self.ttl = ttl
        self.max_size = max_size
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, sql: str, params: Iterable[Any]) -> str:
        payload = sql + "|" + json.dumps(list(params), default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, sql: str, params: Iterable[Any]) -> Optional[Any]:
        key = self._key(sql, params)
        entry = self.cache.get(key)
        if entry and time.monotonic() - entry[1] < self.ttl:
            self.hits += 1
            return entry[0]
        if entry:
            del self.cache[key]
        self.misses += 1
        return None

    def put(self, sql: str, params: Iterable[Any], value: Any) -> None:
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache.items(), key=lambda kv: kv[1][1])
            del self.cache[oldest[0]]
        self.cache[self._key(sql, params)] = (value, time.monotonic())

    def invalidate(self) -> None:
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }


class Batcher:
    def __init__(self, repo: Repository, size: int = 100, flush_interval: float = 1.0):
        self.repo = repo
        self.size = size
        self.flush_interval = flush_interval
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.monotonic()
        self.flushed = 0

    def add(self, row: Dict[str, Any]) -> int:
        self.buffer.append(row)
        if len(self.buffer) >= self.size:
            return self.flush()
        if time.monotonic() - self.last_flush >= self.flush_interval:
            return self.flush()
        return 0

    def flush(self) -> int:
        if not self.buffer:
            return 0
        inserted = self.repo.insert_many(self.buffer)
        self.flushed += inserted
        self.buffer.clear()
        self.last_flush = time.monotonic()
        return inserted


def render(name: str, data: Dict[str, Any]) -> str:
    lines = ["=" * 64, f"  QUERYFORGE :: {name.upper()}", "=" * 64]
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"  {k}:")
            for kk, vv in v.items():
                lines.append(f"    {kk}: {vv}")
        elif isinstance(v, list):
            lines.append(f"  {k}:")
            for item in v[:10]:
                lines.append(f"    - {item}")
            if len(v) > 10:
                lines.append(f"    ... {len(v) - 10} more")
        else:
            lines.append(f"  {k}: {v}")
    lines.append("=" * 64)
    return "\n".join(lines)


def main() -> None:
    conn = Connection(":memory:")
    schema = SchemaManager(conn)

    users = Table(
        name="users",
        columns=[
            Column("id", ColumnType.INT, primary_key=True),
            Column("email", ColumnType.TEXT, not_null=True, unique=True, indexed=True),
            Column("name", ColumnType.TEXT, not_null=True),
            Column("age", ColumnType.INT),
            Column("active", ColumnType.BOOL, default=True),
            Column("created_at", ColumnType.TEXT),
        ],
    )

    orders = Table(
        name="orders",
        columns=[
            Column("id", ColumnType.INT, primary_key=True),
            Column("user_id", ColumnType.INT, not_null=True, indexed=True),
            Column("amount", ColumnType.REAL, not_null=True),
            Column("status", ColumnType.TEXT, default="pending"),
        ],
    )
    orders.indexes.append(Index("idx_orders_status", ["status"]))

    schema.register_table(users)
    schema.register_table(orders)

    users_repo = Repository(conn, users)
    orders_repo = Repository(conn, orders)

    user_rows = [
        {"email": "alice@example.com", "name": "Alice", "age": 30,
         "created_at": datetime.now(timezone.utc).isoformat()},
        {"email": "bob@example.com", "name": "Bob", "age": 25,
         "created_at": datetime.now(timezone.utc).isoformat()},
        {"email": "carol@example.com", "name": "Carol", "age": 35,
         "created_at": datetime.now(timezone.utc).isoformat()},
        {"email": "dave@example.com", "name": "Dave", "age": 28,
         "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    users_repo.insert_many(user_rows)

    order_rows = []
    for uid in range(1, 5):
        for j in range(3):
            order_rows.append({
                "user_id": uid,
                "amount": round(10.0 * (uid + j), 2),
                "status": ["pending", "shipped", "delivered"][j % 3],
            })
    orders_repo.insert_many(order_rows)

    qb = (users_repo.query()
          .select("users.name", "users.email", "SUM(orders.amount) as total")
          .join("orders", "users.id", "orders.user_id")
          .where("users.active", True)
          .group_by("users.id")
          .having("SUM(orders.amount) > ?", 50)
          .order_by("total", "DESC"))
    aggregated = users_repo.execute_query(qb)

    cache = QueryCache(ttl=5.0)
    sql = "SELECT COUNT(*) as c FROM users WHERE age > ?"
    cached = cache.get(sql, (26,))
    if cached is None:
        result = conn.fetch_one(sql, (26,))
        cache.put(sql, (26,), result)
        cached = result
    cache.get(sql, (26,))

    hasher = RowHasher(b"dedupe-key")
    dupes = hasher.find_duplicates([
        {"a": 1, "b": 2}, {"a": 1, "b": 2}, {"a": 3, "b": 4},
    ])

    migration = Migration(schema)
    migration.step("add_phone_column",
                   lambda c: c.execute("ALTER TABLE users ADD COLUMN phone TEXT"))
    migration.step("backfill_phone",
                   lambda c: c.execute("UPDATE users SET phone = 'unknown'"))
    applied = migration.apply()

    backup = Backup(conn)
    dump_stats = backup.dump("/tmp/queryforge_backup.bin")

    conn2 = Connection(":memory:")
    schema2 = SchemaManager(conn2)
    schema2.register_table(users)
    schema2.register_table(orders)
    backup2 = Backup(conn2)
    restore_stats = backup2.restore("/tmp/queryforge_backup.bin")

    batcher = Batcher(orders_repo, size=5, flush_interval=10.0)
    for i in range(7):
        batcher.add({"user_id": 1, "amount": 5.0 + i, "status": "batched"})
    batcher.flush()

    print(render("schema", {
        "tables": list(schema.tables.keys()),
        "users_columns": schema.table_columns("users"),
        "orders_columns": schema.table_columns("orders"),
    }))
    print(render("aggregated_orders", {"rows": aggregated}))
    print(render("query_cache", cache.stats()))
    print(render("dedupe", {"duplicate_groups": dupes}))
    print(render("migrations", {"applied": applied,
                                "applied_history": schema.applied_migrations()}))
    print(render("backup", {"dump": dump_stats, "restore": restore_stats}))
    print(render("batcher", {"flushed": batcher.flushed,
                             "total_orders": orders_repo.count()}))

    conn.close()
    conn2.close()


if __name__ == "__main__":
    main()