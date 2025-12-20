import os
import logging
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class ApiKeyPermission(BasePermission):
    """
    Проверяет заголовок Authorization: Api-Key <token> или X-API-KEY
    Используется для серверного доступа бота к API.
    """

    def has_permission(self, request, view):
        expected = os.getenv("BOT_API_KEY")
        if not expected:
            logger.warning("BOT_API_KEY is not set in environment variables")
            return False

        auth_header = request.headers.get("Authorization") or ""
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "api-key":
            received_key = parts[1]
            if received_key != expected:
                logger.warning(f"API key mismatch. Expected: {expected[:10]}..., Received: {received_key[:10]}...")
            return received_key == expected

        alt = request.headers.get("X-API-KEY")
        if alt:
            if alt != expected:
                logger.warning(f"API key mismatch (X-API-KEY). Expected: {expected[:10]}..., Received: {alt[:10]}...")
            return alt == expected
        
        logger.warning("No valid API key header found")
        return False

