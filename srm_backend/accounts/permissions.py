import os
from rest_framework.permissions import BasePermission


class ApiKeyPermission(BasePermission):
    """
    Проверяет заголовок Authorization: Api-Key <token> или X-API-KEY
    Используется для серверного доступа бота к API.
    """

    def has_permission(self, request, view):
        expected = os.getenv("BOT_API_KEY")
        if not expected:
            return False

        auth_header = request.headers.get("Authorization") or ""
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "api-key":
            return parts[1] == expected

        alt = request.headers.get("X-API-KEY")
        if alt:
            return alt == expected
        return False

