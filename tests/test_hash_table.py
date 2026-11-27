import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import ChainingHashTable, LinearProbingHashTable


TABLE_TYPES = (ChainingHashTable, LinearProbingHashTable)


def keys_for_bucket(bucket, count, bucket_count=16):
    """Find strings whose specified polynomial hash lands in one bucket."""
    matches = []
    candidate = 0
    while len(matches) < count:
        key = f"key-{candidate}"
        value = 0
        for character in key:
            value = (31 * value + ord(character)) % bucket_count
        if value == bucket:
            matches.append(key)
        candidate += 1
    return matches


class TestHashTableCommonBehavior(unittest.TestCase):
    def test_empty_table(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type.__name__):
                table = table_type()
                self.assertEqual(len(table), 0)
                self.assertEqual(table.get("missing"), None)
                self.assertNotIn("missing", table)
                self.assertEqual(table.load_factor, 0)
                found, value, cost = table.find("missing")
                self.assertFalse(found)
                self.assertIsNone(value)
                self.assertGreaterEqual(cost, 0)

    def test_find_reports_hit_value_and_search_cost(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type.__name__):
                table = table_type()
                table.put("present", "value")

                found, value, cost = table.find("present")

                self.assertTrue(found)
                self.assertEqual(value, "value")
                self.assertGreater(cost, 0)

    def test_none_value_is_distinguishable_from_missing_key(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type.__name__):
                table = table_type()
                table.put("none-value", None)

                self.assertIn("none-value", table)
                self.assertIsNone(table.get("none-value"))
                self.assertEqual(table.find("none-value"), (True, None, 1))

                table.delete("none-value")
                self.assertNotIn("none-value", table)
                self.assertEqual(table.find("none-value")[0], False)

    def test_put_updates_existing_value_without_increasing_length(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type.__name__):
                table = table_type()
                table.put("same", "before")
                initial_length = len(table)

                table.put("same", "after")

                self.assertEqual(table.get("same"), "after")
                self.assertEqual(len(table), initial_length)

    def test_delete_removes_key_and_missing_delete_is_safe(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type.__name__):
                table = table_type()
                table.put("remove-me", "value")

                table.delete("remove-me")

                self.assertNotIn("remove-me", table)
                self.assertIsNone(table.get("remove-me"))
                self.assertEqual(len(table), 0)
                table.delete("missing")
                self.assertEqual(len(table), 0)

    def test_non_string_keys_are_rejected(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type.__name__):
                table = table_type()
                with self.assertRaises(TypeError):
                    table.put(1, "value")
                with self.assertRaises(TypeError):
                    table.get(1)

    def test_max_load_none_disables_growth_for_chaining(self):
        table = ChainingHashTable(max_load=None)

        for index in range(40):
            table.put(f"key-{index}", str(index))

        self.assertEqual(len(table), 40)
        self.assertEqual(table.load_factor, 40 / 16)
        self.assertEqual(table.get("key-39"), "39")

    def test_chaining_collision_and_resize_preserve_entries(self):
        table = ChainingHashTable()
        colliding_keys = keys_for_bucket(3, 3)
        for key in colliding_keys:
            table.put(key, key.upper())

        costs = []
        for key in colliding_keys:
            found, value, cost = table.find(key)
            self.assertTrue(found)
            self.assertEqual(value, key.upper())
            costs.append(cost)
        self.assertEqual(sorted(costs), [1, 2, 3])

        for index in range(10):
            table.put(f"extra-{index}", str(index))

        # 13 entries exceed 0.75 of 16 buckets, causing growth to 32.
        self.assertEqual(table.load_factor, 13 / 32)
        for key in colliding_keys:
            self.assertEqual(table.get(key), key.upper())

    def test_chaining_delete_middle_collision_preserves_other_keys(self):
        table = ChainingHashTable()
        colliding_keys = keys_for_bucket(3, 3)
        for key in colliding_keys:
            table.put(key, key.upper())

        table.delete(colliding_keys[1])

        self.assertEqual(table.get(colliding_keys[0]), colliding_keys[0].upper())
        self.assertEqual(table.get(colliding_keys[2]), colliding_keys[2].upper())
        self.assertNotIn(colliding_keys[1], table)

    def test_chaining_find_in_empty_bucket_has_zero_cost(self):
        table = ChainingHashTable()
        stored_key = keys_for_bucket(1, 1)[0]
        missing_key = keys_for_bucket(0, 1)[0]
        table.put(stored_key, "value")

        found, value, cost = table.find(missing_key)

        self.assertFalse(found)
        self.assertIsNone(value)
        self.assertEqual(cost, 0)

    def test_linear_probing_wraps_from_last_slot_to_zero(self):
        table = LinearProbingHashTable(max_load=None)
        keys = keys_for_bucket(15, 2)

        table.put(keys[0], "first")
        table.put(keys[1], "second")

        found, value, cost = table.find(keys[1])
        self.assertTrue(found)
        self.assertEqual(value, "second")
        self.assertEqual(cost, 2)

    def test_linear_probing_finds_key_after_deleted_slot(self):
        table = LinearProbingHashTable(max_load=None)
        keys = keys_for_bucket(7, 2)
        table.put(keys[0], "first")
        table.put(keys[1], "second")

        table.delete(keys[0])

        self.assertEqual(table.get(keys[1]), "second")
        found, value, cost = table.find(keys[1])
        self.assertTrue(found)
        self.assertEqual(value, "second")
        self.assertEqual(cost, 2)

    def test_linear_probing_can_reinsert_a_deleted_key(self):
        table = LinearProbingHashTable(max_load=None)
        keys = keys_for_bucket(7, 2)
        table.put(keys[0], "before")
        table.put(keys[1], "neighbor")

        table.delete(keys[0])
        table.put(keys[0], "after")

        self.assertEqual(table.get(keys[0]), "after")
        self.assertEqual(table.get(keys[1]), "neighbor")

    def test_linear_probing_growth_preserves_entries(self):
        table = LinearProbingHashTable()
        for index in range(9):
            table.put(f"key-{index}", str(index))

        # 9 entries exceed 0.5 of 16 slots, causing growth to 32.
        self.assertEqual(table.load_factor, 9 / 32)
        for index in range(9):
            self.assertEqual(table.get(f"key-{index}"), str(index))

    def test_full_fixed_linear_table_updates_existing_key(self):
        table = LinearProbingHashTable(max_load=None)
        for index in range(16):
            table.put(f"key-{index}", str(index))

        table.put("key-0", "updated")

        self.assertEqual(len(table), 16)
        self.assertEqual(table.get("key-0"), "updated")
        with self.assertRaises(OverflowError):
            table.put("new-key", "value")

    def test_full_fixed_linear_table_get_for_missing_key_terminates(self):
        table = LinearProbingHashTable(max_load=None)
        for index in range(16):
            table.put(f"key-{index}", str(index))

        self.assertIsNone(table.get("missing-key"))


if __name__ == "__main__":
    unittest.main()
