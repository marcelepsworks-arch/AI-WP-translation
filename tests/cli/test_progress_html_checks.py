from app.cli.progress_html import ProgressTracker
from app.qa.scoring import QAReport


def _report(**overrides) -> QAReport:
    fields = {
        "numeric_passed": True, "terminology_passed": True, "url_passed": True,
        "structure_passed": True, "review_passed": True, "score": 100, "decision": "auto_approve",
    }
    return QAReport(**{**fields, **overrides})


def _tracker(tmp_path, total=1):
    return ProgressTracker(total=total, post_id=1, target_language="es", html_path=tmp_path / "progress.html")


def test_recording_without_a_qa_report_still_works(tmp_path):
    # translate.py is free not to pass one; the tracker must not require it.
    tracker = _tracker(tmp_path)
    tracker.record("block_1", "paragraph", "auto_approve", 100)

    assert tracker.snapshot()["blocks"][0]["checks"] == {}


def test_a_failing_check_is_named_in_the_snapshot(tmp_path):
    tracker = _tracker(tmp_path)
    tracker.record("block_1", "paragraph", "reject", 60, qa=_report(numeric_passed=False, score=60, decision="reject"))

    assert tracker.snapshot()["blocks"][0]["checks"]["numeric"] is False
    assert tracker.snapshot()["blocks"][0]["checks"]["terminology"] is True


def test_every_check_including_structure_is_reported(tmp_path):
    tracker = _tracker(tmp_path)
    tracker.record("block_1", "paragraph", "auto_approve", 100, qa=_report())

    assert set(tracker.snapshot()["blocks"][0]["checks"]) == {
        "numeric", "terminology", "url", "structure", "review",
    }


def test_the_failing_check_is_named_in_the_written_html(tmp_path):
    path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=1, target_language="es", html_path=path)
    tracker.record("block_1", "paragraph", "reject", 75, qa=_report(url_passed=False, score=80, decision="reject"))

    written = path.read_text(encoding="utf-8")
    assert '<span class="check check-fail">url</span>' in written


def test_a_fully_passing_block_shows_no_failure_marker(tmp_path):
    path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=1, target_language="es", html_path=path)
    tracker.record("block_1", "paragraph", "auto_approve", 100, qa=_report())

    assert '<span class="check check-fail">' not in path.read_text(encoding="utf-8")


def test_blocks_without_qa_render_without_check_markup(tmp_path):
    path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=1, target_language="es", html_path=path)
    tracker.record("block_1", "title", "skipped", None)

    assert '<span class="check check-fail">' not in path.read_text(encoding="utf-8")
