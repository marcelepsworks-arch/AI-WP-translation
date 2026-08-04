"""Thin, testable HTTP client for the WordPress REST API.

Handles two independent auth layers: an optional HTTP Basic Auth gate
in front of the whole staging site, and an optional WordPress
Application Password for the REST API itself. When both are available,
the Application Password takes precedence for REST calls.
"""
from __future__ import annotations

import time

import requests

_RETRYABLE_STATUS_CODES = {429, 503}


class WordPressClient:
    def __init__(
        self,
        base_url: str,
        basic_auth: tuple[str, str] | None = None,
        wp_username: str | None = None,
        wp_app_password: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._basic_auth = basic_auth
        self._wp_auth = (
            (wp_username, wp_app_password) if wp_username and wp_app_password else None
        )
        self._session = session or requests.Session()

    def get(self, path: str, params: dict | None = None) -> requests.Response:
        url = f"{self._base_url}{path}"
        auth = self._wp_auth or self._basic_auth

        response = self._session.get(url, params=params, auth=auth, timeout=20)
        if response.status_code in _RETRYABLE_STATUS_CODES:
            time.sleep(1)
            response = self._session.get(url, params=params, auth=auth, timeout=20)

        response.raise_for_status()
        return response

    def post(self, path: str, json: dict | None = None) -> requests.Response:
        url = f"{self._base_url}{path}"
        auth = self._wp_auth or self._basic_auth

        response = self._session.post(url, json=json, auth=auth, timeout=20)
        if response.status_code in _RETRYABLE_STATUS_CODES:
            time.sleep(1)
            response = self._session.post(url, json=json, auth=auth, timeout=20)

        response.raise_for_status()
        return response
