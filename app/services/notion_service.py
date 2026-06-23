"""Optional Notion integration for tracking feature delivery status."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotionService:
    """Placeholder for future Notion API integration; logs when not configured."""

    def __init__(self):
        self.token = settings.NOTION_TOKEN
        self.database_id = settings.NOTION_DATABASE_ID

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.database_id)

    async def update_endpoint_status(self, feature_name: str, status: str):
        if not self.is_configured:
            logger.debug(
                "Notion integration skipped (not configured): %s -> %s",
                feature_name,
                status,
            )
            return

        logger.info(
            "Notion feature '%s' status changed to: %s (API integration pending)",
            feature_name,
            status,
        )
