"""Local-only web dashboard for the translation pipeline (binds to
127.0.0.1, never exposed): lists every page/post with its translation
status and lets you trigger translate/sync/publish with a click, instead
of the CLI.

Deliberately thin: every button here calls the exact same, already-tested
orchestrator functions the CLI uses (`translate_page`, `sync_page`,
`publish_review`) -- no new translation logic lives here, only HTTP
plumbing and an in-memory job registry (single-user local tool, so a
plain dict + lock is enough; no task queue).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.cli.publish import publish_review
from app.cli.translate import PageReview, configure_logging, translate_page
from app.cli.sync import sync_page
from app.config.settings import load_settings
from app.translation.deepseek_client import DeepSeekClient
from app.translation.glossary import load_glossary_files
from app.wordpress import content as wp_content
from app.wordpress import wpml as wp_wpml
from app.wordpress.client import WordPressClient

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"
_LOGS_DIR = Path("logs")
_GLOSSARY_FILES = [Path("glossary/gnss.json"), Path("glossary/surveying.json")]
_TARGET_LANGUAGE = "es"

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

# Random per-process secret, embedded server-side into the page it serves at
# `/` (never sent to any other origin) and required as a header on every
# state-changing request. Without this, any webpage open in another tab
# could silently POST to this local server while it's running -- a known
# "localhost CSRF" attack class (has hit Ollama, Docker Desktop, etc.):
# browsers block a cross-origin page from *reading* the response, but not
# always from *sending* the request. A custom header can only be attached
# by JavaScript running on this app's own origin, since the browser refuses
# to send a non-CORS-safelisted header cross-origin without an explicit,
# matching Access-Control-Allow-* response -- which this server never sends.
_DASHBOARD_TOKEN = uuid.uuid4().hex


def _require_dashboard_token(x_dashboard_token: str | None = Header(default=None)) -> None:
    if x_dashboard_token != _DASHBOARD_TOKEN:
        raise HTTPException(403, "missing or invalid dashboard token")


def _build_wp_client() -> WordPressClient:
    """Prefers PROD_ADMIN_URL/PROD_ADMIN_USERNAME + PROD_APPLICATION_PASSWORD
    (what every real translation in this project has actually run against),
    falling back to the generic WP_URL/WP_USERNAME/WP_APPLICATION_PASSWORD
    used by the CLI tools for staging.
    """
    base_url = os.environ.get("PROD_ADMIN_URL") or os.environ.get("WP_URL") or os.environ["STAGING_URL"]
    username = os.environ.get("PROD_ADMIN_USERNAME") or os.environ.get("WP_USERNAME")
    app_password = os.environ.get("PROD_APPLICATION_PASSWORD") or os.environ.get("WP_APPLICATION_PASSWORD")
    if not app_password:
        raise RuntimeError(
            "No WordPress Application Password configured. Set PROD_APPLICATION_PASSWORD "
            "(for PROD_ADMIN_URL) or WP_APPLICATION_PASSWORD in .env."
        )
    basic_auth = None
    if os.environ.get("STAGING_BASIC_AUTH_USER"):
        basic_auth = (os.environ["STAGING_BASIC_AUTH_USER"], os.environ["STAGING_BASIC_AUTH_PASSWORD"])
    return WordPressClient(base_url=base_url, basic_auth=basic_auth, wp_username=username, wp_app_password=app_password)


def _build_deepseek_client() -> DeepSeekClient:
    settings = load_settings()
    return DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.default_model,
        qa_model=settings.qa_model,
    )


app = FastAPI(title="GNSS AI Translation Engine -- Dashboard")


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    # Config problems (missing .env credentials) should surface as a
    # readable message in the dashboard, not a stack trace.
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace("__DASHBOARD_TOKEN__", _DASHBOARD_TOKEN)


def _status_for(client: WordPressClient, item: dict, post_type: str) -> dict:
    status = wp_wpml.get_translation_status(client, item["id"], _TARGET_LANGUAGE)
    if not status.get("translation_exists"):
        state = "not_translated"
    elif status.get("needs_update") is True:
        state = "needs_update"
    elif status.get("needs_update") is False:
        state = "up_to_date"
    else:
        state = "unknown"
    return {
        "id": item["id"],
        "post_type": post_type,
        "title": item.get("title", {}).get("rendered", f"#{item['id']}"),
        "status": state,
        "translated_post_id": status.get("translated_post_id"),
    }


@app.get("/api/pages")
def list_pages() -> list[dict]:
    client = _build_wp_client()
    pages = wp_content.get_pages(client)
    posts = wp_content.get_posts(client)
    items = [(p, "page") for p in pages] + [(p, "post") for p in posts]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda pair: _status_for(client, pair[0], pair[1]), items))
    return sorted(results, key=lambda r: r["title"].lower())


class JobRequest(BaseModel):
    post_id: int
    post_type: str = "page"
    action: str  # "translate" | "sync"


def _run_translate_job(job_id: str, post_id: int, post_type: str) -> None:
    wp_client = _build_wp_client()
    deepseek = _build_deepseek_client()
    glossary_entries = load_glossary_files(_GLOSSARY_FILES)
    review_path = _LOGS_DIR / f"review_{job_id}.json"
    progress_path = _LOGS_DIR / f"progress_{job_id}.html"
    try:
        result = translate_page(
            wp_client, deepseek, glossary_entries, post_id, post_type, _TARGET_LANGUAGE,
            dry_run=True, max_workers=5, progress_html_path=progress_path, review_json_path=review_path,
        )
        with _jobs_lock:
            _jobs[job_id].update(
                status="awaiting_review", outcome="translated", overall_decision=result.overall_decision,
                review_path=str(review_path),
            )
    except Exception as exc:  # noqa: BLE001 -- surfaced to the dashboard, not swallowed
        logger.exception("translate job %s failed", job_id)
        with _jobs_lock:
            _jobs[job_id].update(status="error", error=str(exc))


def _run_sync_job(job_id: str, post_id: int, post_type: str) -> None:
    wp_client = _build_wp_client()
    deepseek = _build_deepseek_client()
    glossary_entries = load_glossary_files(_GLOSSARY_FILES)
    progress_path = _LOGS_DIR / f"progress_{job_id}.html"
    try:
        result = sync_page(
            wp_client, deepseek, glossary_entries, post_id, post_type, _TARGET_LANGUAGE,
            max_workers=5, progress_html_path=progress_path,
        )
        with _jobs_lock:
            _jobs[job_id].update(
                status="done", outcome=result.outcome, translated_post_id=result.translated_post_id,
                blocks_translated=result.blocks_translated, blocks_reused=result.blocks_reused,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("sync job %s failed", job_id)
        with _jobs_lock:
            _jobs[job_id].update(status="error", error=str(exc))


@app.post("/api/jobs", dependencies=[Depends(_require_dashboard_token)])
def create_job(req: JobRequest) -> dict:
    if req.action not in ("translate", "sync"):
        raise HTTPException(400, "action must be 'translate' or 'sync'")

    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "post_id": req.post_id, "post_type": req.post_type, "action": req.action}

    target = _run_translate_job if req.action == "translate" else _run_sync_job
    threading.Thread(target=target, args=(job_id, req.post_id, req.post_type), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job


@app.get("/api/jobs/{job_id}/review")
def get_job_review(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None or "review_path" not in job:
        raise HTTPException(404, "no review artifact for this job")
    review = PageReview.model_validate_json(Path(job["review_path"]).read_text(encoding="utf-8"))
    return {"post_id": review.post_id, "post_type": review.post_type, "blocks": [b.model_dump() for b in review.blocks]}


@app.post("/api/jobs/{job_id}/publish", dependencies=[Depends(_require_dashboard_token)])
def publish_job(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None or "review_path" not in job:
        raise HTTPException(404, "no review artifact for this job")

    wp_client = _build_wp_client()
    review = PageReview.model_validate_json(Path(job["review_path"]).read_text(encoding="utf-8"))
    translated_post_id = publish_review(wp_client, review)

    with _jobs_lock:
        _jobs[job_id].update(status="done", outcome="published", translated_post_id=translated_post_id)
    return {"translated_post_id": translated_post_id}


@app.get("/progress/{job_id}")
def progress_page(job_id: str) -> FileResponse:
    path = _LOGS_DIR / f"progress_{job_id}.html"
    if not path.exists():
        raise HTTPException(404, "no progress file yet")
    return FileResponse(path, media_type="text/html")
