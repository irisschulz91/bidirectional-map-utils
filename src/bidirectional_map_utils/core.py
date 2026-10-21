"""Core implementation of a bidirectional map.

Design decisions (documented so the behaviour is unambiguous):

1. Values must be hashable. We need to build a reverse index keyed by
   value, so unhashable values are rejected at insertion time.

2. The inverse mapping is one-to-one: inserting a duplicate value
   raises ValueConflictError. We deliberately do NOT silently overwrite
   the existing key. Overwriting would make the reverse index stale
   unless we also scanned for orphans, and the most common bug in
   hand-rolled inverse dicts is exactly that stale-orphan case. Raising
   forces the caller to be explicit.

3. The class behaves like a MutableMapping where it is cheap to do so
   (__len__, __contains__, __iter__, keys, values, items, get) and adds
   `get_key` for the reverse lookup that is the whole reason this class
   exists.

4. Deletions update both indices together, so they can never drift.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")


class ValueConflictError(ValueError):
    """Raised when a value that already exists in the inverse index is inserted.

    We raise rather than overwrite so that callers who accidentally
    introduce a duplicate value hear about it instead of silently
    corrupting the reverse index.
    """


class BidirectionalMap(Mapping):
    """A dict-like structure with an O(1) reverse lookup.

    Maintains two internal dicts:
      * ``_forward``: key -> value
      * ``_inverse``: value -> key

    Because both are plain dicts, forward lookup (``self[k]``) and
    reverse lookup (``self.get_key(v)``) are both O(1) average.

    The trade-off: values must be hashable, and duplicate values are
    forbidden (see ValueConflictError).
    """

    __slots__ = ("_forward", "_inverse")

    def __init__(self, initial: Mapping | None = None) -> None:
        """Create an empty map, optionally seeded from ``initial``.

        ``initial`` must be a mapping; passing a sequence of pairs is
        intentionally not supported to keep the signature simple and
        unambiguous.
        """
        self._forward: dict = {}
        self._inverse: dict = {}
        if initial is not None:
            for key, value in initial.items():
                self[key] = value

    # ------------------------------------------------------------------
    # Forward access (dict-like, read side of MutableMapping)
    # ------------------------------------------------------------------

    def __getitem__(self, key: _K) -> _V:
        return self._forward[key]

    def __iter__(self) -> Iterator:
        """Iterate over keys, matching built-in dict semantics."""
        return iter(self._forward)

    def __len__(self) -> int:
        return len(self._forward)

    def __contains__(self, key: object) -> bool:
        return key in self._forward

    def get(self, key, default=None):
        """Forward get: returns the value for ``key`` or ``default``."""
        return self._forward.get(key, default)

    def keys(self):
        return self._forward.keys()

    def values(self):
        return self._forward.values()

    def items(self):
        return self._forward.items()

    # ------------------------------------------------------------------
    # Reverse access (the reason this class exists)
    # ------------------------------------------------------------------

    def get_key(self, value, default=...):
        """Return the key mapped to ``value``.

        Raises ``KeyError`` if ``value`` is not present and no
        ``default`` was supplied; otherwise returns ``default``.

        The sentinel default uses ``...`` (Ellipsis) so that callers
        can legitimately pass ``None`` as their default value.
        """
        if value in self._inverse:
            return self._inverse[value]
        if default is ...:
            raise KeyError(value)
        return default

    # ------------------------------------------------------------------
    # Mutation (write side of MutableMapping)
    # ------------------------------------------------------------------

    def __setitem__(self, key: _K, value: _V) -> None:
        """Insert or replace the forward mapping ``key -> value``.

        If ``key`` was already present with a *different* value, the
        old value is removed from the inverse index first to keep both
        indices consistent.

        If ``value`` is already mapped to a *different* key, raise
        ValueConflictError instead of silently remapping.
        """
        # If we are changing an existing key, evict its old value
        # from the inverse index before we check for conflicts,
        # otherwise reassigning a key to a value it already held
        # under a different key would be wrongly rejected.
        if key in self._forward:
            old_value = self._forward[key]
            if old_value == value:
                return
            del self._inverse[old_value]

        if value in self._inverse:
            existing_key = self._inverse[value]
            if existing_key != key:
                raise ValueConflictError(
                    f"Value {value!r} is already mapped to key "
                    f"{existing_key!r}"
                )

        self._forward[key] = value
        self._inverse[value] = key

    def __delitem__(self, key: _K) -> None:
        """Remove ``key`` and its associated value from both indices."""
        value = self._forward[key]
        del self._forward[key]
        del self._inverse[value]

    def clear(self) -> None:
        """Remove all entries."""
        self._forward.clear()
        self._inverse.clear()

    # ------------------------------------------------------------------
    # Convenience / equality
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self._forward)!r})"

    def __eq__(self, other: object) -> bool:
        """Equal to another BidirectionalMap with the same forward mapping.

        We compare only the forward index; the inverse is by
        construction the same when the forward is the same, so
        checking both would be redundant work.
        """
        if isinstance(other, BidirectionalMap):
            return self._forward == other._forward
        if isinstance(other, Mapping):
            return dict(self._forward) == dict(other)
        return NotImplemented

    def copy(self) -> "BidirectionalMap":
        """Return a shallow copy with independent indices."""
        clone = BidirectionalMap()
        clone._forward = dict(self._forward)
        clone._inverse = dict(self._inverse)
        return clone
