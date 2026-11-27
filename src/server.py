"""HTTP interface for the in-memory URL shortener."""

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, unquote, urlsplit

from hash_table import ChainingHashTable
from shortener import Shortener


MAX_FORM_BYTES = 16_384


def _escape(value):
    return html.escape(str(value), quote=True)


def _request_origin(handler):
    forwarded_host = handler.headers.get("X-Forwarded-Host", "")
    host = forwarded_host.split(",", 1)[0].strip()
    if not host:
        host = handler.headers.get("Host") or handler.server.server_name

    forwarded_proto = handler.headers.get("X-Forwarded-Proto", "")
    protocol = forwarded_proto.split(",", 1)[0].strip().lower()
    if protocol not in ("http", "https"):
        protocol = "http"
    return f"{protocol}://{host}"


def _page(title, content):
    return (
        "<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_escape(title)}</title>"
        "<style>"
        "body{font:16px system-ui,sans-serif;max-width:1000px;margin:2rem auto;"
        "padding:0 1rem;color:#222}input[type=url]{width:min(100%,40rem);"
        "padding:.6rem}button{padding:.6rem 1rem}table{border-collapse:collapse;"
        "width:100%;margin:1rem 0}th,td{border:1px solid #bbb;padding:.5rem;"
        "text-align:left;vertical-align:top;overflow-wrap:anywhere}code{"
        "overflow-wrap:anywhere}.chain{display:flex;align-items:flex-start;"
        "flex-wrap:wrap;gap:.5rem}.node{border:1px solid #bbb;padding:.75rem;"
        "min-width:12rem;max-width:36rem}.arrow{padding-top:1rem}"
        "</style><body>"
        f"<h1>{_escape(title)}</h1>{content}</body></html>"
    )


def _render_hash_details(key, capacity):
    value = 0
    rows = []
    for character in key:
        previous = value
        value = (31 * value + ord(character)) % capacity
        rows.append(
            "<tr>"
            f"<td>{_escape(character)}</td>"
            f"<td>{ord(character)}</td>"
            f"<td>(31 × {previous} + {ord(character)}) mod {capacity}</td>"
            f"<td>{value}</td>"
            "</tr>"
        )
    return (
        "<details><summary>호너 해시 계산 과정</summary>"
        f"<p>각 문자를 처리한 뒤 칸 수 {capacity}로 나머지를 구합니다. "
        f"최종 칸: <strong>{value}</strong></p>"
        "<table><thead><tr><th>문자</th><th>코드 포인트</th>"
        "<th>계산</th><th>결과</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table></details>"
    )


def _render_node(key, code, origin, capacity):
    short_url = f"{origin}/{code}"
    return (
        '<div class="node">'
        f"<p><strong>URL 키</strong><br><code>{_escape(key)}</code></p>"
        f"<p><strong>짧은 코드</strong>: {_escape(code)}</p>"
        f'<p><strong>짧은 링크</strong>: <a href="{_escape(short_url)}">'
        f"{_escape(short_url)}</a></p>"
        f"{_render_hash_details(key, capacity)}"
        "</div>"
    )


def _render_chaining_table(table, origin):
    rows = []
    capacity = len(table.buckets)
    for index, head in enumerate(table.buckets):
        nodes = []
        node = head
        while node is not None:
            nodes.append(_render_node(node.key, node.value, origin, capacity))
            node = node.next
        chain = '<span class="arrow">∅</span>'
        if nodes:
            chain = '<span class="arrow">→</span>'.join(nodes)
        rows.append(f"<tr><th>{index}</th><td><div class=\"chain\">{chain}</div></td></tr>")
    return (
        "<p>개별 체이닝 해시 테이블: 칸별 연결 리스트</p>"
        "<table><thead><tr><th>칸</th><th>연결 리스트 (URL 키 → 짧은 코드 "
        "→ 짧은 링크)</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table>"
    )


