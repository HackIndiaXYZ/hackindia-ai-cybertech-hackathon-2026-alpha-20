"""Shared helpers for routes: typed access to app state and a uniform error type."""
from typing import Any

from fastapi import Request

from app.services.storage import Database


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def get_settings_from(request: Request) -> Any:
    return request.app.state.settings


def get_db_from(request: Request) -> Database:
    return request.app.state.db
