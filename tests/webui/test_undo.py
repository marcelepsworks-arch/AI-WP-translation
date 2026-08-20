import pytest

from app.webui.undo import describe_undo, perform_undo

BASE = "https://staging.example.com"


def test_a_translate_job_created_a_new_post_so_it_can_be_trashed():
    job = {"action": "translate", "outcome": "created", "translated_post_id": 981, "post_type": "page"}

    undo = describe_undo(job, BASE)

    assert undo["kind"] == "trash"
    assert undo["translated_post_id"] == 981
    assert undo["reversible_here"] is True


def test_a_published_translate_job_is_still_a_new_post():
    job = {"action": "translate", "outcome": "published", "translated_post_id": 981, "post_type": "page"}

    assert describe_undo(job, BASE)["kind"] == "trash"


def test_a_sync_that_created_a_translation_can_be_trashed():
    job = {"action": "sync", "outcome": "created", "translated_post_id": 55, "post_type": "post"}

    assert describe_undo(job, BASE)["kind"] == "trash"


def test_a_sync_that_updated_in_place_points_at_wp_native_revisions():
    # Rebuilding WordPress's own revision restore would be reimplementing a
    # feature that already exists and is better tested than anything here.
    job = {"action": "sync", "outcome": "updated", "translated_post_id": 981, "post_type": "page"}

    undo = describe_undo(job, BASE)

    assert undo["kind"] == "revisions"
    assert undo["reversible_here"] is False
    assert undo["admin_url"] == f"{BASE}/wp-admin/post.php?post=981&action=edit"


def test_a_job_that_wrote_nothing_has_nothing_to_undo():
    assert describe_undo({"action": "sync", "outcome": "up_to_date"}, BASE)["kind"] == "none"


def test_a_job_still_awaiting_review_has_nothing_to_undo():
    job = {"action": "translate", "outcome": "translated", "status": "awaiting_review"}

    assert describe_undo(job, BASE)["kind"] == "none"


def test_a_failed_job_has_nothing_to_undo():
    assert describe_undo({"action": "translate", "status": "error"}, BASE)["kind"] == "none"


class _RecordingClient:
    def __init__(self):
        self.posts = []

    def post(self, path, json=None):
        self.posts.append((path, json))

        class _Response:
            def json(self):
                return {"id": 981, "status": "trash"}

        return _Response()


def test_performing_an_undo_trashes_the_translated_post():
    client = _RecordingClient()
    job = {"action": "translate", "outcome": "created", "translated_post_id": 981, "post_type": "page"}

    result = perform_undo(client, job, BASE)

    assert client.posts == [("/wp/v2/pages/981", {"status": "trash"})]
    assert result["status"] == "trash"


def test_performing_an_undo_uses_the_posts_endpoint_for_a_post():
    client = _RecordingClient()
    job = {"action": "sync", "outcome": "created", "translated_post_id": 55, "post_type": "post"}

    perform_undo(client, job, BASE)

    assert client.posts[0][0] == "/wp/v2/posts/55"


def test_performing_an_undo_refuses_an_in_place_update():
    client = _RecordingClient()
    job = {"action": "sync", "outcome": "updated", "translated_post_id": 981, "post_type": "page"}

    with pytest.raises(ValueError):
        perform_undo(client, job, BASE)

    assert client.posts == []
