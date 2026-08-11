"""Local, auto-refreshing HTML progress view for long translation runs.

Not a published Artifact — Artifacts have no capability to reach into a
local Python process (only `downloads` and `mcp` are available to this
account, neither of which bridges live local state). This writes a plain
HTML file to disk instead; <meta http-equiv="refresh"> does the auto-reload
client-side. Open it once in a browser and leave it open.

Once a run finishes, this file *is* the human review report (source vs.
translation per block, QA verdict) — see `app.cli.translate --review` and
`app.cli.publish` — so its styling matches the project's other client-facing
reports (`docs/reports/*.html`), not a debug console.
"""
from __future__ import annotations

import html
import threading
import time
from pathlib import Path

from app.translation.pricing import estimate_cost_usd

_MAX_ROWS_SHOWN = 50

_DECISION_LABEL = {"auto_approve": "Auto-approved", "human_review": "Needs review", "reject": "Rejected"}


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
        self._publish_command: str | None = None
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
        source: str = "",
        translation: str = "",
    ) -> None:
        with self._lock:
            self._completed.append(
                {
                    "content_id": content_id,
                    "type": block_type,
                    "decision": decision,
                    "score": score,
                    "source": source,
                    "translation": translation,
                }
            )
            if usage is not None:
                # Snapshot, not a live reference -- DeepSeekClient.usage keeps
                # mutating after this call returns.
                self._usage = {model: dict(counts) for model, counts in usage.items()}
            self._write()

    def finish(self, overall_decision: str, publish_command: str | None = None) -> None:
        with self._lock:
            self._finished_decision = overall_decision
            self._publish_command = publish_command
            self._write()

    def _write(self) -> None:
        done = len(self._completed)
        pct = int(done / self.total * 100) if self.total else 100
        elapsed = time.time() - self.started_at

        counts: dict[str, int] = {}
        for item in self._completed:
            counts[item["decision"]] = counts.get(item["decision"], 0) + 1

        # While running, only the tail is shown (live feed). Once finished,
        # this file *is* the review report, so every block must be visible.
        shown = self._completed if self._finished_decision else self._completed[-_MAX_ROWS_SHOWN:]
        rows = "\n".join(
            f'<tr class="row-{html.escape(item["decision"])}">'
            f'<td><span class="dot dot-{html.escape(item["decision"])}"></span>{html.escape(item["content_id"])}</td>'
            f'<td class="muted">{html.escape(item["type"])}</td>'
            f'<td>{html.escape(_DECISION_LABEL.get(item["decision"], item["decision"]))}</td>'
            f'<td class="muted">{item["score"] if item["score"] is not None else "&ndash;"}</td>'
            f'<td class="text">{html.escape(item["source"])}</td>'
            f'<td class="text">{html.escape(item["translation"])}</td>'
            f"</tr>"
            for item in reversed(shown)
        )
        counts_html = " ".join(
            f'<span class="badge badge-{k}"><span class="dot dot-{k}"></span>{_DECISION_LABEL.get(k, k)}: {v}</span>'
            for k, v in counts.items()
        )

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
<h2>Token usage &amp; estimated cost</h2>
<table>
<tr><th>Model</th><th>Input tokens</th><th>Output tokens</th><th>Total</th></tr>
{usage_rows}
</table>
<div class="callout"><b>Estimated cost: ${cost:.4f} USD</b> <span class="muted">(DeepSeek pricing, approximate — see app/translation/pricing.py)</span></div>"""

        if self._finished_decision:
            status_kind = self._finished_decision if self._finished_decision != "auto_approve" else "auto_approve"
            status_pill = (
                f'<span class="pill pill-{html.escape(status_kind)}"><span class="dot dot-{html.escape(status_kind)}"></span>'
                f'Finished &middot; {html.escape(_DECISION_LABEL.get(self._finished_decision, self._finished_decision))}</span>'
            )
        else:
            status_pill = '<span class="pill pill-running"><span class="dot dot-running"></span>Running&hellip;</span>'

        publish_section = ""
        if self._finished_decision and self._publish_command:
            publish_section = f"""
<h2>Review this page, then publish it</h2>
<p class="lead">Nothing has been written to WordPress yet. Read through the source/translation columns above; if it
looks good, run this command to publish the draft and link it in WPML &mdash; no re-translation, no extra
DeepSeek cost.</p>
<pre class="cmd">{html.escape(self._publish_command)}</pre>"""
        refresh_tag = "" if self._finished_decision else '<meta http-equiv="refresh" content="2">'

        page = f"""<!doctype html>
