"""The hot path: resolving a short code and redirecting."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import client_ip
from app.models import Link
from app.services import links as links_service
from app.services.analytics import ClickContext, record_click

router = APIRouter(tags=["redirect"])


@router.get("/{code}", summary="Redirect to the original URL", include_in_schema=False)
async def redirect(
    code: str,
    request: Request,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Response:
    original_url = await links_service.resolve_code(session, code)
    if original_url is None:
        return Response(
            content="Short link not found or no longer active.",
            status_code=status.HTTP_404_NOT_FOUND,
            media_type="text/plain",
        )

    # We need the link id for analytics but must avoid blocking the redirect.
    # The id lookup is cheap (indexed) and only the persistence is backgrounded.
    link_id = await session.scalar(select(Link.id).where(Link.code == code))
    if link_id is not None:
        background.add_task(
            record_click,
            ClickContext(
                link_id=link_id,
                ip_address=client_ip(request),
                referrer=request.headers.get("referer"),
                user_agent=request.headers.get("user-agent"),
            ),
        )

    return RedirectResponse(
        url=original_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
