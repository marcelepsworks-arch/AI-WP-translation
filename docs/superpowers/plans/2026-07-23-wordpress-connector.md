# WordPress Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the non-WPML-blocked part of FASE 2 of `PLA-ACCIO.md`: a Python client that reads content from the real WordPress staging site (posts, pages, post meta, Elementor data) over the REST API, handling the site's two auth layers (the staging Basic Auth gate, and — once created — a WordPress Application Password). WPML-specific functions (`get_wpml_status()`, `link_translation()`) are explicitly out of scope until WPML is installed (`AUDITORIA-INICIAL.md` §0.2).

**Architecture:** `WordPressClient` (`app/wordpress/client.py`) is a thin, testable wrapper around `requests` handling auth and retries. `app/wordpress/content.py` holds pure functions (`get_post`, `get_page`, `get_pages`, `get_post_meta`, `get_elementor_data`) that take a `WordPressClient` and return plain dicts/lists — no WordPress-specific logic lives outside these two files.

**Tech Stack:** Python 3.10, `requests` (new dependency), `pytest` + `unittest.mock` (mocked HTTP session in tests — no live calls). Manual verification against the real staging site happens via a smoke script, mirroring `scripts/translate_sample.py`.

## Global Constraints

- No live HTTP calls in the automated test suite — inject a fake `requests.Session`-like object.
- The client must support **two independent auth layers**: the staging's HTTP Basic Auth gate (`STAGING_BASIC_AUTH_USER/PASSWORD`) and, when available, a WordPress Application Password (`WP_USERNAME`/`WP_APPLICATION_PASSWORD`) — never hardcode which one is "the" auth.
- Retry once on HTTP 429/503 with a short backoff; raise on any other non-2xx status.
- Code and comments in English.

---

## File Structure

```
app/wordpress/
├── __init__.py
├── client.py     # WordPressClient
└── content.py    # get_post(), get_page(), get_pages(), get_post_meta(), get_elementor_data()

tests/wordpress/
├── __init__.py
├── test_client.py
└── test_content.py

scripts/
└── inspect_staging_page.py   # manual smoke test against the real staging site
```

---

### Task 1: `WordPressClient` — auth + retries

**Files:**
- Create: `app/wordpress/__init__.py`
- Create: `app/wordpress/client.py`
- Create: `tests/wordpress/__init__.py`
- Create: `tests/wordpress/test_client.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `WordPressClient(base_url: str, basic_auth: tuple[str, str] | None = None, wp_username: str | None = None, wp_app_password: str | None = None, session: requests.Session | None = None)` with method `.get(path: str, params: dict | None = None) -> requests.Response`. Task 2 calls `.get()` and reads `.json()` / `.headers` from the result.

- [ ] **Step 1: Create package init files**

`app/wordpress/__init__.py`:
```python
```

`tests/wordpress/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing test — `tests/wordpress/test_client.py`**

```python
from unittest.mock import MagicMock

import pytest
import requests

from app.wordpress.client import WordPressClient


def _fake_session(responses: list) -> MagicMock:
    session = MagicMock()
    session.get.side_effect = responses
    return session


def _fake_response(status_code: int, json_data=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error", response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_get_uses_wp_app_password_when_available():
    session = _fake_session([_fake_response(200, {"id": 1})])

    client = WordPressClient(
        base_url="https://staging.example.com",
        basic_auth=("root", "gatepass"),
        wp_username="bot",
        wp_app_password="app-pass-1234",
        session=session,
    )
    client.get("/wp-json/wp/v2/posts/1")

    _, kwargs = session.get.call_args
    assert kwargs["auth"] == ("bot", "app-pass-1234")


def test_get_falls_back_to_basic_auth_when_no_wp_credentials():
    session = _fake_session([_fake_response(200, {"id": 1})])

    client = WordPressClient(
        base_url="https://staging.example.com",
        basic_auth=("root", "gatepass"),
        session=session,
    )
    client.get("/wp-json/wp/v2/posts/1")

    _, kwargs = session.get.call_args
    assert kwargs["auth"] == ("root", "gatepass")


def test_get_builds_full_url_from_base_and_path():
    session = _fake_session([_fake_response(200, {})])

    client = WordPressClient(base_url="https://staging.example.com/", session=session)
    client.get("/wp-json/wp/v2/pages")

    args, _ = session.get.call_args
    assert args[0] == "https://staging.example.com/wp-json/wp/v2/pages"


def test_get_retries_once_on_429_then_succeeds():
    session = _fake_session([_fake_response(429), _fake_response(200, {"ok": True})])

    client = WordPressClient(base_url="https://staging.example.com", session=session)
    response = client.get("/wp-json/wp/v2/posts")

    assert response.json() == {"ok": True}
    assert session.get.call_count == 2


def test_get_raises_on_404_without_retrying():
    session = _fake_session([_fake_response(404)])

    client = WordPressClient(base_url="https://staging.example.com", session=session)

    with pytest.raises(requests.HTTPError):
        client.get("/wp-json/wp/v2/posts/999999")

    assert session.get.call_count == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/wordpress/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.wordpress.client'`.

