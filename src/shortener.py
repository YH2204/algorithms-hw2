"""In-memory URL shortener backed by the project's hash tables."""

import unicodedata
from urllib.parse import urlsplit

from base62 import encode
from hash_table import ChainingHashTable, LinearProbingHashTable


class Shortener:
    def __init__(self, table_type="chaining"):
        if table_type == "chaining":
            table_class = ChainingHashTable
        elif table_type == "linear":
            table_class = LinearProbingHashTable
        else:
            raise ValueError("table_type은 'chaining' 또는 'linear'여야 합니다")

        self.table_type = table_type
        self.url_to_code = table_class()
        self.code_to_url = table_class()
        self._next_id = 1

    @staticmethod
    def _normalize_url(url):
        if not isinstance(url, str):
            raise ValueError("잘못된 URL입니다")

        normalized = url.strip()
        if not normalized or len(normalized) > 2048:
            raise ValueError("잘못된 URL입니다")
        if any(
            character.isspace() or unicodedata.category(character) == "Cc"
            for character in normalized
        ):
            raise ValueError("잘못된 URL입니다")

        try:
            parsed = urlsplit(normalized)
            hostname = parsed.hostname
            parsed.port
        except ValueError:
            raise ValueError("잘못된 URL입니다") from None

        if parsed.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError("잘못된 URL입니다")
        return normalized

    def shorten(self, url):
        normalized = self._normalize_url(url)
        existing_code = self.url_to_code.get(normalized)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._next_id += 1
        self.url_to_code.put(normalized, code)
        self.code_to_url.put(code, normalized)
        return code

    def expand(self, code):
        return self.code_to_url.get(code)
