# Pla d'acció — GNSS AI Translation Engine

> Desglossament operatiu de `ROADMAP.md` en tasques concretes i verificables. Cada tasca té un criteri de "fet" explícit. **Cap d'aquestes tasques s'ha començat a executar encara** — aquest document és la guia per quan s'aprovi engegar el desenvolupament.

Llegenda d'estat: `[ ]` pendent · `[~]` en curs · `[x]` fet

---

## FASE 0 — Auditoria i validació d'entorn

- [x] **0.0** Còpia fidel de producció: **parcialment confirmat**. El contingut (pages/posts) coincideix amb producció, però **la configuració de plugins NO coincideix amb el que teníem assumit** — veure 0.2. *(Fet 2026-07-23.)*
- [x] **0.1** Credencials i accessos: Basic Auth de l'staging ✅ i sessió d'administrador WordPress ✅, ambdues verificades i funcionals (guardades només a `.env` local). **Pendent:** Application Password dedicada (usuari `translation_bot`), credencials MySQL read-only, `DEEPSEEK_API_KEY` permanent. *(Fet parcialment 2026-07-23.)*
- [x] **0.2** 🛑 **WPML no està instal·lat a l'staging** (ni actiu, ni inactiu, ni com a mu-plugin, ni als namespaces de la REST API). Contradiu el supòsit previ. Detall complet i decisió a `AUDITORIA-INICIAL.md` §0.2. *(Fet/troballa crítica 2026-07-23.)*
- [x] **0.3** Elementor **Pro** 4.1.5 (plugin) + 4.0.4 (Elementor Pro) confirmat. Yoast SEO 28.0 + Premium 27.1. Sense WooCommerce, sense ACF. Fluent Forms instal·lat però inactiu. *(Fet 2026-07-23.)*
- [ ] **0.4** `DESCRIBE` de taules `icl_*`: **bloquejat** — com que WPML no està instal·lat, aquestes taules encara no existeixen a la BD. A més, encara no tenim credencials MySQL. Pendent fins instal·lar WPML.
- [x] **0.5** Inventari de contingut generat via REST API: **24 pages + 17 posts**, sense custom post types propis (només interns d'Elementor/FluentCRM). Llista completa a `AUDITORIA-INICIAL.md` §0.5. Confirmat empíricament que Yoast/`_elementor_data` no s'exposen per defecte via REST — calen `register_post_meta()` al mu-plugin, tal com ja preveia `BIBLIOGRAFIA.md` §6. *(Fet 2026-07-23.)*
- [x] **0.6** Selecció provisional de pàgines de prova feta (`AUDITORIA-INICIAL.md` §0.6) — a confirmar visualment en arribar a la FASE 9. *(Fet 2026-07-23.)*

**Sortida de la fase:** ✅ `AUDITORIA-INICIAL.md` creat amb l'inventari real. **Desviació important respecte al `ROADMAP.md`: WPML no instal·lat** — bloqueja FASE 1/8 i la part de 0.4, però la resta de FASE 0 està completa.

---

## FASE 1 — Component pont `gnss-bridge` (mu-plugin)

- [ ] **1.1** Crear l'esquelet del mu-plugin (`gnss-bridge.php`) amb namespace REST `gnss-bridge/v1`.
- [ ] **1.2** Implementar `POST /link-translation` que embolcalli els 3 hooks oficials (`wpml_element_type`, `wpml_element_language_details`, `wpml_set_element_language_details`) documentats a `BIBLIOGRAFIA.md` §2.
  - *Verificació:* crear manualment un post ES de prova i confirmar via `wp-admin → WPML → Translation Management` que apareix correctament vinculat al `trid` de l'original.
- [ ] **1.3** Implementar `GET /translation-status/{post_id}` que retorni `trid`, idiomes ja traduïts i el flag `needs_update`/`md5` d'`icl_translation_status`.
- [ ] **1.4** `register_post_meta()` per als camps Yoast identificats a la FASE 0 (típicament `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw`), amb `show_in_rest => true` i `auth_callback` que exigeixi capacitat `edit_posts`.
  - *Verificació:* `POST /wp/v2/pages/{id}` amb `{"meta": {"_yoast_wpseo_metadesc": "test"}}` i confirmar canvi reflectit a l'editor Yoast.
- [ ] **1.5** Crear `wpml-config.xml` declarant `_elementor_data` (`action="translate" encoding="json"`) i qualsevol camp ACF detectat a la FASE 0.
  - *Verificació:* seleccionar una pàgina Elementor de prova des del Translation Dashboard de WPML i confirmar que els widgets apareixen com a contingut traduïble.
- [ ] **1.6** Seguretat: totes les rutes de `gnss-bridge` exigeixen autenticació (Application Password) i capacitat mínima necessària; cap ruta accessible anònimament.
- [ ] **1.7** Desplegar exclusivament a l'**staging** de precision-gnss.com (confirmat disponible). El desplegament a producció és una decisió posterior i explícita, fora d'abast d'aquesta fase.

**Sortida de la fase:** mu-plugin desplegat i verificat manualment amb un cas de prova real.

---

## FASE 2 — WordPress Connector (Python)

- [x] **2.1** `app/wordpress/client.py`: `WordPressClient` amb doble autenticació (Basic Auth de l'staging + Application Password de WP, la segona té prioritat quan totes dues estan disponibles) i retry automàtic en 429/503. *(Fet 2026-07-23 — encara sense Application Password real creada; de moment només s'usa el Basic Auth de l'staging.)*
- [x] **2.2** `app/wordpress/content.py`: `get_post()`, `get_page()`, `get_pages()`, `get_post_meta()`, `get_page_meta()`. *(Fet 2026-07-23 — un sol fitxer `content.py` en lloc de `posts.py`/`pages.py` separats, ja que la lògica és pràcticament idèntica; `create_translation()` ajornat fins tenir Application Password amb permisos d'escriptura.)*
- [x] **2.3** `get_elementor_data(meta)`: **redissenyat com a funció pura** sobre un `dict` de meta ja obtingut (no torna a fer cap crida HTTP) — descobert durant una prova real contra l'staging que la versió inicial només funcionava amb posts, no amb pages (bug real, corregit amb TDD). **Confirmat empíricament contra l'staging real: `_elementor_data` NO s'exposa via REST per defecte** (calen `register_post_meta()` al mu-plugin, tal com ja preveia `BIBLIOGRAFIA.md` §6). *(Fet 2026-07-23.)*
- [ ] **2.4** `app/wordpress/wpml.py`: `get_wpml_status()` i `link_translation()` — **bloquejat**, WPML no instal·lat a l'staging (`AUDITORIA-INICIAL.md` §0.2).
- [~] **2.5** Test d'integració: fet manualment contra l'staging real (`scripts/inspect_staging_page.py`, provat amb la pàgina "Precision Agriculture" i el post "RTK GNSS for Robotics") — lectura confirmada. Crear/vincular traducció **bloquejat** fins tenir WPML + Application Password amb permisos d'escriptura.

**Sortida de la fase:** ✅ connector Python de lectura provat contra l'staging real (14 tests nous, 74 en total al projecte). Pendent: 2.4 (bloquejat per WPML), escriptura/creació de traduccions (bloquejat per WPML + Application Password).

---

## FASE 3 — Content Extraction Engine

- [ ] **3.1** `app/extraction/strings.py` + `html_parser.py`: extractor de blocs semàntics genèrics (paràgrafs, headings, CTA, alt text) amb el format `content_id`/`type`/`context`/`source` (brief secció 6).
- [ ] **3.2** `app/extraction/content_extractor.py`: orquestra extracció per tipus de post/pàgina, aplicant la llista de contingut protegit (brief secció 7.2: URLs, emails, SKUs, model numbers, CSS/JS, shortcodes, API keys, IDs).
- [ ] **3.3** `app/extraction/elementor_extractor.py` **(versió reduïda)**: només per a `--dry-run` (compta blocs/paraules/cost estimat) i per detectar widgets Elementor no estàndard no coberts per la integració nativa WPML (veure `BIBLIOGRAFIA.md` §4, "Registering Custom Elementor Widgets").
- [ ] **3.4** Test amb les 5-10 pàgines seleccionades a la FASE 0: confirmar que cap URL, email, SKU o shortcode acaba marcat com a traduïble per error.

**Sortida de la fase:** extractor que separa correctament traduïble/protegit a les pàgines de prova, verificat manualment bloc a bloc en almenys 2 pàgines.

---

## FASE 4 — Translation Engine (DeepSeek)

- [x] **4.1** `app/translation/deepseek_client.py`: client via SDK `openai` amb `base_url=https://api.deepseek.com`, JSON mode activat, model configurable (`DeepSeekClient(api_key, base_url, model, qa_model)`). *(Fet 2026-07-23; `qa_model` afegit 2026-07-23 quan es va construir el Reviewer/Validator.)*
- [x] **4.2** `app/translation/prompt_builder.py`: implementa el prompt de sistema exacte de la secció 10 del brief (15 regles MUST + 6 regles MUST NOT), parametritzat per idioma destí i glossari opcional. *(Fet 2026-07-23.)*
- [x] **4.3** Crida "Translator" aïllada (brief secció 9.A): `DeepSeekClient.translate()` retorna `TranslationResult` validat contra l'schema de la secció 11 (`app/translation/schemas.py`). *(Fet 2026-07-23 — implementat com a mètode del client, no com a fitxer `translator.py` separat.)*
- [x] **4.4** Segona crida independent "Technical Reviewer" (secció 9.B, `DeepSeekClient.review()` → `ReviewResult`) i tercera "Terminology Validator" (secció 9.C, `DeepSeekClient.validate_terminology()` → `TerminologyValidationResult`) — **cada una és una crida `_call()` separada, mai combinades**. Totes tres crides (`translate`/`review`/`validate_terminology`) comparteixen el mateix client HTTP però `review`/`validate_terminology` fan servir `qa_model` mentre que `translate` fa servir `model`, tal com preveu `.env` (`DEFAULT_MODEL` vs `QA_MODEL`). *(Fet 2026-07-23 — pla a `docs/superpowers/plans/2026-07-23-deepseek-reviewer-terminology-validator.md`.)*
- [x] **4.5** `app/translation/chunking.py`: `chunk_text()` divideix per paràgrafs (amb fallback a frases per a un paràgraf sol massa llarg, sense mai tallar a mig número/unitat/terme), preservant el context; `translate_long_text()` divideix, tradueix cada tros amb el mateix `context`/glossari i els torna a ajuntar. *(Fet 2026-07-23 — pla a `docs/superpowers/plans/2026-07-23-chunking.md`. Pressupost per caràcters, no per tokens — es reavaluarà si cal quan hi hagi contingut real.)*
- [x] **4.6** Test unitari: 60 tests automatitzats (mockejats) cobrint settings/schema/prompt/client/glossary/chunking. **A més**, validat amb 4 crides reals a l'API (`DEEPSEEK_API_KEY` real de l'usuari, 2026-07-23): confidence ≥0.95 en tots els casos, terminologia del glossari aplicada correctament, i el `review()` va detectar correctament un canvi subtil de precisió tècnica ("within 5s" → "menos de 5s") en una de les traduccions — confirma que el pipeline Translator+Reviewer funciona com a xarxa de seguretat real. *(Fet 2026-07-23 — encara falten 10-15 frases reals extretes específicament de precision-gnss.com, bloquejat per accés a l'staging.)*

**Sortida de la fase:** ✅ **FASE 4 completa** — client DeepSeek (Translator + Reviewer + Terminology Validator + chunking) funcional, provat (mockejat) i validat amb l'API real — codi a `app/config/settings.py`, `app/translation/{schemas,prompt_builder,deepseek_client,chunking}.py`, tests a `tests/`, plans a `docs/superpowers/plans/2026-07-23-deepseek-translation-client.md`, `2026-07-23-deepseek-reviewer-terminology-validator.md` i `2026-07-23-chunking.md`.

---

## FASE 5 — Glossary Engine

- [x] **5.1** Poblat `glossary/gnss.json` (6 termes) i `glossary/surveying.json` (4 termes) amb els termes exemple del brief (secció 8) + terminologia GNSS/RTK/surveying ben establerta. *(Fet 2026-07-23 — són glossaris llavor (seed), NOMÉS 10 termes; falta ampliar-los amb terminologia real de precision-gnss.com quan hi hagi accés a l'staging (FASE 0). `forestry.json`/`spanish.json`/`global.json` encara no creats — no hi ha contingut real per poblar-los sense inventar-se termes.)*
- [x] **5.2** `app/translation/glossary.py`: `GlossaryEntry` (model Pydantic), `load_glossary_files(paths)`, `get_relevant_terms(text, entries, language)` (matching per paraula completa, case-insensitive, filtrat per idioma) i `validate_translation(source_text, translated_text, entries, language)` (comprovació local determinista, sense crida a l'API, dels termes `mandatory`). *(Fet 2026-07-23.)*
- [x] **5.3** `get_relevant_terms()` ja retorna objectes `GlossaryTerm` directament compatibles amb `DeepSeekClient.translate()`/`.validate_terminology()` — no cal cap capa d'adaptació addicional. *(Fet 2026-07-23 — falta encara la integració end-to-end dins un pipeline orquestrat, que és FASE 8.)*
- [x] **5.4** Test: 12 tests (`tests/translation/test_glossary.py`) verifiquen que "base station"/"rover"/"fix" es filtren i validen correctament segons `mandatory`/`notes`, incloent matching de paraula completa (`fix` no fa match dins `prefix`/`suffix`) i filtratge per idioma. *(Fet 2026-07-23 — pendent ampliar amb frases reals del lloc quan hi hagi accés a l'staging.)*

**Sortida de la fase:** ✅ Glossary Engine funcional i provat — codi a `app/translation/glossary.py`, glossaris llavor a `glossary/*.json`, tests a `tests/translation/test_glossary.py`, pla a `docs/superpowers/plans/2026-07-23-glossary-engine.md`. Pendent: ampliar el glossari amb termes reals (bloquejat per accés a l'staging, FASE 0) i la integració end-to-end (FASE 8).

---

## FASE 6 — Translation Memory i detecció de canvis

- [ ] **6.1** `app/storage/models.py` + `database.py`: taules SQLite `source_content`, `content_blocks`, `translations`, `terminology`, `qa_results` (esquema exacte del brief secció 18).
- [ ] **6.2** `app/synchronization/change_detector.py`: hash SHA-256 per bloc; comparació `source_hash_old != source_hash_new` per determinar retraducció.
- [ ] **6.3** **(Millora derivada de la investigació)** afegir contrast opcional amb `icl_translation_status.md5`/`needs_update` (via `gnss-bridge/v1/translation-status/{id}`) com a doble verificació a nivell de pàgina.
- [ ] **6.4** Test: modificar un sol paràgraf d'una pàgina de prova i confirmar que només aquest bloc es marca per retraduir.

**Sortida de la fase:** sistema de detecció de canvis provat amb un cas real de modificació parcial.

---

## FASE 7 — QA Engine

- [ ] **7.1** `app/qa/numerical_checker.py`: comparació de valors numèrics/decimals/percentatges/rangs i unitats (mm, cm, m, km, Hz, MHz, V, A).
- [ ] **7.2** `app/qa/terminology_checker.py`: verificació que termes protegits (GNSS, RTK, NTRIP, NMEA 2000, ZED-F9P, noms de producte) no s'han alterat.
- [ ] **7.3** `app/qa/url_validator.py`: comparació d'URLs original vs. traduït, alerta en qualsevol discrepància.
- [ ] **7.4** `app/qa/html_validator.py`: integritat d'etiquetes HTML/Elementor.
- [ ] **7.5** `app/qa/semantic_checker.py`: crida DeepSeek "Reviewer" (FASE 4.4) per detectar informació afegida/eliminada/alterada.
- [ ] **7.6** Sistema de puntuació (brief secció 13): 5 dimensions 0-100, llindars `≥95 auto-approve / 85-94 revisió humana / <85 rebuig`, `<95` obligatori a revisió manual per a productes/claims tècnics.
- [ ] **7.7** Test: injectar deliberadament un error (canviar "1 cm" per "2 cm" en una traducció de prova) i confirmar que el QA el detecta i el marca FAIL.

**Sortida de la fase:** QA Engine que detecta correctament almenys 3 tipus d'error injectats deliberadament (numèric, terminològic, URL).

---

## FASE 8 — Integració WPML (orquestració completa)

- [ ] **8.1** `app/wordpress/wpml.py` (`WPMLAdapter`): orquestra `link_translation()` (FASE 2.4) després que la QA (FASE 7) doni PASS.
- [ ] **8.2** `app/cli/translate.py`: implementa el flux complet (brief secció 16) end-to-end sobre **una** pàgina de prova.
- [ ] **8.3** `AUTO_PUBLISH=false` per defecte: la traducció es crea com `draft`/`pending`, mai `publish` automàtic.
- [ ] **8.4** Logging complet de cada pas (`app/cli` + un `Audit Logger` transversal) — cap acció sense traça.
- [ ] **8.5** Test end-to-end complet amb 1 pàgina simple: des de `python translate.py --post-id X --language es` fins a veure el draft ES correctament vinculat i amb contingut traduït dins `wp-admin`.

**Sortida de la fase:** una pàgina real traduïda de cap a cap, revisada manualment i aprovada.

---

## FASE 9 — Pilot (5 pàgines)

- [ ] **9.1** Executar el flux complet sobre les 5 pàgines seleccionades a la FASE 0.6.
- [ ] **9.2** Revisió humana de cadascuna (nadiu/tècnic castellà) abans de publicar.
- [ ] **9.3** Documentar resultats (puntuacions QA, temps, cost real en tokens) a `MEMORIA.md`.
- [ ] **9.4** Decisió go/no-go per a l'escalat, amb el client.

---

## FASE 10 — Escalat i manteniment

- [ ] **10.1** `python sync.py` en cron (freqüència a decidir amb el client — diària/setmanal).
- [ ] **10.2** Ampliació a més idiomes (fr, de, it, pt) reutilitzant la mateixa arquitectura.
- [ ] **10.3** Revisió de costos reals DeepSeek acumulats vs. estimació inicial.

---

## Riscos identificats (a vigilar durant l'execució)

| Risc | Origen | Mitigació |
|---|---|---|
| WPML actualitza a la 5.0 (canvi de motor intern) durant el desenvolupament | `BIBLIOGRAFIA.md` §1 | Fixar la versió de WPML al `.env`/documentació, no actualitzar producció sense revalidar `gnss-bridge` |
| Esquema real de taules `icl_*` difereix del documentat aquí (no hi ha diccionari oficial complet) | `BIBLIOGRAFIA.md` §1 | FASE 0.4 (`DESCRIBE` real) abans de donar per bo cap supòsit |
| Camps Yoast no escrivibles via REST sense el mu-plugin | `BIBLIOGRAFIA.md` §6 | Coberta a FASE 1.4 |
| Widgets Elementor personalitzats no detectats per la integració nativa WPML | `BIBLIOGRAFIA.md` §4 | Registrar-los amb "WPML Multilingual Tools" o cobrir-los amb l'extractor propi (FASE 3.3) |
| Creixement excessiu de `icl_translate`/`icl_translate_job` (reportat als fòrums oficials) | `BIBLIOGRAFIA.md` §1 | Monitoritzar mida de BD durant el pilot; no és responsabilitat directa del nostre script però pot alentir consultes |
| Cost DeepSeek superior a l'estimat | Brief secció 17.1 | Mode `--dry-run` obligatori abans de qualsevol traducció real, tracking de tokens (FASE 4.1) |
