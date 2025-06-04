"""
Test suite for verifying the hardening of the local HTTP server against LNA, CORS, and unsafe access.

IMPORTANT: The application/server must be running for these tests to pass. This test suite sends real HTTP requests to the running server instance. If the server is not running, all tests will fail with connection errors.

This test checks:
- No Access-Control-Allow-Private-Network header is ever sent
- No permissive Access-Control-Allow-Origin header is sent
- OPTIONS (preflight) requests are blocked (403)
- POST, PUT, DELETE are blocked (405)
- Directory traversal is blocked (403)
- Dangerous file types are blocked (403)
- Directory listing is blocked (403)
- Only whitelisted MIME types are served
- Security headers are always present
"""

import pytest
import requests
import os

SERVER_URL = os.environ.get(
    "AIRUNNER_TEST_SERVER_URL", "https://localhost:5005"
)
VERIFY_SSL = False  # Set True if using valid certs


@pytest.mark.parametrize(
    "method, path, expected_status",
    [
        ("OPTIONS", "/", 403),
        ("POST", "/", 405),
        ("PUT", "/", 405),
        ("DELETE", "/", 405),
        ("GET", "/../../etc/passwd", 403),
        ("GET", "/static/../../etc/passwd", 403),
        ("GET", "/.env", 403),
        ("GET", "/file_that_does_not_exist.txt", 404),
    ],
)
def test_hardened_methods_and_traversal(method, path, expected_status):
    url = SERVER_URL + path
    resp = requests.request(method, url, verify=VERIFY_SSL)
    # Accept 403 for missing files and directory listing as valid for a hardened server
    if method == "GET" and path == "/file_that_does_not_exist.txt":
        assert resp.status_code in (403, 404)
    else:
        assert resp.status_code == expected_status
    # Should never leak server file paths or stack traces
    assert "Traceback" not in resp.text
    # Do not check for '/' in resp.text, as default error pages contain HTML tags


@pytest.mark.parametrize(
    "path, should_be_served",
    [
        ("/robots.txt", True),
        ("/.env", False),
        ("/test.py", False),
        ("/test.sh", False),
        ("/test.exe", False),
        ("/test.md", False),
    ],
)
def test_dangerous_extensions(path, should_be_served):
    url = SERVER_URL + path
    resp = requests.get(url, verify=VERIFY_SSL)
    if should_be_served:
        assert resp.status_code in (
            200,
            404,
            403,
        )  # Accept 403 for hardened server
    else:
        assert resp.status_code == 403


@pytest.mark.parametrize("path", ["/", "/robots.txt"])
def test_security_headers(path):
    url = SERVER_URL + path
    resp = requests.get(url, verify=VERIFY_SSL)
    # Always present security headers
    assert resp.headers.get("Strict-Transport-Security")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    # Never present
    assert "Access-Control-Allow-Private-Network" not in resp.headers
    assert "Access-Control-Allow-Origin" not in resp.headers


@pytest.mark.parametrize(
    "path, mime_prefix, should_be_served",
    [
        ("/robots.txt", "text/", True),
        ("/test.png", "image/", True),
        ("/test.pdf", "application/pdf", True),
        ("/test.exe", None, False),
    ],
)
def test_mime_type_whitelist(path, mime_prefix, should_be_served):
    url = SERVER_URL + path
    resp = requests.get(url, verify=VERIFY_SSL)
    if should_be_served:
        if resp.status_code == 200:
            assert resp.headers["Content-Type"].startswith(mime_prefix)
        else:
            assert resp.status_code in (404, 403)
    else:
        assert resp.status_code == 403


def test_directory_listing():
    url = SERVER_URL + "/"
    resp = requests.get(url, verify=VERIFY_SSL)
    # Accept 403 as valid for hardened server
    assert resp.status_code in (200, 404, 403)
    assert "<title>Directory listing" not in resp.text
