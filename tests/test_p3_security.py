"""P3 security hardening tests: throttles, SSRF guards, production config."""

import pytest
from app.core.config import Settings
from app.core.request_throttle import InMemoryRequestThrottle
from app.main import app
from app.utils.image_validation import validate_product_image_url
from fastapi.testclient import TestClient
from pydantic import ValidationError

client = TestClient(app)


class TestRequestThrottle:
    def test_in_memory_request_throttle_limits(self):
        throttle = InMemoryRequestThrottle()

        async def scenario():
            for _ in range(3):
                assert await throttle.check_and_increment("ip:1", 3, 60) is None
            retry_after = await throttle.check_and_increment("ip:1", 3, 60)
            assert retry_after is not None and retry_after > 0

        import asyncio

        asyncio.run(scenario())


class TestPublicEndpointThrottles:
    def test_contact_form_rate_limited(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.PUBLIC_THROTTLE_CONTACT_MAX", 2)
        monkeypatch.setattr("app.core.config.settings.PUBLIC_THROTTLE_CONTACT_WINDOW", 300)
        payload = {
            "full_name": "کاربر",
            "phone": "09124444444",
            "subject": "سوال",
            "message": "پیام تست برای فرم تماس با ما",
        }
        assert client.post("/api/v1/contact", json=payload).status_code == 200
        assert client.post("/api/v1/contact", json=payload).status_code == 200
        blocked = client.post("/api/v1/contact", json=payload)
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "RATE_LIMITED"
        assert "Retry-After" in blocked.headers

    def test_tracking_rate_limited(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.PUBLIC_THROTTLE_TRACKING_MAX", 2)
        monkeypatch.setattr("app.core.config.settings.PUBLIC_THROTTLE_TRACKING_WINDOW", 60)
        assert client.get("/api/v1/orders/track/KZ-NOTFOUND01").status_code == 404
        assert client.get("/api/v1/orders/track/KZ-NOTFOUND02").status_code == 404
        blocked = client.get("/api/v1/orders/track/KZ-NOTFOUND03")
        assert blocked.status_code == 429

    def test_plp_search_rate_limited(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.PUBLIC_THROTTLE_PLP_MAX", 2)
        monkeypatch.setattr("app.core.config.settings.PUBLIC_THROTTLE_PLP_WINDOW", 60)
        assert client.get("/api/v1/products/?search=TEST").status_code == 200
        assert client.get("/api/v1/products/?search=TEST2").status_code == 200
        blocked = client.get("/api/v1/products/?search=TEST3")
        assert blocked.status_code == 429


class TestImageUrlSsrfGuard:
    def test_blocks_localhost_urls(self):
        with pytest.raises(ValueError, match="internal or private"):
            validate_product_image_url("http://localhost/image.jpg", resolve_dns=False)

    def test_blocks_private_ipv4_urls(self):
        with pytest.raises(ValueError, match="internal or private"):
            validate_product_image_url("https://192.168.1.10/photo.png", resolve_dns=False)

    def test_blocks_metadata_host(self):
        with pytest.raises(ValueError, match="internal or private"):
            validate_product_image_url(
                "https://metadata.google.internal/logo.webp", resolve_dns=False
            )

    def test_allows_public_https_image(self, monkeypatch):
        monkeypatch.setattr(
            "app.utils.image_validation.socket.getaddrinfo",
            lambda *args, **kwargs: [
                (0, 0, 0, "", ("203.0.113.10", 0)),
            ],
        )
        # 203.0.113.0/24 is TEST-NET and blocked — use a public-looking address.
        monkeypatch.setattr(
            "app.utils.image_validation.socket.getaddrinfo",
            lambda *args, **kwargs: [
                (0, 0, 0, "", ("8.8.8.8", 0)),
            ],
        )
        url = validate_product_image_url("https://cdn.example.com/products/a.jpg")
        assert url.startswith("https://")

    def test_blocks_dns_rebinding_to_private(self, monkeypatch):
        monkeypatch.setattr(
            "app.utils.image_validation.socket.getaddrinfo",
            lambda *args, **kwargs: [
                (0, 0, 0, "", ("10.0.0.5", 0)),
            ],
        )
        with pytest.raises(ValueError, match="internal or private"):
            validate_product_image_url("https://evil.example.com/photo.png")

    def test_rejects_svg_extension(self):
        with pytest.raises(ValueError, match="image file"):
            validate_product_image_url(
                "https://cdn.example.com/logo.svg", resolve_dns=False
            )


class TestCookieCsrfOrigin:
    def test_cookie_post_without_origin_rejected(self, monkeypatch):
        monkeypatch.setattr("app.core.security_middleware.settings.DEBUG", False)
        client.cookies.set("karzar_access", "dummy-token")
        try:
            resp = client.post(
                "/api/v1/contact",
                json={
                    "full_name": "کاربر",
                    "phone": "09125555555",
                    "subject": "سوال",
                    "message": "پیام تست برای فرم تماس با ما",
                },
            )
            assert resp.status_code == 403
            assert resp.json()["error_code"] == "FORBIDDEN"
        finally:
            client.cookies.clear()

    def test_cookie_post_with_disallowed_origin_rejected(self, monkeypatch):
        monkeypatch.setattr("app.core.security_middleware.settings.DEBUG", False)
        monkeypatch.setattr(
            "app.core.security_middleware._origin_allowed",
            lambda origin: False,
        )
        client.cookies.set("karzar_access", "dummy-token")
        try:
            resp = client.post(
                "/api/v1/contact",
                json={
                    "full_name": "کاربر",
                    "phone": "09125555556",
                    "subject": "سوال",
                    "message": "پیام تست برای فرم تماس با ما",
                },
                headers={"Origin": "https://evil.example"},
            )
            assert resp.status_code == 403
        finally:
            client.cookies.clear()

    def test_cookie_post_same_origin_passes_csrf(self, monkeypatch):
        monkeypatch.setattr("app.core.security_middleware.settings.DEBUG", False)
        client.cookies.set("karzar_access", "dummy-token")
        try:
            resp = client.post(
                "/api/v1/contact",
                json={
                    "full_name": "کاربر",
                    "phone": "09125555557",
                    "subject": "سوال",
                    "message": "پیام تست برای فرم تماس با ما",
                },
                headers={"Origin": "http://testserver"},
            )
            assert resp.status_code != 403
        finally:
            client.cookies.clear()


class TestProductionConfigGuards:
    def _base_kwargs(self) -> dict:
        return {
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_SERVER": "localhost",
            "POSTGRES_DB": "test",
            "SECRET_KEY": "x" * 40,
            "ADMIN_STEP_UP_PIN": "9382746150",
            "DEBUG": False,
            "REDIS_HOST": "127.0.0.1",
            "OTP_DEV_ECHO": False,
            "CORS_ORIGINS": "https://shop.example.com",
        }

    def test_rejects_otp_dev_echo_in_production(self):
        kwargs = self._base_kwargs()
        kwargs["OTP_DEV_ECHO"] = True
        with pytest.raises(ValidationError, match="OTP_DEV_ECHO"):
            Settings(**kwargs)

    def test_rejects_wildcard_cors_in_production(self):
        kwargs = self._base_kwargs()
        kwargs["CORS_ORIGINS"] = "*"
        with pytest.raises(ValidationError, match="CORS_ORIGINS"):
            Settings(**kwargs)

    def test_requires_redis_in_production(self):
        kwargs = self._base_kwargs()
        kwargs["REDIS_HOST"] = None
        with pytest.raises(ValidationError, match="REDIS_HOST"):
            Settings(**kwargs)

    def test_rejects_debug_true_when_app_env_production(self):
        kwargs = self._base_kwargs()
        kwargs.update(
            {
                "APP_ENV": "production",
                "DEBUG": True,
                "TRUSTED_HOSTS": "api.example.com",
                "ENFORCE_HTTPS": True,
                "PAYMENT_PROVIDER": "zarinpal",
                "SMS_PROVIDER": "kavenegar",
                "SMS_KAVENEGAR_API_KEY": "test-key",
                "ENABLE_API_DOCS": False,
            }
        )
        with pytest.raises(ValidationError, match="DEBUG"):
            Settings(**kwargs)

    def test_production_requires_trusted_hosts_and_https(self):
        kwargs = self._base_kwargs()
        kwargs.update(
            {
                "APP_ENV": "production",
                "PAYMENT_PROVIDER": "zarinpal",
                "SMS_PROVIDER": "kavenegar",
                "SMS_KAVENEGAR_API_KEY": "test-key",
                "ENABLE_API_DOCS": False,
                "ENFORCE_HTTPS": True,
                "TRUSTED_HOSTS": "",
            }
        )
        with pytest.raises(ValidationError, match="TRUSTED_HOSTS"):
            Settings(**kwargs)


class TestLogoutRevokesAccessToken:
    def test_logout_invalidates_existing_access_token(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.OTP_DEV_ECHO", True)
        request = client.post("/api/v1/auth/otp/request", json={"phone": "09128887777"})
        code = request.json()["dev_code"]
        verify = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "09128887777", "code": code},
        )
        headers = {"Authorization": f"Bearer {verify.json()['access_token']}"}
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

        logout = client.post("/api/v1/auth/logout", headers=headers)
        assert logout.status_code == 200

        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


class TestRequestBodySizeLimit:
    def test_rejects_oversized_content_length(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.MAX_REQUEST_BODY_BYTES", 32)
        response = client.post(
            "/api/v1/contact",
            json={"full_name": "x" * 100, "phone": "0912", "subject": "s", "message": "m"},
            headers={"Content-Length": "99999"},
        )
        assert response.status_code == 413
