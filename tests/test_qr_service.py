"""Unit tests for the QR generator URL helper service."""

from app.services.qr_service import QRGeneratorService


def test_format_qr_svg_url_defaults_and_custom_color() -> None:
    default_url = QRGeneratorService.format_qr_svg_url("https://sho.rt/abc123")
    assert default_url == (
        "https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://sho.rt/abc123&color=000000"
    )

    branded_url = QRGeneratorService.format_qr_svg_url("https://sho.rt/xyz", fill_color="#ff5500")
    assert branded_url.endswith("&color=ff5500")
