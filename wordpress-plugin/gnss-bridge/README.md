# gnss-bridge

Minimal WordPress mu-plugin that bridges the external GNSS AI Translation
Engine (Python) to WPML's official translation-linking hooks and the Yoast
SEO meta fields. Contains **zero translation logic** — that lives entirely
in the Python engine. See `ROADMAP.md` FASE 1 and `BIBLIOGRAFIA.md` §2/§11
in the main repo for the full design rationale.

## What's implemented

- `POST /wp-json/gnss-bridge/v1/link-translation` — wraps WPML's documented
  3-step hook pattern (`wpml_element_type` → `wpml_set_element_language_details`).
- `GET /wp-json/gnss-bridge/v1/translation-status/{post_id}` — read-only,
  reports `trid`/`language_code` via `wpml_element_language_details`, and
  (with `?language_code=es`) whether a translation already exists via
  `wpml_object_id`, plus `needs_update` — WPML's own per-language status
  (`icl_translations.status`, read-only `SELECT`), used by
  `app/cli/sync.py` to decide between creating a new translation and
  re-translating only the blocks that changed.
- `register_post_meta()` for the three Yoast SEO fields (`_yoast_wpseo_title`,
  `_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw`) — not exposed via REST by
  Yoast by default.

## What's deliberately NOT implemented

`/create-job`, `/export-xliff/{job_id}`, `/import-xliff` all return `501`.
WPML's own job/XLIFF REST namespace (`wpml/tm/v1`) rejects Application
Password auth even for a full Administrator (confirmed empirically
2026-08-05 against `precision-gnss.com` — see `MEMORIA.md`), and the
underlying PHP class/method names it uses internally are undocumented.
Guessing at them here would be reckless: this file loads on **every single
request** (mu-plugins can't be toggled off from `wp-admin`), so one wrong
class/method name is a fatal PHP error that takes the whole site down —
English content included. These routes are stubbed to fail loudly and
safely until `PLA-ACCIO.md` task 1.8 is resolved properly (WPML support
ticket or direct source review).

## Deployment checklist (production — precision-gnss.com has no staging copy of WPML yet)

1. **Take a manual backup first.** UpdraftPlus is already active on the site
   (`AUDITORIA-INICIAL.md` §0.3) — run a manual backup, don't rely on the
   schedule.
2. **Re-run the syntax check** right before uploading, in case the file was
   edited since: `php -l gnss-bridge.php`.
3. **Deploy in a low-traffic window.**
4. Upload `gnss-bridge.php` to `wp-content/mu-plugins/gnss-bridge.php`
   (create the `mu-plugins` folder if it doesn't exist yet — WordPress loads
   any `.php` file placed directly in it automatically, no activation step,
   and **no way to deactivate it from `wp-admin`**).
5. Upload `wpml-config.xml` to the **active theme's root directory**
   (`wp-content/themes/{active-theme}/wpml-config.xml`) — WPML does not scan
   the `mu-plugins` folder for this file, only theme roots and regular
   plugin folders.
6. **Verify immediately**: load the homepage and 2-3 other pages in a normal
   browser tab to confirm the site is still up. Then check
   `GET /wp-json/` and confirm `gnss-bridge/v1` appears in the `namespaces`
   list.
7. **If anything breaks**: remove/rename
   `wp-content/mu-plugins/gnss-bridge.php` via FTP or the hosting file
   manager — this is the only way to disable a mu-plugin, `wp-admin` does
   not have a toggle for it.

## Auth

All routes require `current_user_can('edit_posts')`. Use a dedicated
`translation_bot` WordPress user with the **Editor** role (never
Administrator) and a **WordPress Application Password** generated for that
account — never the account's normal login password (WordPress core's REST
Basic Auth only accepts generated Application Passwords, confirmed
empirically 2026-08-05).

## Testing link-translation and translation-status safely

Always test against a translation post you created yourself for this
purpose — never call `link-translation` against the `element_id` of a real,
live English page on a guess. A wrong `trid` doesn't touch post content,
but it can scramble which posts WPML considers linked as translations of
each other.
