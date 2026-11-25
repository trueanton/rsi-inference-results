"""Materialize the cluster scripts at the absolute paths used on login and compute nodes."""
import argparse
import re
from pathlib import Path


def cluster_path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or not re.fullmatch(r"/[A-Za-z0-9_./-]+", value):
        raise argparse.ArgumentTypeError("Use an absolute Linux path with no spaces, shell metacharacters or '..'")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bench", "local", "shared"):
        parser.add_argument("--" + name, required=True, type=cluster_path)
    args = parser.parse_args()
    roots = {"@BENCH_ROOT@": args.bench, "@LOCAL_ROOT@": args.local, "@SHARED_ROOT@": args.shared}
    if len(set(roots.values())) != 3:
        parser.error("Use distinct locations for the checkout, local scratch and shared assets")
    source = Path(__file__).resolve().parent
    destination = args.bench / "experiments"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "runs").mkdir()
    for group in ("configs", "patches", "scripts"):
        for path in sorted((source / group).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            content = path.read_text()
            for token, root in roots.items():
                content = content.replace(token, str(root))
            target.write_text(content)
            target.chmod(0o700 if path.suffix == ".sh" else 0o600)
    print(destination)


if __name__ == "__main__":
    main()
