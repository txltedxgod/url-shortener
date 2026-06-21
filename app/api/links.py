"""REST API for managing links and reading analytics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import build_qr_url, build_short_url
from app.schemas import (
    LabelCount,
    LinkAnalytics,
    LinkList,
    LinkListItem,
    LinkOut,
    MessageResponse,
    ShortenRequest,
    TimeseriesPoint,
)
from app.services import analytics as analytics_service
from app.services import links as links_service

router = APIRouter(prefix="/api", tags=["links"])


def _to_link_out(link) -> LinkOut:
    return LinkOut(
        code=link.code,
        short_url=build_short_url(link.code),
        original_url=link.original_url,
        is_active=link.is_active,
        is_custom_alias=link.is_custom_alias,
        click_count=link.click_count,
        created_at=link.created_at,
        expires_at=link.expires_at,
        qr_url=build_qr_url(link.code),
    )


@router.post(
    "/shorten",
    response_model=LinkOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short link",
)
async def shorten(
    payload: ShortenRequest,
    session: AsyncSession = Depends(get_session),
) -> LinkOut:
    try:
        link = await links_service.create_link(session, payload)
    except links_service.AliasTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This alias is already taken.",
        ) from exc
    except links_service.shortcode.CodeGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not allocate a short code, please retry.",
        ) from exc
    return _to_link_out(link)


@router.get("/links", response_model=LinkList, summary="List links")
async def list_links(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> LinkList:
    rows, total = await links_service.list_links(session, limit=limit, offset=offset)
    items = [
        LinkListItem(
            code=link.code,
            short_url=build_short_url(link.code),
            original_url=link.original_url,
            is_active=link.is_active,
            click_count=link.click_count,
            created_at=link.created_at,
            expires_at=link.expires_at,
            qr_url=build_qr_url(link.code),
        )
        for link in rows
    ]
    return LinkList(items=items, total=total, limit=limit, offset=offset)


@router.get("/links/{code}", response_model=LinkOut, summary="Get a single link")
async def get_link(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> LinkOut:
    try:
        link = await links_service.get_link(session, code)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc
    return _to_link_out(link)


@router.get(
    "/links/{code}/analytics",
    response_model=LinkAnalytics,
    summary="Analytics for a link",
)
async def link_analytics(
    code: str,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> LinkAnalytics:
    try:
        link = await links_service.get_link(session, code)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc

    bundle = await analytics_service.build_analytics(session, link, days=days)
    return LinkAnalytics(
        code=link.code,
        total_clicks=bundle.total_clicks,
        unique_visitors=bundle.unique_visitors,
        timeseries=[TimeseriesPoint(bucket=b, clicks=c) for b, c in bundle.timeseries],
        top_referrers=[LabelCount(label=label, count=c) for label, c in bundle.top_referrers],
        devices=[LabelCount(label=label, count=c) for label, c in bundle.devices],
        browsers=[LabelCount(label=label, count=c) for label, c in bundle.browsers],
        countries=[LabelCount(label=label, count=c) for label, c in bundle.countries],
    )


@router.patch(
    "/links/{code}/deactivate",
    response_model=LinkOut,
    summary="Deactivate a link",
)
async def deactivate(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> LinkOut:
    try:
        link = await links_service.set_active(session, code, active=False)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc
    return _to_link_out(link)


@router.patch(
    "/links/{code}/activate",
    response_model=LinkOut,
    summary="Re-activate a link",
)
async def activate(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> LinkOut:
    try:
        link = await links_service.set_active(session, code, active=True)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc
    return _to_link_out(link)


@router.delete(
    "/links/{code}",
    response_model=MessageResponse,
    summary="Delete a link",
)
async def delete_link(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await links_service.delete_link(session, code)
    except links_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found") from exc
    return MessageResponse(detail="deleted")
