"""Canonical HTTP paths for public widget integration tests (single source of truth)."""


def public_widget_bootstrap_path(public_widget_key: str) -> str:
    return f"/api/v1/public/widget/{public_widget_key}/bootstrap"


def public_widget_chat_path(public_widget_key: str) -> str:
    return f"/api/v1/public/widget/{public_widget_key}/chat"
