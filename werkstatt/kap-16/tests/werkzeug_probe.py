"""Probe fuer werkzeug.py: leerer Text zaehlt 0, zwei Woerter zaehlen 2."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from werkzeug import zaehle_woerter

assert zaehle_woerter("") == 0, "leerer Text"
assert zaehle_woerter("ein zwei") == 2, "zwei Woerter"
print("gruen")
