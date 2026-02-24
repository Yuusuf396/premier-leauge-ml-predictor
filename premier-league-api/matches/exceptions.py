from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.views import exception_handler


def _flatten_detail(detail) -> str:
    if isinstance(detail, dict):
        for value in detail.values():
            return _flatten_detail(value)
        return "Request failed."
    if isinstance(detail, (list, tuple)) and detail:
        return _flatten_detail(detail[0])
    return str(detail or "Request failed.")


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        response.status_code = status.HTTP_403_FORBIDDEN
        response.data = {
            "error": "forbidden",
            "message": _flatten_detail(getattr(exc, "detail", None)) or "Authentication token is required.",
        }
        return response

    if isinstance(exc, PermissionDenied):
        response.data = {
            "error": "forbidden",
            "message": _flatten_detail(getattr(exc, "detail", None)) or "You do not have permission to perform this action.",
        }
        return response

    if isinstance(exc, ValidationError):
        response.data = {
            "error": "invalid_input",
            "message": _flatten_detail(getattr(exc, "detail", None)) or "Invalid input.",
        }
        return response

    if isinstance(response.data, dict) and "detail" in response.data:
        response.data = {
            "error": "request_failed",
            "message": _flatten_detail(response.data.get("detail")),
        }

    return response
