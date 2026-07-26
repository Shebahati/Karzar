"""Ensure one Hesabfa contact per customer (create/link on demand)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.hesabfa import HesabfaContactMapping
from app.services.hesabfa.client import (
    CONTACT_TYPE_CUSTOMER,
    HesabfaClient,
    get_hesabfa_client,
)

logger = get_logger(__name__)


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    return digits


async def ensure_hesabfa_contact(
    db: AsyncSession,
    *,
    phone: str,
    full_name: str,
    user_id: int | None = None,
    company_name: str | None = None,
    client: HesabfaClient | None = None,
) -> HesabfaContactMapping:
    """Return existing mapping or create/link a Hesabfa contact for this phone."""
    api = client or get_hesabfa_client()
    phone_norm = _normalize_phone(phone)
    if not phone_norm:
        raise ValueError("Customer phone is required for Hesabfa contact")

    existing = (
        await db.execute(
            select(HesabfaContactMapping).where(
                HesabfaContactMapping.customer_phone == phone_norm
            )
        )
    ).scalars().first()
    if existing:
        if user_id and existing.user_id is None:
            existing.user_id = user_id
        if full_name:
            existing.customer_name = full_name
        await db.flush()
        return existing

    # Prefer linking an existing Hesabfa contact with the same mobile.
    found_code: str | None = None
    page = await api.get_contacts(
        take=5,
        filters=[{"property": "Mobile", "operator": "=", "value": phone_norm}],
    )
    for item in page.get("List") or []:
        code = str(item.get("Code") or item.get("code") or "").strip()
        if code:
            found_code = code
            break

    if not found_code:
        # Also try without leading zero variants.
        alt = phone_norm[1:] if phone_norm.startswith("0") else f"0{phone_norm}"
        if alt != phone_norm:
            page = await api.get_contacts(
                take=5,
                filters=[{"property": "Mobile", "operator": "=", "value": alt}],
            )
            for item in page.get("List") or []:
                code = str(item.get("Code") or item.get("code") or "").strip()
                if code:
                    found_code = code
                    break

    name = (full_name or company_name or phone_norm).strip() or phone_norm
    parts = name.split(None, 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    if found_code:
        hesabfa_code = found_code
    else:
        saved = await api.save_contact(
            {
                "name": name,
                "firstName": first_name,
                "lastName": last_name,
                "contactType": CONTACT_TYPE_CUSTOMER,
                "mobile": phone_norm,
                "company": company_name or "",
                "tag": f"karzar:phone:{phone_norm}",
                "active": True,
            }
        )
        hesabfa_code = str(saved.get("Code") or saved.get("code") or "").strip()
        if not hesabfa_code:
            raise ValueError("Hesabfa contact save returned no Code")

    mapping = HesabfaContactMapping(
        user_id=user_id,
        customer_phone=phone_norm,
        customer_name=full_name,
        hesabfa_code=hesabfa_code,
        last_synced_at=datetime.now(UTC),
    )
    db.add(mapping)
    await db.flush()
    logger.info(
        "Hesabfa contact ensured phone=%s code=%s linked=%s",
        phone_norm,
        hesabfa_code,
        bool(found_code),
    )
    return mapping
