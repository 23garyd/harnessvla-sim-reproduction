"""Artifacts disk guard (spec section 4): 200 GB hard cap under artifacts/.
The batch runner calls this before each rollout; on OVER it pauses the
queue. It never deletes anything."""
import argparse
import os
import sys

DEFAULT_CAP_BYTES = 200 * 1024**3  # 200 GB


def usage_bytes(root):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            try:
                total += os.stat(os.path.join(dirpath, name)).st_size
            except OSError:
                continue  # file vanished mid-scan
    return total


def check(root, cap_bytes=DEFAULT_CAP_BYTES):
    used = usage_bytes(root)
    return used, used <= cap_bytes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="artifacts")
    parser.add_argument("--cap-bytes", type=int, default=DEFAULT_CAP_BYTES)
    args = parser.parse_args(argv)
    used, ok = check(args.path, args.cap_bytes)
    print(f"disk_guard: used={used} cap={args.cap_bytes} "
          f"status={'OK' if ok else 'OVER'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
