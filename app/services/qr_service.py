"""
QR Code Generator & In-Memory SVG Renderer
"""

class QRGeneratorService:
    @staticmethod
    def format_qr_svg_url(short_url: str, fill_color: str = "#000000") -> str:
        return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={short_url}&color={fill_color.lstrip('#')}"
