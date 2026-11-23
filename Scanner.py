import socket
import threading
from queue import Queue
from typing import List, Tuple

class PortScanner:
    def __init__(self, target: str, start_port: int = 1, end_port: int = 1024, threads: int = 100, timeout: float = 1.0):
        self.target = target
        self.start_port = start_port
        self.end_port = end_port
        self.threads = threads
        self.timeout = timeout
        self.open_ports: List[int] = []
        self.lock = threading.Lock()
        self.queue: Queue = Queue()

    def scan_port(self, port: int) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                result = sock.connect_ex((self.target, port))
                if result == 0:
                    with self.lock:
                        self.open_ports.append(port)
        except Exception:
            pass

    def worker(self) -> None:
        while not self.queue.empty():
            port = self.queue.get()
            self.scan_port(port)
            self.queue.task_done()

    def run(self) -> List[int]:
        for port in range(self.start_port, self.end_port + 1):
            self.queue.put(port)

        thread_list = []
        for _ in range(self.threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            thread_list.append(t)

        self.queue.join()

        for t in thread_list:
            t.join(timeout=0.1)

        self.open_ports.sort()
        return self.open_ports

def resolve_target(target: str) -> Tuple[str, str]:
    try:
        ip = socket.gethostbyname(target)
        return target, ip
    except socket.gaierror:
        return target, "Unable to resolve"

if __name__ == "__main__":
    target_host = input("Enter target (IP or domain): ").strip()
    if not target_host:
        target_host = "scanme.nmap.org"

    name, ip = resolve_target(target_host)
    print(f"\nScanning {name} ({ip})")
    print("-" * 40)

    scanner = PortScanner(
        target=ip if ip != "Unable to resolve" else target_host,
        start_port=1,
        end_port=1024,
        threads=150,
        timeout=0.8
    )

    open_ports = scanner.run()

    if open_ports:
        print(f"\nOpen ports found ({len(open_ports)}):")
        for port in open_ports:
            print(f"  {port}/tcp")
    else:
        print("\nNo open ports found in the scanned range.")

    print("\nScan complete.")