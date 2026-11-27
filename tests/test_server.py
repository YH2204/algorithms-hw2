import http.client
import os
import sys
import threading
import unittest
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import ShortenerHTTPServer


TABLE_TYPES = ("chaining", "linear")
TEST_URL = "https://origin.example/path"


class TestShortenerHTTPServer(unittest.TestCase):
    def request(self, server, method, path, headers=None, body=None):
        connection = http.client.HTTPConnection(*server.server_address)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status = response.status
        response_headers = response.headers
        response_body = response.read().decode("utf-8")
        connection.close()
        return status, response_headers, response_body

    def start_server(self, table_type):
        server = ShortenerHTTPServer(("127.0.0.1", 0), table_type)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def stop_server(self, server, thread):
        server.shutdown()
        server.server_close()
        thread.join()

    def test_home_page_has_url_form(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                server, thread = self.start_server(table_type)
                try:
                    status, headers, body = self.request(server, "GET", "/")
                finally:
                    self.stop_server(server, thread)

                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["Content-Type"])
                self.assertIn('action="/shorten"', body)
                self.assertIn('name="url"', body)

    def test_shorten_uses_proxy_headers_and_code_redirects(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                server, thread = self.start_server(table_type)
                try:
                    status, _, body = self.request(
                        server,
                        "POST",
                        "/shorten",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "X-Forwarded-Host": "short.example:8443",
                            "X-Forwarded-Proto": "https",
                        },
                        body=urlencode({"url": TEST_URL}),
                    )
                    redirect_status, redirect_headers, _ = self.request(
                        server,
                        "GET",
                        "/1",
                    )
                finally:
                    self.stop_server(server, thread)

                self.assertEqual(status, 200)
                self.assertIn("https://short.example:8443/1", body)
                self.assertEqual(redirect_status, 302)
                self.assertEqual(redirect_headers["Location"], TEST_URL)

    def test_invalid_url_returns_400_and_unknown_code_returns_404(self):
        server, thread = self.start_server("chaining")
        try:
            invalid_status, _, _ = self.request(
                server,
                "POST",
                "/shorten",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                body=urlencode({"url": "ftp://invalid.example"}),
            )
            missing_status, _, _ = self.request(server, "GET", "/unknown")
        finally:
            self.stop_server(server, thread)

        self.assertEqual(invalid_status, 400)
        self.assertEqual(missing_status, 404)

    def test_table_shows_chains_hash_steps_and_linear_visit_counts(self):
        for table_type in TABLE_TYPES:
            with self.subTest(table=table_type):
                server, thread = self.start_server(table_type)
                try:
                    self.request(
                        server,
                        "POST",
                        "/shorten",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        body=urlencode({"url": TEST_URL}),
                    )
                    status, _, body = self.request(
                        server,
                        "GET",
                        "/table",
                        headers={
                            "X-Forwarded-Host": "short.example",
                            "X-Forwarded-Proto": "https",
                        },
                    )
                finally:
                    self.stop_server(server, thread)

                self.assertEqual(status, 200)
                self.assertIn(TEST_URL, body)
                self.assertIn("https://short.example/1", body)
                self.assertIn("호너 해시 계산 과정", body)
                self.assertIn("(31 ×", body)
                if table_type == "chaining":
                    self.assertIn("연결 리스트", body)
                    self.assertIn("→", body)
                else:
                    self.assertIn("방문한 슬롯", body)


if __name__ == "__main__":
    unittest.main()
