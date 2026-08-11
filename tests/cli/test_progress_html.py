from pathlib import Path

from app.cli.progress_html import ProgressTracker


def test_creates_html_file_on_init(tmp_path: Path):
    html_path = tmp_path / "progress.html"

    ProgressTracker(total=3, post_id=42, target_language="es", html_path=html_path)

    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "0 / 3 blocks" in content
    assert "Running" in content


def test_record_updates_progress_and_percentage(tmp_path: Path):
    html_path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=2, post_id=42, target_language="es", html_path=html_path)

    tracker.record("b1", "paragraph", "auto_approve", 100)

    content = html_path.read_text(encoding="utf-8")
    assert "1 / 2 blocks (50%)" in content
    assert "b1" in content
    assert "Auto-approved: 1" in content


def test_record_shows_reject_row_with_reject_css_class(tmp_path: Path):
    html_path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=42, target_language="es", html_path=html_path)

    tracker.record("b1", "paragraph", "reject", 60)

    content = html_path.read_text(encoding="utf-8")
    assert '<tr class="row-reject">' in content


def test_finish_marks_page_as_done_and_removes_auto_refresh(tmp_path: Path):
    html_path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=42, target_language="es", html_path=html_path)

    tracker.finish("auto_approve")

    content = html_path.read_text(encoding="utf-8")
    assert "Finished" in content
    assert "http-equiv=\"refresh\"" not in content


def test_record_with_usage_shows_token_counts_and_estimated_cost(tmp_path: Path):
    html_path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=42, target_language="es", html_path=html_path)

    tracker.record("b1", "paragraph", "auto_approve", 100, usage={"deepseek-v4-pro": {"input": 1000, "output": 500}})

    content = html_path.read_text(encoding="utf-8")
    assert "deepseek-v4-pro" in content
    assert "1,000" in content
    assert "500" in content
    assert "Estimated cost" in content


def test_no_usage_section_when_usage_never_recorded(tmp_path: Path):
    html_path = tmp_path / "progress.html"
    tracker = ProgressTracker(total=1, post_id=42, target_language="es", html_path=html_path)

    tracker.record("b1", "paragraph", "auto_approve", 100)

    content = html_path.read_text(encoding="utf-8")
    assert "Token usage" not in content


def test_escapes_html_in_block_content_id():
    from app.cli.progress_html import ProgressTracker as PT

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "progress.html"
        tracker = PT(total=1, post_id=1, target_language="es", html_path=html_path)
        tracker.record("<script>alert(1)</script>", "paragraph", "auto_approve", 100)

        content = html_path.read_text(encoding="utf-8")
        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;" in content
