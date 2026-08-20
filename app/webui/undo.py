"""What a finished job can be walked back, and how.

The two cases are genuinely different and must not be shown as one button.

A job that *created* a translated post can be undone here: trashing it
removes something that did not exist before, and WordPress keeps it in the
trash rather than destroying it. A job that *updated* an existing
translation in place cannot -- the previous content is held in WordPress's
own revision history, which already does restore properly. Linking there
beats reimplementing it against the REST API.

Neither case can ever touch the source-language post: no code path writes
to it, so it is never a candidate for undo.
"""
from __future__ import annotations

_CREATED_OUTCOMES = {"created", "published"}
_ENDPOINTS = {"page": "/wp/v2/pages", "post": "/wp/v2/posts"}


def _endpoint_for(post_type: str) -> str:
    return _ENDPOINTS.get(post_type, _ENDPOINTS["page"])


def describe_undo(job: dict, admin_base_url: str) -> dict:
    """Classifies a job into "trash" (reversible from the dashboard),
    "revisions" (reversible in wp-admin) or "none".
    """
    outcome = job.get("outcome")
    translated_post_id = job.get("translated_post_id")

    if job.get("status") == "error" or translated_post_id is None:
        return {"kind": "none", "reversible_here": False, "reason": "this job wrote nothing to WordPress"}

    if outcome in _CREATED_OUTCOMES:
        return {
            "kind": "trash",
            "reversible_here": True,
            "translated_post_id": translated_post_id,
            "post_type": job.get("post_type", "page"),
            "description": f"moves the translated {job.get('post_type', 'page')} #{translated_post_id} to the trash",
        }

    if outcome == "updated":
        base = admin_base_url.rstrip("/")
        return {
            "kind": "revisions",
            "reversible_here": False,
            "translated_post_id": translated_post_id,
            "admin_url": f"{base}/wp-admin/post.php?post={translated_post_id}&action=edit",
            "description": "restore the previous version from WordPress's own revision history",
        }

    return {"kind": "none", "reversible_here": False, "reason": "this job wrote nothing to WordPress"}


def perform_undo(client, job: dict, admin_base_url: str) -> dict:
    """Trashes the post a job created. Refuses anything else -- an in-place
    update must go through WordPress's revision UI, and silently doing
    something different from what the caller asked for would be worse than
    failing.
    """
    undo = describe_undo(job, admin_base_url)
    if undo["kind"] != "trash":
        raise ValueError(undo.get("reason") or "this job cannot be undone from the dashboard")

    endpoint = _endpoint_for(undo["post_type"])
    return client.post(f"{endpoint}/{undo['translated_post_id']}", json={"status": "trash"}).json()
