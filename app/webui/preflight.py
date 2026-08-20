"""Pre-flight facts the dashboard shows before a job runs, and the safety
snapshot it takes first.

Two separate concerns, both belonging to the moment *before* anything is
written to WordPress:

- `describe_impact()` answers "what is this button about to do?" — a new
  post or an in-place update, and whether the result goes live. Today that
  only reaches the server log as a warning, so the operator clicking the
  button cannot see it.
- `save_wpml_snapshot()` records the WPML state before linking. Nothing
  here writes to WordPress; the write path is untouched. It exists because
  `link_translation` is the one step whose failure mode is not a content
  change but a scrambled translation *relationship* — recoverable only if
  someone wrote down what it looked like beforehand.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.wordpress import wpml as wp_wpml

logger = logging.getLogger(__name__)


def describe_impact(
    client,
    post_id: int,
    post_type: str,
    action: str,
    target_language: str,
    publish_directly: bool,
    auto_publish_mode: str,
) -> dict:
    """`resulting_status` mirrors `app.cli.translate.resolve_publish_status`,
    with one addition it cannot have: "depends_on_qa". Under `qa_gated` the
    outcome is decided by a QA score that does not exist yet, so claiming
    "draft" before the run would be wrong roughly half the time.
    """
    status = wp_wpml.get_translation_status(client, post_id, target_language)
    exists = bool(status.get("translation_exists"))

    if publish_directly or auto_publish_mode == "all":
        resulting_status = "publish"
    elif auto_publish_mode == "qa_gated":
        resulting_status = "depends_on_qa"
    else:
        resulting_status = "draft"

    return {
        "post_id": post_id,
        "post_type": post_type,
        "action": action,
        "target": "update" if exists else "create",
        "translated_post_id": status.get("translated_post_id") if exists else None,
        "resulting_status": resulting_status,
        # Stated explicitly rather than left implicit: no code path writes to
        # the source-language post, so the blast radius is always the
        # translated post alone.
        "touches_source_post": False,
        "trid": status.get("trid"),
    }


def save_wpml_snapshot(client, post_id: int, job_id: str, logs_dir: Path) -> Path | None:
    """Writes the current WPML status to `logs/` before the job starts.
    Returns None if it could not be taken -- a missing safety net must not
    stop work the operator explicitly asked for.
    """
    try:
        status = wp_wpml.get_wpml_status(client, post_id)
    except Exception:  # noqa: BLE001 -- best effort by design, see docstring
        logger.warning("could not snapshot WPML state for post %s (job %s)", post_id, job_id, exc_info=True)
        return None

    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"wpml_snapshot_{job_id}.json"
    path.write_text(
        json.dumps(
            {
                "job_id": job_id,
                "post_id": post_id,
                "taken_at": datetime.now(timezone.utc).isoformat(),
                "wpml_status": status,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path
