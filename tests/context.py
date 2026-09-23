"""Put ``src/`` on the path so the suite runs from a bare checkout.

Deliberately no install step: the whole package is stdlib-only unless you opt
into the ``anthropic`` backend, so ``python -m unittest`` works on a fresh
machine with nothing fetched from the network.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
