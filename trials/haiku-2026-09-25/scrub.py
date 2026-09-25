"""Rewrite machine-specific paths in the trial record to readable placeholders."""
import re, sys
from pathlib import Path
SCRATCH = "/tmp/claude-0/-home-user-harness-engineering-demo/c1c8aa19-33c1-5600-b044-80ddd8b5dd33/scratchpad"
subs = [
    (re.escape(SCRATCH) + r"/trial/run-[0-9a-z]+/[a-z0-9-]+", "<ws>"),
    (re.escape(SCRATCH) + r"/snap\d*", "<repo>"),
    (re.escape(SCRATCH) + r"/lc12/bin/python3?", "python"),
    (r"/home/user/harness-engineering-demo", "<repo>"),
    (r"/usr/bin/python3\.12", "python"),
    (re.escape(SCRATCH), "<scratch>"),
]
for p in Path(sys.argv[1]).rglob("*"):
    if p.is_file() and p.suffix in {".md", ".json", ".txt", ".py", ""}:
        try:
            t = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        n = t
        for pat, rep in subs:
            n = re.sub(pat, rep, n)
        if n != t:
            p.write_text(n, encoding="utf-8", newline="\n")
