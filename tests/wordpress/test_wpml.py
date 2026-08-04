from unittest.mock import MagicMock

from app.wordpress.wpml import (
    complete_job,
    create_job,
    export_xliff,
    get_wpml_status,
    import_xliff,
    link_translation,
    start_job,
)

_XLIFF = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file original="post-42" source-language="en" target-language="es" datatype="plaintext">
    <body>
      <trans-unit id="1">
        <source>Rover connects via NTRIP.</source>
      </trans-unit>
    </body>
  </file>
</xliff>
"""


def _client_returning(json_data=None, text=None):
    client = MagicMock()
    response = MagicMock()
    if json_data is not None:
        response.json.return_value = json_data
    if text is not None:
        response.text = text
    client.get.return_value = response
    client.post.return_value = response
    return client


def test_get_wpml_status_calls_correct_endpoint():
    client = _client_returning(json_data={"trid": 7, "needs_update": False})

    result = get_wpml_status(client, 42)

    client.get.assert_called_once_with("/wp-json/gnss-bridge/v1/translation-status/42")
    assert result == {"trid": 7, "needs_update": False}


def test_link_translation_posts_expected_payload():
    client = _client_returning(json_data={"status": "linked"})

    result = link_translation(
        client, element_id=99, trid=7, language_code="es", source_language_code="en"
    )

    client.post.assert_called_once_with(
        "/wp-json/gnss-bridge/v1/link-translation",
        json={
            "element_id": 99,
            "trid": 7,
            "language_code": "es",
            "source_language_code": "en",
        },
    )
    assert result == {"status": "linked"}


def test_create_job_posts_expected_payload():
    client = _client_returning(json_data={"job_id": 5})

    result = create_job(client, element_id=42, language_code="es")

    client.post.assert_called_once_with(
        "/wp-json/gnss-bridge/v1/create-job",
        json={"element_id": 42, "language_code": "es"},
    )
    assert result == {"job_id": 5}


def test_export_xliff_calls_correct_endpoint_and_returns_raw_text():
    client = _client_returning(text=_XLIFF)

    result = export_xliff(client, job_id=5)

    client.get.assert_called_once_with("/wp-json/gnss-bridge/v1/export-xliff/5")
    assert result == _XLIFF


def test_import_xliff_posts_xliff_content():
    client = _client_returning(json_data={"status": "complete"})

    result = import_xliff(client, _XLIFF)

    client.post.assert_called_once_with(
        "/wp-json/gnss-bridge/v1/import-xliff", json={"xliff": _XLIFF}
    )
    assert result == {"status": "complete"}


def test_start_job_returns_xliff_and_parsed_blocks():
    client = MagicMock()
    job_response = MagicMock()
    job_response.json.return_value = {"job_id": 5}
    xliff_response = MagicMock()
    xliff_response.text = _XLIFF
    client.post.return_value = job_response
    client.get.return_value = xliff_response

    xliff_content, blocks = start_job(client, element_id=42, language_code="es")

    client.post.assert_called_once_with(
        "/wp-json/gnss-bridge/v1/create-job",
        json={"element_id": 42, "language_code": "es"},
    )
    client.get.assert_called_once_with("/wp-json/gnss-bridge/v1/export-xliff/5")
    assert xliff_content == _XLIFF
    assert len(blocks) == 1
    assert blocks[0].source == "Rover connects via NTRIP."


def test_complete_job_imports_translated_xliff():
    client = _client_returning(json_data={"status": "complete"})

    result = complete_job(client, _XLIFF, {"1": "El rover se conecta vía NTRIP."})

    assert client.post.call_count == 1
    call_kwargs = client.post.call_args.kwargs
    assert "El rover se conecta vía NTRIP." in call_kwargs["json"]["xliff"]
    assert result == {"status": "complete"}
