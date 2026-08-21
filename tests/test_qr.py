import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.links import LinkNotFoundError
from app.models import Link
import datetime as dt

client = TestClient(app)

@pytest.fixture
def mock_get_link():
    with patch("app.api.qr.links_service.get_link") as mock:
        yield mock

def _make_mock_link():
    return Link(
        id=1,
        code="abcd12",
        original_url="http://example.com",
        is_active=True,
        is_custom_alias=False,
        created_at=dt.datetime.now(),
        expires_at=None,
    )

def test_default_qr_code(mock_get_link):
    mock_get_link.return_value = _make_mock_link()
    response = client.get("/api/links/abcd12/qr")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b'\x89PNG\r\n\x1a\n')

def test_custom_colors(mock_get_link):
    mock_get_link.return_value = _make_mock_link()
    response = client.get("/api/links/abcd12/qr?fg_color=ff0000&bg_color=000000")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

def test_custom_colors_names(mock_get_link):
    mock_get_link.return_value = _make_mock_link()
    response = client.get("/api/links/abcd12/qr?fg_color=red&bg_color=blue")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

def test_invalid_color(mock_get_link):
    mock_get_link.return_value = _make_mock_link()
    response = client.get("/api/links/abcd12/qr?fg_color=notacolor")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid color format: notacolor"

def test_missing_short_url(mock_get_link):
    mock_get_link.side_effect = LinkNotFoundError("notfound")
    response = client.get("/api/links/notfound/qr")
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"
