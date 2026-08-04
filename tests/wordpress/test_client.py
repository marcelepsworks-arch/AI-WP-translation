from unittest.mock import MagicMock

import pytest
import requests

from app.wordpress.client import WordPressClient


def _fake_session(responses: list, method: str = "get") -> MagicMock:
    session = MagicMock()
    getattr(session, method).side_effect = responses
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


def test_post_uses_wp_app_password_when_available():
    session = _fake_session([_fake_response(200, {"ok": True})], method="post")

    client = WordPressClient(
        base_url="https://staging.example.com",
        basic_auth=("root", "gatepass"),
        wp_username="bot",
        wp_app_password="app-pass-1234",
        session=session,
    )
    client.post("/wp-json/gnss-bridge/v1/link-translation", json={"element_id": 1})

    _, kwargs = session.post.call_args
    assert kwargs["auth"] == ("bot", "app-pass-1234")
    assert kwargs["json"] == {"element_id": 1}


def test_post_builds_full_url_from_base_and_path():
    session = _fake_session([_fake_response(200, {})], method="post")

    client = WordPressClient(base_url="https://staging.example.com/", session=session)
    client.post("/wp-json/gnss-bridge/v1/create-job", json={})

    args, _ = session.post.call_args
    assert args[0] == "https://staging.example.com/wp-json/gnss-bridge/v1/create-job"


def test_post_retries_once_on_503_then_succeeds():
    session = _fake_session([_fake_response(503), _fake_response(200, {"ok": True})], method="post")

    client = WordPressClient(base_url="https://staging.example.com", session=session)
    response = client.post("/wp-json/gnss-bridge/v1/create-job", json={})

    assert response.json() == {"ok": True}
    assert session.post.call_count == 2


def test_post_raises_on_error_without_retrying():
    session = _fake_session([_fake_response(403)], method="post")

    client = WordPressClient(base_url="https://staging.example.com", session=session)

    with pytest.raises(requests.HTTPError):
        client.post("/wp-json/gnss-bridge/v1/create-job", json={})

    assert session.post.call_count == 1
