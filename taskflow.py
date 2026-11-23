import asyncio
import heapq
import inspect
import json
import os
import pickle
import secrets
import signal
import sys
import time
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class Backoff(Enum):
    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff: Backoff = Backoff.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.1

    def delay_for(self, attempt: int) -> float:
        if self.backoff == Backoff.CONSTANT:
            d = self.base_delay
        elif self.backoff == Backoff.LINEAR:
            d = self.base_delay * attempt
        elif self.backoff == Backoff.EXPONENTIAL:
            d = self.base_delay * (2 ** (attempt - 1))
        else:
            a, b = 0, 1
            for _ in range(attempt):
                a, b = b, a + b
            d = self.base_delay * b
        d = min(d, self.max_delay)
        if self.jitter:
            d *= 1 + secrets.randbelow(1000) / 1000 * self.jitter
        return d


@dataclass
class TaskRecord:
    task_id: str
    name: str
    state: TaskState = TaskState.PENDING
    attempts: int = 0
    created_at: float = field(default_factory=time.monotonic)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    depends_on: Set[str] = field(default_factory=set)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    priority: int = 5
    tags: Set[str] = field(default_factory=set)
    output_slot: Optional[str] = None

    def duration(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "state": self.state.value,
            "attempts": self.attempts,
            "duration": round(self.duration(), 4) if self.duration() else None,
            "error": self.error,
            "depends_on": list(self.depends_on),
            "tags": list(self.tags),
        }


class DAG:
    def __init__(self):
        self.nodes: Dict[str, TaskRecord] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)
        self.reverse: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, record: TaskRecord) -> None:
        if record.task_id in self.nodes:
            raise ValueError(f"duplicate task id: {record.task_id}")
        self.nodes[record.task_id] = record
        for dep in record.depends_on:
            self.edges[dep].add(record.task_id)
            self.reverse[record.task_id].add(dep)

    def topo_sort(self) -> List[str]:
        indegree = {n: 0 for n in self.nodes}
        for n, deps in self.reverse.items():
            indegree[n] = len(deps)
        heap = [(self.nodes[n].priority, n) for n, d in indegree.items() if d == 0]
        heapq.heapify(heap)
        order = []
        while heap:
            _, node = heapq.heappop(heap)
            order.append(node)
            for succ in self.edges.get(node, set()):
                indegree[succ] -= 1
                if indegree[succ] == 0:
                    heapq.heappush(heap, (self.nodes[succ].priority, succ))
        if len(order) != len(self.nodes):
            raise ValueError("cycle detected in DAG")
        return order

    def detect_cycle(self) -> Optional[List[str]]:
        color = {n: 0 for n in self.nodes}
        stack: List[str] = []
        cycle: Optional[List[str]] = None

        def dfs(node: str) -> bool:
            nonlocal cycle
            color[node] = 1
            stack.append(node)
            for succ in self.edges.get(node, set()):
                if color[succ] == 0:
                    if dfs(succ):
                        return True
                elif color[succ] == 1:
                    idx = stack.index(succ)
                    cycle = stack[idx:] + [succ]
                    return True
            stack.pop()
            color[node] = 2
            return False

        for n in self.nodes:
            if color[n] == 0 and dfs(n):
                return cycle
        return None

    def roots(self) -> List[str]:
        return [n for n in self.nodes if not self.reverse.get(n)]

    def leaves(self) -> List[str]:
        return [n for n in self.nodes if not self.edges.get(n)]

    def ancestors(self, node: str) -> Set[str]:
        seen = set()
        stack = list(self.reverse.get(node, set()))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self.reverse.get(cur, set()))
        return seen

    def descendants(self, node: str) -> Set[str]:
        seen = set()
        stack = list(self.edges.get(node, set()))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self.edges.get(cur, set()))
        return seen


class TaskContext:
    def __init__(self, task_id: str, name: str, attempt: int,
                 output_slot: Optional[str]):
        self.task_id = task_id
        self.name = name
        self.attempt = attempt
        self.output_slot = output_slot
        self.logs: List[str] = []
        self.start = time.monotonic()
        self.metadata: Dict[str, Any] = {}

    def log(self, message: str) -> None:
        self.logs.append(f"[{time.monotonic() - self.start:.3f}s] {message}")

    def elapsed(self) -> float:
        return time.monotonic() - self.start


