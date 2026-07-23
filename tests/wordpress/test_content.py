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
