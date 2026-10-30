# bidirectional-map-utils

A dictionary-like structure that maintains a reverse lookup index, giving O(1) value-to-key lookups alongside normal key-to-value access.

## Usage

```python
from bidirectional_map_utils import BidirectionalMap, ValueConflictError

m = BidirectionalMap()
m["red"] = "#ff0000"
m["blue"] = "#0000ff"

print(m["red"])          # forward lookup: '#ff0000'
print(m.get_key("#ff0000"))  # reverse lookup: 'red'

# Duplicate values are rejected, not silently remapped:
try:
    m["green"] = "#ff0000"
except ValueConflictError:
    pass
```

## Why this exists

When you need to look up a key from a value as often as you look up the value from a key, maintaining a hand-rolled inverse dict alongside the forward one is the usual answer — and the usual bug is forgetting to update one side on mutation, leaving a stale entry behind. `BidirectionalMap` keeps both indices in a single object so they can never drift apart.

The trade-off: **values must be hashable** (they are used as dict keys in the inverse index), and **duplicate values are forbidden**. Inserting a value that already exists raises `ValueConflictError` rather than silently remapping the value to a new key. This is deliberate: silent remapping would require scanning for orphaned keys, and a quiet overwrite is exactly the kind of bug this library exists to prevent.

## The awkward edge

If you call `get_key` on a missing value, it raises `KeyError` unless you pass an explicit `default`. Note that `None` is a perfectly legal value (and a legal default), so the default sentinel is internal — you can safely do `m.get_key(missing_value, default=None)` without ambiguity.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

