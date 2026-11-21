"""Fixed-target local ingress for Docker's internal-network port limitation.

The document processor stays solely on the internal network. This small stdlib
gateway joins ingress/internal networks and cannot proxy arbitrary destinations.
No document logging, persistence, third-party service or new dependency.
"""

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import tempfile
import threading
import re

BACKEND = ("formforge", 8000)
MAX_BODY = int(os.environ.get("FORMFORGE_MAX_UPLOAD_MB", "20")) * 1024 * 1024 + 64 * 1024
CHUNKED_SLOTS = threading.BoundedSemaphore(2)
UPSTREAM_TIMEOUT = int(os.environ.get("FORMFORGE_PROCESSING_TIMEOUT", "90")) + 15
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade", "host"}


class BodyError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def read_chunked(stream):
    body = tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
    total = 0
    try:
        while True:
            line = stream.readline(8193)
            token = line.split(b";", 1)[0].strip()
            if len(line) > 8192 or not line.endswith(b"\r\n") or not re.fullmatch(b"[0-9a-fA-F]+", token):
                raise BodyError(400, "invalid_chunked_body")
            size = int(token, 16)
            if not size:
                trailers = 0
                while True:
                    line = stream.readline(8193)
                    trailers += len(line)
                    if not line or trailers > 16384:
                        raise BodyError(400, "invalid_trailer")
                    if line == b"\r\n":
                        break
                break
            total += size
            if total > MAX_BODY:
                raise BodyError(413, "file_too_large")
            remaining = size
            while remaining:
                chunk = stream.read(min(65536, remaining))
                if not chunk:
                    raise BodyError(400, "incomplete_body")
                body.write(chunk)
                remaining -= len(chunk)
            if stream.read(2) != b"\r\n":
                raise BodyError(400, "invalid_chunked_body")
        body.seek(0)
        return body, total
    except Exception:
        body.close()
        raise


class Gateway(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = UPSTREAM_TIMEOUT

    def log_message(self, *args):
        pass

    def error(self, status, code):
        body = json.dumps({"error": {"code": code, "message": "Żądanie bramy lokalnej nie powiodło się."}}).encode()
        self.send_response_only(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def forward(self):
        if not self.path.startswith("/") or self.path.startswith("//"):
            self.error(400, "invalid_target")
            return
        lengths = self.headers.get_all("Content-Length", [])
        encoding = self.headers.get("Transfer-Encoding", "").lower()
        if len(lengths) > 1 or encoding and (encoding != "chunked" or lengths):
            self.error(400, "unsupported_framing")
            return
        try:
            length = int(lengths[0]) if lengths else 0
        except ValueError:
            self.error(400, "invalid_length")
            return
        if length < 0 or length > MAX_BODY:
            self.error(413, "file_too_large")
            return
        buffered = None
        if encoding:
            if not CHUNKED_SLOTS.acquire(blocking=False):
                self.error(503, "upload_capacity")
                return
            try:
                buffered, length = read_chunked(self.rfile)
            except BodyError as error:
                CHUNKED_SLOTS.release()
                self.error(error.status, error.code)
                return
            except OSError, TimeoutError:
                CHUNKED_SLOTS.release()
                self.error(408, "upload_timeout")
                return
        upstream = http.client.HTTPConnection(*BACKEND, timeout=UPSTREAM_TIMEOUT)
        response_started = False
        try:
            upstream.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            upstream.putheader("Host", f"{BACKEND[0]}:{BACKEND[1]}")
            blocked = HOP | {v.strip().lower() for v in self.headers.get("Connection", "").split(",")}
            for name, value in self.headers.items():
                if name.lower() not in blocked and name.lower() != "content-length":
                    upstream.putheader(name, value)
            if lengths or encoding:
                upstream.putheader("Content-Length", str(length))
            upstream.putheader("Connection", "close")
            upstream.endheaders()
            remaining = length
            while remaining:
                chunk = (buffered or self.rfile).read(min(65536, remaining))
                if not chunk:
                    raise ConnectionError("Incomplete request body")
                upstream.send(chunk)
                remaining -= len(chunk)
            response = upstream.getresponse()
            self.send_response_only(response.status)
            response_started = True
            blocked = HOP | {v.strip().lower() for v in response.getheader("Connection", "").split(",")}
            for name, value in response.getheaders():
                if name.lower() not in blocked:
                    self.send_header(name, value)
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                while chunk := response.read(65536):
                    self.wfile.write(chunk)
        except OSError, http.client.HTTPException, ConnectionError, socket.timeout:
            if not response_started:
                try:
                    self.error(502, "backend_unavailable")
                except OSError:
                    pass
        finally:
            upstream.close()
            if buffered is not None:
                buffered.close()
                CHUNKED_SLOTS.release()
            self.close_connection = True

    do_GET = forward
    do_HEAD = forward
    do_POST = forward
    do_OPTIONS = forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Gateway).serve_forever()
