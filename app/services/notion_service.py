# app/services/notion_service.py
import os
import logging

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")

    async def update_endpoint_status(self, feature_name: str, status: str):
        """
        ارسال وضعیت جدید به نوشن (فعلاً لاگ می‌اندازیم تا سرور کرش نکند)
        """
        logger.info(f"🔔 [Notion Service] Feature '{feature_name}' status changed to: {status}")
        # کدهای اصلی اتصال به API نوشن را در فاز بعدی اینجا قرار می‌دهیم