import hashlib, os, sys
from pathlib import Path
from collections import defaultdict

def file_hash(path, chunk=65536):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk_data := f.read(chunk):
            h.update(chunk_data)
    return h.hexdigest()

def find_dupes(folder):
    hashes = defaultdict(list)
    for p in Path(folder).rglob("*"):
        if p.is_file():
            try:
                hashes[file_hash(p)].append(p)
            except (OSError, PermissionError):
                pass
    return {h: files for h, files in hashes.items() if len(files) > 1}

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    dupes = find_dupes(folder)
    if not dupes:
        print("No duplicates found.")
    else:
        total = 0
        for files in dupes.values():
            size = files[0].stat().st_size
            wasted = size * (len(files) - 1)
            total += wasted
            print(f"\n[{size} bytes each]")
            for f in files:
                print(f"  {f}")
        print(f"\nTotal wasted: {total / 1024:.1f} KB")