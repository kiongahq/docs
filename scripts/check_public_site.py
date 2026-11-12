"""Fail publication if engineering content enters the public documentation output."""
import json
from pathlib import Path
import sys


def check(root):
    root = Path(root)
    # The old landing URL may contain only a redirect to the access notice.
    engineering = root / "engineering"
    if engineering.exists():
        files = {p.relative_to(engineering).as_posix() for p in engineering.rglob("*") if p.is_file()}
        if files - {"index.html"}:
            raise ValueError("Engineering files must not be published in the public site")
        if "index.html" in files and "engineering-access" not in (engineering / "index.html").read_text():
            raise ValueError("The engineering landing URL must redirect to the access notice")
    index = json.loads((root / "search/search_index.json").read_text())
    if any(entry.get("location", "").lstrip("/").startswith("engineering/") for entry in index["docs"]):
        raise ValueError("Engineering content must not enter public search")


if __name__ == "__main__":
    check(sys.argv[1])
