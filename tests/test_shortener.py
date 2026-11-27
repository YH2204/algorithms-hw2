import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shortener import Shortener


TABLE_TYPES = ("chaining", "linear")


class TestShortener(unittest.TestCase):
    def test_codes_start_at_one_and_duplicate_urls_reuse_code(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)

                first_code = shortener.shorten("https://example.com/one")
                second_code = shortener.shorten("https://example.com/two")
                duplicate_code = shortener.shorten("https://example.com/one")

                self.assertEqual(first_code, "1")
                self.assertEqual(second_code, "2")
                self.assertEqual(duplicate_code, first_code)

    def test_shorten_trims_url_and_reuses_normalized_address(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)
                code = shortener.shorten("  https://example.com/path  ")

                self.assertEqual(
                    shortener.shorten("https://example.com/path"),
                    code,
                )
                self.assertEqual(
                    shortener.expand(code),
                    "https://example.com/path",
                )

    def test_http_urls_are_accepted(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)
                code = shortener.shorten("http://example.com/path")

                self.assertEqual(shortener.expand(code), "http://example.com/path")

    def test_expand_returns_none_for_unknown_code(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)

                self.assertIsNone(shortener.expand("999"))

    def test_invalid_urls_raise_value_error(self):
        invalid_urls = (
            "",
            "   ",
            "ftp://example.com",
            "http://",
            "https:///path",
            "https://example.com/has space",
            "https://example.com/has\ttab",
            "https://example.com/has\nnewline",
        )
        for table_type in TABLE_TYPES:
            for url in invalid_urls:
                with self.subTest(table=table_type, url=repr(url)):
                    shortener = Shortener(table_type=table_type)
                    with self.assertRaises(ValueError):
                        shortener.shorten(url)

    def test_url_length_limit_includes_2048_character_boundary(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)
                max_length_url = "https://" + ("a" * (2048 - len("https://")))
                too_long_url = max_length_url + "a"

                self.assertEqual(len(max_length_url), 2048)
                self.assertIsInstance(shortener.shorten(max_length_url), str)
                with self.assertRaises(ValueError):
                    shortener.shorten(too_long_url)

    def test_shortener_remains_correct_after_table_growth(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)
                urls = [
                    f"https://example.com/path/{index}"
                    for index in range(40)
                ]

                codes = [shortener.shorten(url) for url in urls]

                self.assertEqual(len(set(codes)), len(codes))
                for url, code in zip(urls, codes):
                    self.assertEqual(shortener.expand(code), url)

    def test_sixty_second_url_uses_base62_code_10(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                shortener = Shortener(table_type=table_type)
                code = None

                for index in range(1, 63):
                    code = shortener.shorten(
                        f"https://example.com/path/{index}"
                    )

                self.assertEqual(code, "10")


if __name__ == "__main__":
    unittest.main()