- [ ] **Step 4: Write minimal implementation — `app/wordpress/client.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/wordpress/test_client.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit and push**

```bash
git add app/wordpress/__init__.py app/wordpress/client.py tests/wordpress/__init__.py tests/wordpress/test_client.py
git commit -m "feat: add WordPressClient with dual auth and 429/503 retry"
git push origin master
```

---

### Task 2: Content-reading functions

**Files:**
- Create: `app/wordpress/content.py`
- Create: `tests/wordpress/test_content.py`

**Interfaces:**
- Consumes: `WordPressClient.get()` from Task 1.
- Produces: `get_post(client, post_id: int) -> dict`; `get_page(client, page_id: int) -> dict`; `get_pages(client, per_page: int = 100) -> list[dict]`; `get_post_meta(client, post_id: int) -> dict`; `get_elementor_data(client, post_id: int) -> str | None`.

- [ ] **Step 1: Write the failing test — `tests/wordpress/test_content.py`**

```python
from unittest.mock import MagicMock

from app.wordpress.content import (
    get_elementor_data,
    get_page,
    get_pages,
    get_post,
    get_post_meta,
)


def _client_returning(json_data):
    client = MagicMock()
    response = MagicMock()
    response.json.return_value = json_data
    client.get.return_value = response
    return client


def test_get_post_calls_correct_endpoint_and_returns_json():
    client = _client_returning({"id": 42, "title": {"rendered": "Hello"}})

    result = get_post(client, 42)

    client.get.assert_called_once_with("/wp-json/wp/v2/posts/42")
    assert result["id"] == 42


def test_get_page_calls_correct_endpoint():
    client = _client_returning({"id": 4309, "slug": "precision-agriculture"})

    result = get_page(client, 4309)

    client.get.assert_called_once_with("/wp-json/wp/v2/pages/4309")
    assert result["slug"] == "precision-agriculture"


def test_get_pages_calls_endpoint_with_per_page_param():
    client = _client_returning([{"id": 1}, {"id": 2}])

    result = get_pages(client, per_page=50)

    client.get.assert_called_once_with("/wp-json/wp/v2/pages", params={"per_page": 50})
    assert len(result) == 2


def test_get_pages_defaults_per_page_to_100():
    client = _client_returning([])

    get_pages(client)

    client.get.assert_called_once_with("/wp-json/wp/v2/pages", params={"per_page": 100})


def test_get_post_meta_returns_meta_dict_from_post():
    client = _client_returning({"id": 1, "meta": {"footnotes": ""}})

    result = get_post_meta(client, 1)

    assert result == {"footnotes": ""}


def test_get_post_meta_returns_empty_dict_when_no_meta_key():
    client = _client_returning({"id": 1})

    result = get_post_meta(client, 1)

    assert result == {}


def test_get_elementor_data_returns_value_when_present_in_meta():
    client = _client_returning({"id": 1, "meta": {"_elementor_data": '{"foo": "bar"}'}})

    result = get_elementor_data(client, 1)

    assert result == '{"foo": "bar"}'


def test_get_elementor_data_returns_none_when_not_exposed():
    client = _client_returning({"id": 1, "meta": {"footnotes": ""}})

    result = get_elementor_data(client, 1)

    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/wordpress/test_content.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.wordpress.content'`.

- [ ] **Step 3: Write minimal implementation — `app/wordpress/content.py`**

