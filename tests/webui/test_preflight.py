import json

from app.webui.preflight import describe_impact, save_wpml_snapshot


class _FakeClient:
    def __init__(self, status: dict) -> None:
        self._status = status
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, path: str, params: dict | None = None):
        self.calls.append((path, params))

        class _Response:
            def __init__(self, payload: dict) -> None:
                self._payload = payload

            def json(self) -> dict:
                return self._payload

        return _Response(self._status)


def test_translate_of_an_untranslated_page_reports_a_new_post():
    client = _FakeClient({"translation_exists": False, "trid": 77})

    impact = describe_impact(client, 12, "page", "translate", "es", publish_directly=False, auto_publish_mode="off")

    assert impact["target"] == "create"
    assert impact["translated_post_id"] is None
    assert impact["resulting_status"] == "draft"
    assert impact["touches_source_post"] is False


def test_sync_of_a_translated_page_reports_an_in_place_update():
    client = _FakeClient({"translation_exists": True, "translated_post_id": 981, "trid": 77})

    impact = describe_impact(client, 12, "page", "sync", "es", publish_directly=False, auto_publish_mode="off")

    assert impact["target"] == "update"
    assert impact["translated_post_id"] == 981


def test_publish_directly_reports_a_live_publish():
    client = _FakeClient({"translation_exists": False, "trid": 77})

    impact = describe_impact(client, 12, "page", "translate", "es", publish_directly=True, auto_publish_mode="off")

    assert impact["resulting_status"] == "publish"


def test_qa_gated_mode_cannot_be_resolved_before_the_run():
    # "qa_gated" publishes only when QA finds nothing, which is unknowable
    # before translating. Saying "draft" here would be a lie half the time.
    client = _FakeClient({"translation_exists": False, "trid": 77})

    impact = describe_impact(client, 12, "page", "translate", "es", publish_directly=False, auto_publish_mode="qa_gated")

    assert impact["resulting_status"] == "depends_on_qa"


def test_auto_publish_all_reports_a_live_publish():
    client = _FakeClient({"translation_exists": True, "translated_post_id": 5, "trid": 77})

    impact = describe_impact(client, 12, "page", "sync", "es", publish_directly=False, auto_publish_mode="all")

    assert impact["resulting_status"] == "publish"


def test_snapshot_records_the_wpml_state_before_any_linking(tmp_path):
    client = _FakeClient({"trid": 77, "translation_exists": True, "translated_post_id": 981})

    path = save_wpml_snapshot(client, post_id=12, job_id="abc123", logs_dir=tmp_path)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["post_id"] == 12
    assert saved["job_id"] == "abc123"
    assert saved["wpml_status"]["trid"] == 77


def test_snapshot_failure_never_blocks_the_job(tmp_path):
    class _BrokenClient:
        def get(self, path, params=None):
            raise RuntimeError("bridge unreachable")

    # The snapshot is a safety net, not a gate: losing it must not stop a
    # translation the operator asked for.
    assert save_wpml_snapshot(_BrokenClient(), post_id=12, job_id="abc", logs_dir=tmp_path) is None