class OutputStore:
    def __init__(self):
        self.slots: Dict[str, Any] = {}
        self.watchers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def put(self, slot: str, value: Any) -> None:
        self.slots[slot] = value
        for cb in self.watchers.get(slot, []):
            try:
                cb(value)
            except Exception:
                pass

    def get(self, slot: str, default: Any = None) -> Any:
        return self.slots.get(slot, default)

    def has(self, slot: str) -> bool:
        return slot in self.slots

    def watch(self, slot: str, cb: Callable[[Any], None]) -> None:
        self.watchers[slot].append(cb)

    def snapshot(self) -> Dict[str, Any]:
        return dict(self.slots)


class Checkpoint:
    def __init__(self, path: str):
        self.path = path

    def save(self, dag: DAG, outputs: OutputStore) -> None:
        data = {
            "nodes": {n: r.to_dict() for n, r in dag.nodes.items()},
            "states": {n: r.state.value for n, r in dag.nodes.items()},
            "outputs": {k: repr(v) for k, v in outputs.snapshot().items()},
            "saved": datetime.now(timezone.utc).isoformat(),
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)

    def load(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return None
        with open(self.path) as f:
            return json.load(f)


class MetricsCollector:
    def __init__(self):
        self.counts: Dict[str, int] = defaultdict(int)
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.start = time.monotonic()

    def record(self, key: str, value: float = 1.0) -> None:
        self.counts[key] += 1
        self.timings[key].append(value)

    def summary(self) -> Dict[str, Any]:
        out = {"uptime": round(time.monotonic() - self.start, 3)}
        for key, vals in self.timings.items():
            if vals:
                out[key] = {
                    "count": self.counts[key],
                    "avg": round(sum(vals) / len(vals), 4),
                    "min": round(min(vals), 4),
                    "max": round(max(vals), 4),
                }
        return out


class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.history: deque = deque(maxlen=10000)

    def subscribe(self, event: str, handler: Callable) -> None:
        self.subscribers[event].append(handler)

    def emit(self, event: str, payload: Dict[str, Any]) -> None:
        record = {"event": event, "payload": payload,
                  "at": datetime.now(timezone.utc).isoformat()}
        self.history.append(record)
        for h in self.subscribers.get(event, []):
            try:
                h(payload)
            except Exception:
                pass


class Worker:
    def __init__(self, worker_id: str, engine: "TaskEngine"):
        self.worker_id = worker_id
        self.engine = engine
        self.busy = False
        self.current_task: Optional[str] = None

    async def run_task(self, record: TaskRecord,
                       fn: Callable) -> Tuple[TaskState, Any, Optional[Exception]]:
        self.busy = True
        self.current_task = record.task_id
        ctx = TaskContext(record.task_id, record.name, record.attempts + 1,
                          record.output_slot)
        try:
            if inspect.iscoroutinefunction(fn):
                result = await fn(ctx)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, fn, ctx)
            return TaskState.SUCCESS, result, None
        except Exception as e:
            return TaskState.FAILED, None, e
        finally:
            self.busy = False
            self.current_task = None