<html><head><meta charset="utf-8">
{refresh_tag}
<title>Translation review — post {self.post_id}</title>
<style>
  :root{{
    --ink:#1d1d1f; --ink-soft:#6e6e73; --accent:#0a5fb4; --accent-soft:#eef4fb;
    --line:#e5e5e7; --bg-card:#f5f5f7; --good:#1a7a3c; --good-soft:#e9f6ee;
    --warn:#a8631a; --warn-soft:#fbf1e6; --bad:#b3261e; --bad-soft:#fbeceb;
    --run:#6e6e73; --run-soft:#f0f0f2;
  }}
  *{{ box-sizing:border-box; }}
  html,body{{ margin:0; padding:0; }}
  body{{
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    color:var(--ink); background:#fafafa; font-size:13px; line-height:1.6; -webkit-font-smoothing:antialiased;
    padding:32px 40px 56px;
  }}
  .wrap{{ max-width:1100px; margin:0 auto; }}
  .eyebrow{{ font-size:11px; letter-spacing:2px; text-transform:uppercase; color:var(--accent); font-weight:700; margin-bottom:6px; }}
  h1{{ font-size:24px; font-weight:700; letter-spacing:-0.3px; margin:0 0 14px 0; color:var(--ink); }}
  h2{{ font-size:14px; font-weight:700; margin:26px 0 8px 0; color:var(--ink); }}
  p{{ margin:0 0 10px 0; color:#3a3a3c; }}
  p.lead{{ font-size:13px; color:#3a3a3c; }}
  .muted{{ color:var(--ink-soft); }}

  .pill{{
    display:inline-flex; align-items:center; gap:7px; padding:6px 14px; border-radius:100px;
    font-size:12.5px; font-weight:600; margin-bottom:18px;
  }}
  .pill-running{{ background:var(--run-soft); color:var(--run); }}
  .pill-auto_approve{{ background:var(--good-soft); color:var(--good); }}
  .pill-human_review{{ background:var(--warn-soft); color:var(--warn); }}
  .pill-reject{{ background:var(--bad-soft); color:var(--bad); }}

  .dot{{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:2px; }}
  .dot-running{{ background:var(--run); animation:pulse 1.4s ease-in-out infinite; }}
  .dot-auto_approve{{ background:var(--good); }}
  .dot-human_review{{ background:var(--warn); }}
  .dot-reject{{ background:var(--bad); }}
  @keyframes pulse{{ 0%,100%{{ opacity:1; }} 50%{{ opacity:.35; }} }}

  .bar-outer{{ background:var(--line); border-radius:100px; height:8px; width:100%; overflow:hidden; margin:4px 0 10px; }}
  .bar-inner{{ background:var(--accent); height:100%; border-radius:100px; transition:width .3s; }}
  .meta-line{{ font-size:12px; color:var(--ink-soft); margin-bottom:16px; }}

  .badge{{
    display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:8px;
    margin:0 8px 8px 0; font-size:12px; font-weight:600;
  }}
  .badge-auto_approve{{ background:var(--good-soft); color:var(--good); }}
  .badge-human_review{{ background:var(--warn-soft); color:var(--warn); }}
  .badge-reject{{ background:var(--bad-soft); color:var(--bad); }}

  table{{ width:100%; border-collapse:collapse; margin-top:12px; table-layout:fixed; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
  th{{
    text-align:left; font-size:10.5px; letter-spacing:.4px; text-transform:uppercase; color:var(--ink-soft);
    font-weight:600; padding:10px 12px; border-bottom:1.5px solid var(--ink); background:var(--bg-card);
  }}
  td{{ padding:10px 12px; border-bottom:1px solid var(--line); color:#3a3a3c; vertical-align:top; font-size:12.5px; }}
  td.text{{ white-space:pre-wrap; word-break:break-word; width:28%; }}
  tr:last-child td{{ border-bottom:none; }}
  tr.row-human_review td{{ background:var(--warn-soft); }}
  tr.row-reject td{{ background:var(--bad-soft); }}

  pre.cmd{{ background:#1d1d1f; color:#f5f5f7; padding:14px 16px; border-radius:10px; overflow-x:auto; font-family:"SF Mono",Consolas,"Courier New",monospace; font-size:12px; }}
  .callout{{ background:var(--accent-soft); border-radius:12px; padding:12px 16px; margin:10px 0; font-size:12.5px; color:#1a3a57; }}
  .callout b{{ color:var(--accent); }}
  .footnote{{ font-size:11px; color:var(--ink-soft); margin-top:8px; }}
</style>
</head>
<body>
<div class="wrap">
<div class="eyebrow">GNSS AI Translation Engine &middot; local review</div>
<h1>Post {self.post_id} &rarr; {html.escape(self.target_language)}</h1>
{status_pill}
<div class="bar-outer"><div class="bar-inner" style="width:{pct}%"></div></div>
<div class="meta-line">{done} / {self.total} blocks ({pct}%) &middot; {elapsed:.0f}s elapsed</div>
<div>{counts_html}</div>
<table>
<tr><th style="width:16%">Block</th><th style="width:10%">Type</th><th style="width:12%">Decision</th><th style="width:6%">Score</th><th>Source</th><th>Translation</th></tr>
{rows}
</table>
<p class="footnote">{"All blocks shown" if self._finished_decision else f"Most recent {_MAX_ROWS_SHOWN} shown"}, newest first.</p>
{usage_section}
{publish_section}
</div>
</body></html>"""
        self.html_path.write_text(page, encoding="utf-8")
