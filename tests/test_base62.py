import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import ALPHABET, decode, encode


class TestEncode(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(encode(0), "0")

    def test_single_digits(self):
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_multi_digits(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(3843), "ZZ")
        self.assertEqual(encode(3844), "100")

    def test_alphabet_order(self):
        self.assertEqual(
            ALPHABET,
            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )

    def test_negative(self):
        with self.assertRaises(ValueError):
            encode(-1)


class TestDecode(unittest.TestCase):
    def test_known(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("100"), 3844)

    def test_round_trip(self):
        for n in list(range(0, 5000)) + [10**8, 2**63]:
            self.assertEqual(decode(encode(n)), n)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            decode("")
        with self.assertRaises(ValueError):
            decode("ab-c")


if __name__ == "__main__":
    unittest.main()
