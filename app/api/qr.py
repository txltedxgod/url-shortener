"""QR code generation for short links."""

from __future__ import annotations

import io

import qrcode
import qrcode.constants
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import build_short_url
from app.services import links as links_service

router = APIRouter(prefix="/api", tags=["qr"])


@router.get(
    "/links/{code}/qr",
    summary="PNG QR code for a short link",
    responses={200: {"content": {"image/png": {}}}},
)
async def link_qr(
    code: str,
    box_size: int = Query(default=10, ge=2, le=40),
    border: int = Query(default=2, ge=1, le=16),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await links_service.get_link(session, code)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(build_short_url(code))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
