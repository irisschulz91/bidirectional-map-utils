import sys
import os
import unittest

# Ensure src is importable when tests are run with PYTHONPATH=src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bidirectional_map_utils import BidirectionalMap, ValueConflictError


class ForwardAccessTests(unittest.TestCase):

    def test_set_and_get(self):
        m = BidirectionalMap()
        m["a"] = 1
        self.assertEqual(m["a"], 1)

    def test_len(self):
        m = BidirectionalMap()
        self.assertEqual(len(m), 0)
        m["a"] = 1
        m["b"] = 2
        self.assertEqual(len(m), 2)

    def test_contains(self):
        m = BidirectionalMap()
        m["a"] = 1
        self.assertIn("a", m)
        self.assertNotIn("b", m)

    def test_iter_returns_keys(self):
        m = BidirectionalMap()
        m["a"] = 1
        m["b"] = 2
        self.assertEqual(set(iter(m)), {"a", "b"})

    def test_keys_values_items_views(self):
        m = BidirectionalMap()
        m["a"] = 1
        m["b"] = 2
        self.assertEqual(set(m.keys()), {"a", "b"})
        self.assertEqual(set(m.values()), {1, 2})
        self.assertEqual(set(m.items()), {("a", 1), ("b", 2)})

    def test_get_default(self):
        m = BidirectionalMap()
        m["a"] = 1
        self.assertEqual(m.get("a"), 1)
        self.assertEqual(m.get("missing"), None)
        self.assertEqual(m.get("missing", 42), 42)

    def test_repr_roundtrip_friendly(self):
        m = BidirectionalMap({"a": 1})
        self.assertEqual(repr(m), "BidirectionalMap({'a': 1})")


class ReverseAccessTests(unittest.TestCase):

    def test_get_key(self):
        m = BidirectionalMap()
        m["a"] = 1
        self.assertEqual(m.get_key(1), "a")

    def test_get_key_missing_raises(self):
        m = BidirectionalMap()
        with self.assertRaises(KeyError):
            m.get_key(999)

    def test_get_key_default_returned(self):
        m = BidirectionalMap()
        m["a"] = 1
        self.assertEqual(m.get_key(1, default=None), "a")
        self.assertEqual(m.get_key(999, default=None), None)

    def test_get_key_explicit_none_value_is_findable(self):
        """Guard against a sentinel bug: None must be a legal value."""
        m = BidirectionalMap()
        m["a"] = None
        self.assertEqual(m.get_key(None), "a")
        self.assertEqual(m.get_key(None, default="x"), "a")
        self.assertEqual(m.get_key(999, default=None), None)


class ConflictAndDeletionTests(unittest.TestCase):

    def test_duplicate_value_raises(self):
        m = BidirectionalMap()
        m["a"] = 1
        with self.assertRaises(ValueConflictError):
            m["b"] = 1

    def test_reassign_same_key_same_value_is_noop(self):
        m = BidirectionalMap()
        m["a"] = 1
        m["a"] = 1
        self.assertEqual(m["a"], 1)
        self.assertEqual(m.get_key(1), "a")
        self.assertEqual(len(m), 1)

    def test_reassign_key_to_new_value_updates_inverse(self):
        m = BidirectionalMap()
        m["a"] = 1
        m["a"] = 2
        self.assertEqual(m["a"], 2)
        self.assertEqual(m.get_key(2), "a")
        with self.assertRaises(KeyError):
            m.get_key(1)

    def test_reassign_key_to_value_held_by_other_key_raises(self):
        m = BidirectionalMap()
        m["a"] = 1
        m["b"] = 2
        with self.assertRaises(ValueConflictError):
            m["a"] = 2
        # State unchanged on failed insert
        self.assertEqual(m["a"], 1)
        self.assertEqual(m["b"], 2)

    def test_delete_removes_from_both_indices(self):
        m = BidirectionalMap()
        m["a"] = 1
        del m["a"]
        self.assertNotIn("a", m)
        with self.assertRaises(KeyError):
            m.get_key(1)

    def test_clear(self):
        m = BidirectionalMap()
        m["a"] = 1
        m["b"] = 2
        m.clear()
        self.assertEqual(len(m), 0)
        with self.assertRaises(KeyError):
            m.get_key(1)
        with self.assertRaises(KeyError):
            m["a"]


class EqualityAndCopyTests(unittest.TestCase):

    def test_eq_same(self):
        a = BidirectionalMap({"a": 1})
        b = BidirectionalMap({"a": 1})
        self.assertEqual(a, b)

    def test_eq_diff(self):
        a = BidirectionalMap({"a": 1})
        b = BidirectionalMap({"a": 2})
        self.assertNotEqual(a, b)

    def test_eq_against_plain_dict(self):
        a = BidirectionalMap({"a": 1, "b": 2})
        self.assertEqual(a, {"a": 1, "b": 2})

    def test_copy_independent(self):
        a = BidirectionalMap()
        a["a"] = 1
        b = a.copy()
        b["a"] = 2
        self.assertEqual(a["a"], 1)
        self.assertEqual(b["a"], 2)
        self.assertEqual(a.get_key(1), "a")
        self.assertEqual(b.get_key(2), "a")


class EdgeCaseTests(unittest.TestCase):

    def test_unhashable_value_rejected(self):
        m = BidirectionalMap()
        with self.assertRaises(TypeError):
            m["a"] = [1, 2, 3]

    def test_unhashable_key_rejected(self):
        m = BidirectionalMap()
        with self.assertRaises(TypeError):
            m[[1, 2]] = 1

    def test_value_is_None_supported(self):
        m = BidirectionalMap()
        m["a"] = None
        self.assertEqual(m["a"], None)
        self.assertEqual(m.get_key(None), "a")

    def test_key_is_None_supported(self):
        m = BidirectionalMap()
        m[None] = 1
        self.assertEqual(m[None], 1)
        self.assertEqual(m.get_key(1), None)

    def test_initial_mapping_argument(self):
        m = BidirectionalMap({"a": 1, "b": 2})
        self.assertEqual(m["a"], 1)
        self.assertEqual(m.get_key(2), "b")
        self.assertEqual(len(m), 2)

    def test_initial_mapping_with_duplicate_value_raises(self):
        with self.assertRaises(ValueConflictError):
            BidirectionalMap({"a": 1, "b": 1})


if __name__ == "__main__":
    unittest.main()
