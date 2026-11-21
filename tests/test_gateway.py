import io
from email.message import Message
import pytest
from deploy import gateway


def handler(path="/", body=b"", headers=()):
    instance = object.__new__(gateway.Gateway)
    instance.command = "POST"
    instance.path = path
    instance.request_version = "HTTP/1.1"
    instance.headers = Message()
    for key, value in headers:
        instance.headers.add_header(key, value)
    instance.rfile = io.BytesIO(body)
    instance.wfile = io.BytesIO()
    return instance


def test_gateway_preserves_binary_body_auth_and_fixed_target(monkeypatch):
    seen = {}
    payload = b"%PDF-\x00\xff\n" * 20000

    class Response:
        status = 201

        def __init__(self):
            self.body = io.BytesIO(b'{"accepted":true}')

        def getheader(self, key, default=""):
            return default

        def getheaders(self):
            return [("Content-Type", "application/json"), ("Content-Length", "17")]

        def read(self, n):
            return self.body.read(n)

    class Connection:
        def __init__(self, host, port, timeout):
            seen.update(target=(host, port), headers=[], body=bytearray())

        def putrequest(self, method, path, **kwargs):
            seen.update(method=method, path=path)

        def putheader(self, key, value):
            seen["headers"].append((key, value))

        def endheaders(self):
            pass

        def send(self, chunk):
            seen["body"].extend(chunk)

        def getresponse(self):
            return Response()

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(gateway.http.client, "HTTPConnection", Connection)
    h = handler("/api/v1/forms/convert", payload, [("Host", "untrusted.example"), ("Authorization", "Bearer unit-test"), ("Content-Length", str(len(payload)))])
    h.forward()
    assert seen["target"] == ("formforge", 8000) and bytes(seen["body"]) == payload
    assert ("Host", "formforge:8000") in seen["headers"] and ("Host", "untrusted.example") not in seen["headers"]
    assert ("Authorization", "Bearer unit-test") in seen["headers"] and seen["closed"]
    assert b"201" in h.wfile.getvalue().split(b"\r\n", 1)[0]
    assert h.wfile.getvalue().split(b"\r\n\r\n", 1)[1] == b'{"accepted":true}'


@pytest.mark.parametrize("path", ["http://external.example/path", "//external.example/path"])
def test_gateway_is_not_an_open_proxy(path, monkeypatch):
    monkeypatch.setattr(gateway.http.client, "HTTPConnection", lambda *args, **kwargs: pytest.fail("No upstream connection should be opened"))
    h = handler(path)
    h.forward()
    assert b"400" in h.wfile.getvalue().split(b"\r\n", 1)[0]


@pytest.mark.parametrize(
    "headers", [[("Transfer-Encoding", "gzip")], [("Content-Length", "1"), ("Content-Length", "2")], [("Transfer-Encoding", "chunked"), ("Content-Length", "1")]]
)
def test_gateway_rejects_ambiguous_framing(headers, monkeypatch):
    monkeypatch.setattr(gateway.http.client, "HTTPConnection", lambda *args, **kwargs: pytest.fail("Reject before forwarding"))
    h = handler(headers=headers)
    h.forward()
    assert b"unsupported_framing" in h.wfile.getvalue()


def test_gateway_bounds_upload_before_reading_body(monkeypatch):
    monkeypatch.setattr(gateway, "MAX_BODY", 5)
    h = handler(headers=[("Content-Length", "6")])
    h.forward()
    assert b"413" in h.wfile.getvalue().split(b"\r\n", 1)[0]


def test_gateway_upstream_failure_returns_json_without_document_log(monkeypatch):
    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def putrequest(self, *args, **kwargs):
            pass

        def putheader(self, *args, **kwargs):
            pass

        def endheaders(self):
            raise OSError("unreachable")

        def close(self):
            pass

    monkeypatch.setattr(gateway.http.client, "HTTPConnection", Connection)
    h = handler()
    h.forward()
    assert b"502" in h.wfile.getvalue().split(b"\r\n", 1)[0] and b"backend_unavailable" in h.wfile.getvalue()


def test_chunked_body_dechunking_and_trailers():
    body, length = gateway.read_chunked(io.BytesIO(b"3\r\na\x00b\r\n2;extension=x\r\ncd\r\n0\r\nX-Test: ignored\r\n\r\n"))
    with body:
        assert length == 5 and body.read() == b"a\x00bcd"


@pytest.mark.parametrize("data", [b"not-hex\r\n", b"2\r\nx", b"2\r\nxy!!"])
def test_invalid_chunked_body_cannot_be_forwarded(data):
    with pytest.raises(gateway.BodyError):
        gateway.read_chunked(io.BytesIO(data))


def test_chunked_body_budget(monkeypatch):
    monkeypatch.setattr(gateway, "MAX_BODY", 2)
    with pytest.raises(gateway.BodyError) as error:
        gateway.read_chunked(io.BytesIO(b"3\r\nabc\r\n0\r\n\r\n"))
    assert error.value.status == 413
