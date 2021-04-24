#!/bin/python
import sys
from pathlib import Path
assert len(sys.argv) == 2
path = Path(sys.argv[1])
words = {}

with open(path, encoding='utf-8') as f:
    pairs = [word.strip().rsplit(' ', 1) for word in f]
    pairs.sort(reverse=True, key=lambda x: int(x[1]))
    words = {p[0]: int(p[1]) for p in pairs}

import pickle
pickle.dump(words, open(path.with_suffix(".pkl"), "wb"))
