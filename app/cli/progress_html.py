"""Local, auto-refreshing HTML progress view for long translation runs.

Not a published Artifact — Artifacts have no capability to reach into a
local Python process (only `downloads` and `mcp` are available to this
account, neither of which bridges live local state). This writes a plain
HTML file to disk instead; <meta http-equiv="refresh"> does the auto-reload
client-side. Open it once in a browser and leave it open.
"""
from __future__ import annotations

import html
import threading
import time
from pathlib import Path

from app.translation.pricing import estimate_cost_usd

_MAX_ROWS_SHOWN = 50


class ProgressTracker:
    def __init__(
        self,
        total: int,
        post_id: int,
        target_language: str,
        html_path: Path = Path("logs/progress.html"),
    ) -> None:
        self.total = total
        self.post_id = post_id
        self.target_language = target_language
        self.html_path = html_path
        self.started_at = time.time()
        self._lock = threading.Lock()
        self._completed: list[dict] = []
        self._finished_decision: str | None = None
        self._usage: dict[str, dict[str, int]] = {}
        self.html_path.parent.mkdir(parents=True, exist_ok=True)
        self._write()

    def record(
        self,
        content_id: str,
        block_type: str,
        decision: str,
        score: int | None,
        usage: dict[str, dict[str, int]] | None = None,
    ) -> None:
        with self._lock:
            self._completed.append(
                {"content_id": content_id, "type": block_type, "decision": decision, "score": score}
            )
            if usage is not None:
                # Snapshot, not a live reference -- DeepSeekClient.usage keeps
                # mutating after this call returns.
                self._usage = {model: dict(counts) for model, counts in usage.items()}
            self._write()

    def finish(self, overall_decision: str) -> None:
        with self._lock:
            self._finished_decision = overall_decision
            self._write()

    def _write(self) -> None:
        done = len(self._completed)
        pct = int(done / self.total * 100) if self.total else 100
        elapsed = time.time() - self.started_at

        counts: dict[str, int] = {}
        for item in self._completed:
            counts[item["decision"]] = counts.get(item["decision"], 0) + 1

        rows = "\n".join(
            f'<tr class="{html.escape(item["decision"])}">'
            f'<td>{html.escape(item["content_id"])}</td>'
            f'<td>{html.escape(item["type"])}</td>'
            f'<td>{html.escape(item["decision"])}</td>'
            f'<td>{item["score"] if item["score"] is not None else "-"}</td>'
            f"</tr>"
            for item in reversed(self._completed[-_MAX_ROWS_SHOWN:])
        )
        counts_html = " ".join(f'<span class="badge {k}">{k}: {v}</span>' for k, v in counts.items())

        usage_section = ""
        if self._usage:
            cost = estimate_cost_usd(self._usage)
            usage_rows = "\n".join(
                f"<tr><td>{html.escape(model)}</td>"
                f"<td>{counts.get('input', 0):,}</td>"
                f"<td>{counts.get('output', 0):,}</td>"
                f"<td>{counts.get('input', 0) + counts.get('output', 0):,}</td></tr>"
                for model, counts in self._usage.items()
            )
            usage_section = f"""
<h2 style="font-size:1rem;margin-top:1.5rem;">Token usage &amp; estimated cost</h2>
<table>
<tr><th>Model</th><th>Input tokens</th><th>Output tokens</th><th>Total</th></tr>
{usage_rows}
</table>
<p><b>Estimated cost: ${cost:.4f} USD</b> <span style="opacity:.5">(DeepSeek pricing, approximate — see app/translation/pricing.py)</span></p>"""

        status_line = (
            f'<p class="status">Finished — overall decision: <b>{html.escape(self._finished_decision)}</b></p>'
            if self._finished_decision
            else '<p class="status">Running…</p>'
        )
        refresh_tag = "" if self._finished_decision else '<meta http-equiv="refresh" content="2">'

        page = f"""<!doctype html>
<html><head><meta charset="utf-8">
{refresh_tag}
<title>Translation progress — post {self.post_id}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #111; color: #eee; }}
h1 {{ font-size: 1.2rem; }}
.status {{ opacity: .85; }}
.bar-outer {{ background: #333; border-radius: 6px; height: 24px; width: 100%; overflow: hidden; margin: 1rem 0; }}
.bar-inner {{ background: #4caf50; height: 100%; transition: width .3s; }}
.badge {{ display: inline-block; padding: .2rem .6rem; border-radius: 4px; margin-right: .5rem; font-size: .85rem; }}
.badge.auto_approve {{ background: #2e7d32; }}
.badge.human_review {{ background: #b8860b; }}
.badge.reject {{ background: #b71c1c; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
td, th {{ padding: .3rem .6rem; border-bottom: 1px solid #333; text-align: left; font-size: .9rem; }}
tr.reject {{ background: #3a1414; }}
tr.human_review {{ background: #3a2f14; }}
</style>
</head>
<body>
<h1>Post {self.post_id} &rarr; {html.escape(self.target_language)}</h1>
{status_line}
<div class="bar-outer"><div class="bar-inner" style="width:{pct}%"></div></div>
<p>{done} / {self.total} blocks ({pct}%) &mdash; {elapsed:.0f}s elapsed</p>
<p>{counts_html}</p>
<table>
<tr><th>Block</th><th>Type</th><th>Decision</th><th>Score</th></tr>
{rows}
</table>
<p style="opacity:.5">Most recent {_MAX_ROWS_SHOWN} shown, newest first.</p>
{usage_section}
</body></html>"""
        self.html_path.write_text(page, encoding="utf-8")
