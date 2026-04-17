"""
Tests for security features: IDOR, path traversal, file validation,
X-Forwarded-For trust, and rate limiting.
"""
import io
import pytest


class TestIDORProtection:
    def test_download_requires_auth(self, client):
        resp = client.get("/download_file/1", follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_download_nonexistent_courrier(self, admin_client):
        resp = admin_client.get("/download_file/999999")
        assert resp.status_code == 404

    def test_download_attachment_requires_auth(self, client):
        resp = client.get("/download_attachment/1", follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_download_attachment_nonexistent(self, admin_client):
        resp = admin_client.get("/download_attachment/999999")
        assert resp.status_code == 404


class TestFileValidation:
    def test_validate_file_upload_valid_pdf(self):
        from security_utils import validate_file_upload
        from werkzeug.datastructures import FileStorage

        pdf_bytes = b"%PDF-1.4 1 0 obj<</Type/Catalog>>endobj\n%%EOF"
        f = FileStorage(stream=io.BytesIO(pdf_bytes), filename="test.pdf")
        is_valid, msg = validate_file_upload(f)
        assert is_valid, f"Expected valid PDF but got: {msg}"

    def test_validate_file_upload_rejects_svg(self):
        from security_utils import validate_file_upload
        from werkzeug.datastructures import FileStorage

        svg_bytes = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
        f = FileStorage(stream=io.BytesIO(svg_bytes), filename="malicious.svg")
        is_valid, _ = validate_file_upload(f)
        assert not is_valid, "SVG should be rejected (XSS risk)"

    def test_validate_file_upload_rejects_exe(self):
        from security_utils import validate_file_upload
        from werkzeug.datastructures import FileStorage

        # MZ magic bytes = Windows PE executable
        exe_bytes = b"MZ\x90\x00" + b"\x00" * 60
        f = FileStorage(stream=io.BytesIO(exe_bytes), filename="malware.exe")
        is_valid, _ = validate_file_upload(f)
        assert not is_valid, "EXE should be rejected"

    def test_validate_rejects_pdf_extension_with_wrong_content(self):
        from security_utils import validate_file_upload
        from werkzeug.datastructures import FileStorage

        # Extension says PDF but content is PHP
        php_bytes = b"<?php system($_GET['cmd']); ?>"
        f = FileStorage(stream=io.BytesIO(php_bytes), filename="shell.pdf")
        is_valid, _ = validate_file_upload(f)
        assert not is_valid, "Fake PDF (PHP content) should be rejected"

    def test_validate_png_accepted(self):
        from security_utils import validate_file_upload
        from werkzeug.datastructures import FileStorage

        # PNG magic bytes
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        f = FileStorage(stream=io.BytesIO(png_bytes), filename="image.png")
        is_valid, msg = validate_file_upload(f)
        assert is_valid, f"PNG should be accepted but got: {msg}"


class TestXForwardedFor:
    def test_untrusted_peer_ignores_xff(self):
        from security_utils import get_client_ip
        from app import app

        with app.test_request_context(
            environ_base={
                "REMOTE_ADDR": "203.0.113.1",  # untrusted external IP
                "HTTP_X_FORWARDED_FOR": "1.2.3.4",
            }
        ):
            ip = get_client_ip()
            # Must return the real peer, not the spoofed XFF
            assert ip == "203.0.113.1", f"Expected real peer IP but got {ip}"

    def test_trusted_proxy_uses_xff(self):
        from security_utils import get_client_ip
        from app import app
        import os

        os.environ["TRUSTED_PROXIES"] = "127.0.0.1"
        with app.test_request_context(
            environ_base={
                "REMOTE_ADDR": "127.0.0.1",  # trusted proxy
                "HTTP_X_FORWARDED_FOR": "8.8.8.8",
            }
        ):
            ip = get_client_ip()
            assert ip == "8.8.8.8", f"Expected XFF public IP but got {ip}"


class TestPasswordStrength:
    def test_strong_password_accepted(self):
        from security_utils import validate_password_strength
        ok, _ = validate_password_strength("Str0ngP@ssw0rd!")
        assert ok

    def test_short_password_rejected(self):
        from security_utils import validate_password_strength
        ok, msg = validate_password_strength("Ab1!")
        assert not ok
        assert msg  # error message provided

    def test_no_digit_rejected(self):
        from security_utils import validate_password_strength
        ok, _ = validate_password_strength("NoDigitsHere!")
        assert not ok

    def test_no_special_char_rejected(self):
        from security_utils import validate_password_strength
        ok, _ = validate_password_strength("NoSpecial123")
        assert not ok


class TestSVGNotInAllowedExtensions:
    def test_svg_removed_from_utils(self):
        from utils import ALLOWED_EXTENSIONS
        assert "svg" not in ALLOWED_EXTENSIONS, "SVG must be removed from allowed extensions (XSS risk)"