```python
"""Read-only WordPress content access: posts, pages, meta, Elementor data.

WPML-related functions (get_wpml_status, link_translation) are
intentionally not here yet — WPML is not installed on staging as of
2026-07-23 (see AUDITORIA-INICIAL.md section 0.2).
"""
from __future__ import annotations

from app.wordpress.client import WordPressClient


def get_post(client: WordPressClient, post_id: int) -> dict:
    return client.get(f"/wp-json/wp/v2/posts/{post_id}").json()


def get_page(client: WordPressClient, page_id: int) -> dict:
    return client.get(f"/wp-json/wp/v2/pages/{page_id}").json()


def get_pages(client: WordPressClient, per_page: int = 100) -> list[dict]:
    return client.get("/wp-json/wp/v2/pages", params={"per_page": per_page}).json()


def get_post_meta(client: WordPressClient, post_id: int) -> dict:
    return get_post(client, post_id).get("meta", {})


def get_elementor_data(client: WordPressClient, post_id: int) -> str | None:
    meta = get_post_meta(client, post_id)
    return meta.get("_elementor_data")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/wordpress/test_content.py -v`
Expected: 8 passed.

- [ ] **Step 5: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (60 existing + 5 client + 8 content = 73 total).

- [ ] **Step 6: Commit and push**

```bash
git add app/wordpress/content.py tests/wordpress/test_content.py
git commit -m "feat: add WordPress content-reading functions (posts, pages, meta, Elementor)"
git push origin master
```

---

### Task 3: Manual smoke test against the real staging site

**Files:**
- Create: `scripts/inspect_staging_page.py`

**Interfaces:**
- Consumes: `WordPressClient` (Task 1), `get_page`, `get_post_meta`, `get_elementor_data` (Task 2). Reads `STAGING_URL`, `STAGING_BASIC_AUTH_USER`, `STAGING_BASIC_AUTH_PASSWORD`, `WP_USERNAME`, `WP_APPLICATION_PASSWORD` from `.env` — never hardcoded.

- [ ] **Step 1: Create `scripts/inspect_staging_page.py`**

```python
"""Manual smoke test: fetch one real page from the staging site and
print what the connector actually sees.

Usage:
    python scripts/inspect_staging_page.py <page_id>

Reads credentials from .env — never hardcode them here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.wordpress.client import WordPressClient
from app.wordpress.content import get_elementor_data, get_page, get_post_meta


def main() -> None:
    load_dotenv()

    page_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4309  # Precision Agriculture

    client = WordPressClient(
        base_url=os.environ["STAGING_URL"],
        basic_auth=(os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"]),
        wp_username=os.environ.get("WP_USERNAME"),
        wp_app_password=os.environ.get("WP_APPLICATION_PASSWORD"),
    )

    page = get_page(client, page_id)
    meta = get_post_meta(client, page_id)
    elementor_data = get_elementor_data(client, page_id)

    print(f"Title:          {page['title']['rendered']}")
    print(f"Slug:           {page['slug']}")
    print(f"Content length: {len(page['content']['rendered'])} chars (rendered HTML)")
    print(f"Meta keys:      {list(meta.keys())}")
    print(f"Elementor data exposed via REST: {'yes' if elementor_data else 'no'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script is syntactically valid**

Run: `.venv/Scripts/python.exe -m py_compile scripts/inspect_staging_page.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit and push**

```bash
git add scripts/inspect_staging_page.py
git commit -m "chore: add manual staging-page inspection script"
git push origin master
```

---

### Task 4: Update tracking docs

**Files:**
- Modify: `PLA-ACCIO.md`
- Modify: `LOG.md`
- Modify: `requirements.txt`

- [ ] **Step 1:** Add `requests>=2.31.0` to `requirements.txt` (new runtime dependency).
- [ ] **Step 2:** Mark `PLA-ACCIO.md` FASE 2.1-2.3 as done (2.4 stays blocked on WPML), note 2.5 partial (manual smoke test done, no automated integration test against real site by design).
- [ ] **Step 3:** Add a `LOG.md` entry summarizing this session.
- [ ] **Step 4: Commit and push**

```bash
git add requirements.txt PLA-ACCIO.md LOG.md docs/superpowers/plans/2026-07-23-wordpress-connector.md
git commit -m "docs: mark FASE 2.1-2.3 done, log WordPress connector session"
git push origin master
```

---

## Out of scope for this plan

- `create_translation()`, `get_wpml_status()`, `link_translation()` — blocked on WPML installation (`AUDITORIA-INICIAL.md` §0.2).
- Automated integration tests against the real staging site — deliberately excluded from the test suite (would make CI depend on network + secrets); the manual script (Task 3) covers that need.
- FASE 3 (Elementor JSON parsing into semantic blocks) — separate future plan.
