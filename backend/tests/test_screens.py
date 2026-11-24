import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestScreenURLHandlers:
    """Tests that all frontend HTML screens and static assets are served properly."""

    @pytest.mark.parametrize(
        "url_path,expected_title_fragment",
        [
            ("/", "Dashboard"),
            ("/index.html", "Dashboard"),
            ("/dashboard", "Dashboard"),
            ("/dashboard.html", "Dashboard"),
            ("/live-console", "Live Support Console"),
            ("/live-console.html", "Live Support Console"),
            ("/session-config", "Session Configuration"),
            ("/session-config.html", "Session Configuration"),
            ("/session-history", "Session History"),
            ("/session-history.html", "Session History"),
            ("/knowledge-base", "Knowledge Base"),
            ("/knowledge-base.html", "Knowledge Base"),
            ("/coaching-report", "Coaching Report"),
            ("/coaching-report.html", "Coaching Report"),
        ],
    )
    def test_screen_endpoints_return_200_html(self, url_path, expected_title_fragment):
        response = client.get(url_path, follow_redirects=True)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert expected_title_fragment.lower() in response.text.lower()

    def test_css_asset_served(self):
        response = client.get("/css/style.css")
        assert response.status_code == 200
        assert any(t in response.headers.get("content-type", "") for t in ["text/css", "text/plain"])

    def test_js_asset_served(self):
        response = client.get("/js/api.js")
        assert response.status_code == 200
        assert any(t in response.headers.get("content-type", "") for t in ["javascript", "text/plain"])

    def test_nonexistent_screen_returns_404(self):
        response = client.get("/nonexistent-screen.html", follow_redirects=True)
        assert response.status_code == 404
