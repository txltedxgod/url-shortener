"""IP geolocation via MaxMind GeoLite2.

The reader is optional: if no database is configured (or the file is missing)
the resolver silently returns empty geo data. This keeps the service runnable
out of the box while allowing full geo analytics in production by mounting a
GeoLite2-City.mmdb file and setting GEOIP_DB_PATH.
"""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass

import geoip2.database
import geoip2.errors

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class GeoResult:
    country: str | None = None
    country_code: str | None = None
    city: str | None = None


class GeoIPResolver:
    def __init__(self, db_path: str):
        self._reader: geoip2.database.Reader | None = None
        if db_path and os.path.isfile(db_path):
            try:
                self._reader = geoip2.database.Reader(db_path)
                logger.info("GeoIP database loaded from %s", db_path)
            except Exception as exc:  # pragma: no cover - depends on file
                logger.warning("Failed to load GeoIP database: %s", exc)
        else:
            logger.info("GeoIP disabled (no database configured)")

    @property
    def enabled(self) -> bool:
        return self._reader is not None

    @staticmethod
    def _is_public(ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return not (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )

    def resolve(self, ip: str | None) -> GeoResult:
        if not self._reader or not ip or not self._is_public(ip):
            return GeoResult()
        try:
            response = self._reader.city(ip)
        except (geoip2.errors.AddressNotFoundError, ValueError):
            return GeoResult()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("GeoIP lookup failed for %s: %s", ip, exc)
            return GeoResult()
        return GeoResult(
            country=response.country.name,
            country_code=response.country.iso_code,
            city=response.city.name,
        )

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()
            self._reader = None


_resolver: GeoIPResolver | None = None


def get_geoip() -> GeoIPResolver:
    global _resolver
    if _resolver is None:
        _resolver = GeoIPResolver(settings.geoip_db_path)
    return _resolver


def close_geoip() -> None:
    global _resolver
    if _resolver is not None:
        _resolver.close()
        _resolver = None