class TaskEngine:
    def __init__(self, max_workers: int = 8, checkpoint_path: Optional[str] = None):
        self.dag = DAG()
        self.outputs = OutputStore()
        self.metrics = MetricsCollector()
        self.bus = EventBus()
        self.max_workers = max_workers
        self.functions: Dict[str, Callable] = {}
        self.workers: List[Worker] = [Worker(f"w{i}", self) for i in range(max_workers)]
        self.running: Set[str] = set()
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        self.cancelled = False
        self.checkpoint = Checkpoint(checkpoint_path) if checkpoint_path else None
        self._retry_queue: List[Tuple[float, str, int]] = []

    def register(self, name: str, fn: Callable) -> None:
        self.functions[name] = fn

    def add(self, name: str, depends_on: Optional[List[str]] = None,
            retry: Optional[RetryPolicy] = None, priority: int = 5,
            output_slot: Optional[str] = None,
            tags: Optional[List[str]] = None) -> str:
        task_id = f"{name}-{uuid.uuid4().hex[:8]}"
        record = TaskRecord(
            task_id=task_id,
            name=name,
            depends_on=set(depends_on or []),
            retry_policy=retry or RetryPolicy(),
            priority=priority,
            tags=set(tags or []),
            output_slot=output_slot or task_id,
        )
        self.dag.add_task(record)
        self.bus.emit("task.added", record.to_dict())
        return task_id

    def ready_tasks(self) -> List[TaskRecord]:
        ready = []
        for task_id, record in self.dag.nodes.items():
            if record.state not in (TaskState.PENDING, TaskState.RETRYING):
                continue
            if task_id in self.running or task_id in self.completed:
                continue
            if all(dep in self.completed for dep in record.depends_on):
                ready.append(record)
        ready.sort(key=lambda r: (r.priority, r.created_at))
        return ready

    def _get_free_worker(self) -> Optional[Worker]:
        for w in self.workers:
            if not w.busy:
                return w
        return None

    async def _execute(self, record: TaskRecord, worker: Worker) -> None:
        record.state = TaskState.RUNNING
        record.attempts += 1
        record.started_at = time.monotonic()
        self.running.add(record.task_id)
        self.bus.emit("task.started", record.to_dict())

        fn = self.functions.get(record.name)
        if fn is None:
            record.state = TaskState.FAILED
            record.error = f"no function registered for {record.name}"
            self.failed.add(record.task_id)
            self.running.discard(record.task_id)
            return

        state, result, error = await worker.run_task(record, fn)
        record.finished_at = time.monotonic()
        self.running.discard(record.task_id)

        if state == TaskState.SUCCESS:
            record.state = TaskState.SUCCESS
            record.result = result
            if record.output_slot:
                self.outputs.put(record.output_slot, result)
            self.completed.add(record.task_id)
            self.metrics.record("task.success", record.duration() or 0)
            self.bus.emit("task.success", record.to_dict())
        else:
            if record.attempts < record.retry_policy.max_attempts:
                delay = record.retry_policy.delay_for(record.attempts)
                record.state = TaskState.RETRYING
                record.error = str(error)
                self._retry_queue.append(
                    (time.monotonic() + delay, record.task_id, record.attempts)
                )
                self.metrics.record("task.retry")
                self.bus.emit("task.retry", {**record.to_dict(),
                                            "delay": round(delay, 2)})
            else:
                record.state = TaskState.FAILED
                record.error = str(error)
                record.traceback = "".join(traceback.format_exception(
                    type(error), error, error.__traceback__)) if error else None
                self.failed.add(record.task_id)
                self.metrics.record("task.failed", record.duration() or 0)
                self.bus.emit("task.failed", record.to_dict())

    def _promote_retries(self) -> None:
        now = time.monotonic()
        due = [t for t in self._retry_queue if t[0] <= now]
        self._retry_queue = [t for t in self._retry_queue if t[0] > now]
        for _, task_id, _ in due:
            self.dag.nodes[task_id].state = TaskState.PENDING

    async def run(self, max_iterations: int = 10000) -> Dict[str, Any]:
        self.dag.topo_sort()
        cycle = self.dag.detect_cycle()
        if cycle:
            raise ValueError(f"cycle: {cycle}")

        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()

        def _stop(*_):
            self.cancelled = True
            stop_event.set()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _stop)
        except (NotImplementedError, RuntimeError):
            pass

        iterations = 0
        while iterations < max_iterations:
            iterations += 1
            if self.cancelled:
                break

            self._promote_retries()
            ready = self.ready_tasks()

            if not ready and not self.running and not self._retry_queue:
                break

            tasks = []
            for record in ready:
                worker = self._get_free_worker()
                if not worker:
                    break
                tasks.append(self._execute(record, worker))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            if self.checkpoint and iterations % 10 == 0:
                self.checkpoint.save(self.dag, self.outputs)

            await asyncio.sleep(0.001)

        for tid in self.dag.nodes:
            rec = self.dag.nodes[tid]
            if rec.state == TaskState.PENDING:
                rec.state = TaskState.SKIPPED

        if self.checkpoint:
            self.checkpoint.save(self.dag, self.outputs)

        return self.report()

    def report(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = defaultdict(int)
        for rec in self.dag.nodes.values():
            by_state[rec.state.value] += 1
        durations = [r.duration() for r in self.dag.nodes.values()
                     if r.duration() is not None]
        return {
            "tasks": len(self.dag.nodes),
            "by_state": dict(by_state),
            "avg_duration": round(sum(durations) / len(durations), 4) if durations else 0,
            "max_duration": round(max(durations), 4) if durations else 0,
            "outputs": list(self.outputs.snapshot().keys()),
            "metrics": self.metrics.summary(),
            "failed_details": [
                {"task": r.name, "error": r.error}
                for r in self.dag.nodes.values()
                if r.state == TaskState.FAILED
            ],
        }


async def example_pipeline(engine: TaskEngine) -> None:
    async def fetch(ctx: TaskContext) -> Dict[str, Any]:
        ctx.log("fetching remote payload")
        await asyncio.sleep(0.05)
        if ctx.attempt < 2:
            raise ConnectionError("transient network failure")
        return {"rows": [i * 2 for i in range(50)]}

    async def validate(ctx: TaskContext) -> bool:
        rows = ctx.metadata.get("rows", [])
        ctx.log(f"validating {len(rows)} rows")
        data = engine.outputs.get("fetch_out", {})
        return isinstance(data, dict) and len(data.get("rows", [])) > 0

    async def transform(ctx: TaskContext) -> List[int]:
        data = engine.outputs.get("fetch_out", {})
        rows = data.get("rows", []) if isinstance(data, dict) else []
        await asyncio.sleep(0.02)
        return [r ** 2 for r in rows]

    async def aggregate(ctx: TaskContext) -> Dict[str, Any]:
        data = engine.outputs.get("transform_out", [])
        return {"count": len(data), "sum": sum(data), "max": max(data) if data else 0}

    def report(ctx: TaskContext) -> str:
        agg = engine.outputs.get("aggregate_out", {})
        return f"aggregate={agg}"

    def always_fails(ctx: TaskContext) -> None:
        raise ValueError("this task always fails")

    engine.register("fetch", fetch)
    engine.register("validate", validate)
    engine.register("transform", transform)
    engine.register("aggregate", aggregate)
    engine.register("report", report)
    engine.register("always_fails", always_fails)

    t_fetch = engine.add("fetch", priority=1, output_slot="fetch_out",
                         retry=RetryPolicy(max_attempts=3,
                                           backoff=Backoff.EXPONENTIAL,
                                           base_delay=0.05),
                         tags=["io", "network"])
    t_validate = engine.add("validate", depends_on=[t_fetch], priority=2,
                            retry=RetryPolicy(max_attempts=2, base_delay=0.05))
    t_transform = engine.add("transform", depends_on=[t_validate], priority=3,
                             output_slot="transform_out")
    t_aggregate = engine.add("aggregate", depends_on=[t_transform], priority=4,
                             output_slot="aggregate_out")
    engine.add("report", depends_on=[t_aggregate], priority=6,
               output_slot="report_out")
    engine.add("always_fails", priority=99,
               retry=RetryPolicy(max_attempts=2, base_delay=0.01))

    engine.bus.subscribe("task.started",
                         lambda p: print(f"  [start] {p['name']}"))
    engine.bus.subscribe("task.success",
                         lambda p: print(f"  [ok]    {p['name']} "
                                         f"({p['duration']}s)"))
    engine.bus.subscribe("task.retry",
                         lambda p: print(f"  [retry] {p['name']} "
                                         f"delay={p['delay']}s"))
    engine.bus.subscribe("task.failed",
                         lambda p: print(f"  [fail]  {p['name']}: {p['error']}"))


def render(name: str, data: Dict[str, Any]) -> str:
    lines = ["=" * 64, f"  TASKFLOW :: {name.upper()}", "=" * 64]
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"  {k}:")
            for kk, vv in v.items():
                lines.append(f"    {kk}: {vv}")
        elif isinstance(v, list):
            lines.append(f"  {k}:")
            for item in v:
                lines.append(f"    - {item}")
        else:
            lines.append(f"  {k}: {v}")
    lines.append("=" * 64)
    return "\n".join(lines)


async def main() -> None:
    print("Running example DAG pipeline...\n")
    engine = TaskEngine(max_workers=4)
    await example_pipeline(engine)
    report = await engine.run()

    print()
    print(render("report", {
        "tasks": report["tasks"],
        "by_state": report["by_state"],
        "avg_duration": report["avg_duration"],
        "failed": report["failed_details"],
    }))
    print(render("metrics", report["metrics"]))

    dag = DAG()
    dag.add_task(TaskRecord("a", "task_a"))
    dag.add_task(TaskRecord("b", "task_b", depends_on={"a"}))
    dag.add_task(TaskRecord("c", "task_c", depends_on={"b"}))
    print(render("dag", {
        "topological_order": dag.topo_sort(),
        "roots": dag.roots(),
        "leaves": dag.leaves(),
        "ancestors_of_c": sorted(dag.ancestors("c")),
        "descendants_of_a": sorted(dag.descendants("a")),
        "cycle": dag.detect_cycle(),
    }))


if __name__ == "__main__":
    asyncio.run(main())