def _render_linear_table(table, origin):
    rows = []
    capacity = len(table.slots)
    for index, entry in enumerate(table.slots):
        if entry is None:
            display = "비어 있음"
        elif isinstance(entry, tuple):
            key, code = entry
            found, _, visits = table.find(key)
            node = _render_node(key, code, origin, capacity)
            display = (
                f"{node}<p>탐색 시작부터 이 키까지 방문한 슬롯: "
                f"{visits if found else 0}</p>"
            )
        else:
            display = "삭제 표시"
        rows.append(f"<tr><th>{index}</th><td>{display}</td></tr>")
    return (
        "<p>선형 탐지 해시 테이블: 각 저장 키의 탐색 비용은 시작 슬롯부터 "
        "해당 키까지 방문한 슬롯 수입니다.</p>"
        "<table><thead><tr><th>슬롯</th><th>내용</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table>"
    )


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    def _send_html(self, status, document):
        body = document.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_page(self, status, message):
        self._send_html(status, _page("오류", f"<p>{_escape(message)}</p><p><a href=\"/\">돌아가기</a></p>"))

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            content = (
                '<form method="post" action="/shorten">'
                '<label for="url">줄일 URL</label><br>'
                '<input type="url" id="url" name="url" required '
                'maxlength="2048" placeholder="https://example.com">'
                '<button type="submit">줄이기</button></form>'
                '<p><a href="/table">현재 해시 테이블 보기</a></p>'
            )
            self._send_html(200, _page("URL 단축기", content))
            return

        if path == "/table":
            table = self.server.shortener.url_to_code
            origin = _request_origin(self)
            if isinstance(table, ChainingHashTable):
                content = _render_chaining_table(table, origin)
            else:
                content = _render_linear_table(table, origin)
            self._send_html(200, _page("해시 테이블", content))
            return

        code = unquote(path[1:]) if path.startswith("/") else ""
        if not code or "/" in code:
            self._send_error_page(404, "요청한 짧은 링크를 찾을 수 없습니다.")
            return
        url = self.server.shortener.expand(code)
        if url is None:
            self._send_error_page(404, "요청한 짧은 링크를 찾을 수 없습니다.")
            return
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if urlsplit(self.path).path != "/shorten":
            self._send_error_page(404, "요청한 페이지를 찾을 수 없습니다.")
            return
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            self._send_error_page(400, "폼 데이터가 올바르지 않습니다.")
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            content_length = -1
        if content_length < 0 or content_length > MAX_FORM_BYTES:
            self._send_error_page(400, "폼 데이터 크기가 올바르지 않습니다.")
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
            fields = parse_qsl(body, keep_blank_values=True, strict_parsing=False)
            url = next(value for name, value in fields if name == "url")
            code = self.server.shortener.shorten(url)
        except (UnicodeDecodeError, StopIteration, ValueError):
            self._send_error_page(400, "올바른 http 또는 https URL을 입력해 주세요.")
            return

        short_url = f"{_request_origin(self)}/{code}"
        content = (
            "<p>짧은 링크가 준비되었습니다.</p>"
            f'<p><a href="{_escape(short_url)}">{_escape(short_url)}</a></p>'
            '<p><a href="/">다른 URL 줄이기</a></p>'
        )
        self._send_html(200, _page("단축 결과", content))


class ShortenerHTTPServer(ThreadingHTTPServer):
    def __init__(self, address, table_type="chaining"):
        super().__init__(address, ShortenerRequestHandler)
        self.shortener = Shortener(table_type=table_type)


def main():
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--table",
        choices=("chaining", "linear"),
        default="chaining",
    )
    arguments = parser.parse_args()

    server = ShortenerHTTPServer((arguments.host, arguments.port), arguments.table)
    print(
        f"URL shortener listening on http://{arguments.host}:{arguments.port} "
        f"({arguments.table})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping URL shortener.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
