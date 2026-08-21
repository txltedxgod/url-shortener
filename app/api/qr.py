"""QR code generation for short links."""

from __future__ import annotations

import io
import re

import qrcode
import qrcode.constants
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from PIL import ImageColor
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import build_short_url
from app.services import links as links_service

router = APIRouter(prefix="/api", tags=["qr"])


def validate_color(color: str) -> str:
    """Validate and normalize a color string for PIL."""
    if re.match(r"^[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$", color):
        color = f"#{color}"
    try:
        ImageColor.getrgb(color)
        return color
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid color format: {color}",
        )


@router.get(
    "/links/{code}/qr",
    summary="PNG QR code for a short link",
    responses={200: {"content": {"image/png": {}}}},
)
async def link_qr(
    code: str,
    box_size: int = Query(default=10, ge=2, le=40),
    border: int = Query(default=2, ge=1, le=16),
    fg_color: str = Query(default="black", description="Foreground color (name or hex)"),
    bg_color: str = Query(default="white", description="Background color (name or hex)"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await links_service.get_link(session, code)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc

    valid_fg = validate_color(fg_color)
    valid_bg = validate_color(bg_color)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(build_short_url(code))
    qr.make(fit=True)
    img = qr.make_image(fill_color=valid_fg, back_color=valid_bg)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
