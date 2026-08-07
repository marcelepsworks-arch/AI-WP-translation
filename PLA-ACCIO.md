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

- [x] **1.1** Crear l'esquelet del mu-plugin (`gnss-bridge.php`) amb namespace REST `gnss-bridge/v1`. *(Fet 2026-08-05 — `wordpress-plugin/gnss-bridge/gnss-bridge.php`, sintaxi validada amb `php -l`. No desplegat encara.)*
- [x] **1.2** Implementar `POST /link-translation` que embolcalli els 3 hooks oficials (`wpml_element_type`, `wpml_element_language_details`, `wpml_set_element_language_details`) documentats a `BIBLIOGRAFIA.md` §2. *(Fet 2026-08-05.)*
  - *Verificació: ✅ FETA I PASSADA (2026-08-05, contra producció).* Desplegat `gnss-bridge`, creades dues pàgines de prova (`GNSS Bridge Test — do not publish`, id 6273 = original EN; `GNSS Bridge Test ES — do not publish`, id 6275), cridat `link-translation` amb `trid` real obtingut via `translation-status` (13329). Confirmat visualment a `wp-admin → Pages`: el comptador passa a "Spanish (1)" i la fila de la pàgina de prova mostra la icona d'edició (traduït) en lloc de "+" a la columna ES. **El camí d'escriptura via hooks funciona correctament en producció.**
- [x] **1.3** Implementar `GET /translation-status/{post_id}` — retorna `trid`/`language_code` (via `wpml_element_language_details`) i, amb `?language_code=es`, si ja existeix traducció (via `icl_object_id`). *(Fet 2026-08-05 — **canvi respecte al disseny original**: no es fa servir `needs_update`/`md5` d'`icl_translation_status` perquè no hi ha una via de hooks documentada per llegir-los directament; es fa servir `icl_object_id`, filtre oficial i estable des de fa anys, que respon la mateixa pregunta pràctica ("ja existeix traducció per a aquest idioma?").)*
  - 🐛✅ **Bug trobat i arreglat (2026-08-05).** Trobat: la part `icl_object_id` (`translation_exists`/`translated_post_id`) donava **falsos positius** — provat contra "Privacy Policy" (id 5784, confirmat sense traducció ES real a `WPML → Translation Dashboard`) i amb un codi d'idioma inventat (`xx`); en ambdós casos retornava l'ID de l'element original com si la traducció existís. Causa: `icl_object_id` és el filtre *legacy*, documentat com a poc fiable respectant `$return_original_if_missing = false`. Arreglat canviant al filtre modern `wpml_object_id` (mateixa signatura) + una comprovació defensiva addicional (`$translated_id !== $post_id`, mai hauria de coincidir amb l'original). **Reverificat i correcte** contra els 3 casos: Privacy Policy + `xx` → `false`; Privacy Policy + `es` → `false`; pàgina de prova 6273 + `es` (sap que SÍ té traducció, 6275) → `true`, `translated_post_id: 6275`.
- [x] **1.4** `register_post_meta()` per als camps Yoast (`_yoast_wpseo_title`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw`), amb `show_in_rest => true` i `auth_callback` que exigeix capacitat `edit_posts`. *(Fet 2026-08-05.)*
  - *Verificació: ✅ FETA I PASSADA (2026-08-05, contra producció).* `POST /wp/v2/pages/6273` (pàgina de prova) amb `{"meta": {"_yoast_wpseo_metadesc": "gnss-bridge test value"}}` → confirmat persistit amb un `GET` fresc immediatament després.
- [x] **1.5** Crear `wpml-config.xml` declarant `_elementor_data` (`action="translate" encoding="json"`) i els 3 camps Yoast. *(Fet 2026-08-05 — `wordpress-plugin/gnss-bridge/wpml-config.xml`, XML validat. Cap camp ACF detectat a la FASE 0 (no n'hi ha instal·lat). **Va al directori arrel del theme actiu, no a `mu-plugins`** — WPML no escaneja `mu-plugins` per aquest fitxer.)*
  - *Verificació: ⚠️ bloquejada per un bug natiu de WPML, no relacionat amb `gnss-bridge`.* La cua de traduccions (`Take and Translate`) falla amb "The translator could not be assigned to the job" — confirmat 2026-08-06 que és un bug conegut de WPML (columnes que falten a `wp_icl_translate_job`), no arreglable sense tocar la BD directament. **No bloqueja el projecte**: el pipeline no fa servir mai aquest camí (és la UI manual per a traductors humans), només `link-translation` via hooks, ja validat. Veure `MEMORIA.md` 2026-08-06. Verificació visual d'Elementor ajornada indefinidament, sense prioritat.
- [x] **1.6** Seguretat: totes les rutes de `gnss-bridge` exigeixen `current_user_can('edit_posts')`; cap ruta accessible anònimament. *(Fet 2026-08-05.)*
- [x] **1.7** Desplegat. **Canvi de pla (2026-08-05, veure `MEMORIA.md`):** WPML només s'ha instal·lat a **producció** (`precision-gnss.com`), no a l'staging — desplegat directament a producció seguint el checklist de seguretat de `wordpress-plugin/gnss-bridge/README.md` (backup UpdraftPlus fet, `php -l` validat abans de pujar, verificació immediata post-desplegament: `gnss-bridge/v1` apareix a `/wp-json/`, lloc segueix responent `200` a home i pàgines reals). `gnss-bridge.php` a `wp-content/mu-plugins/gnss-bridge.php`, `wpml-config.xml` a `wp-content/themes/hello-elementor/`.
- [x] **1.8** *(Nou, 2026-08-04)* Confirmar els noms reals de les funcions/classes internes de WPML per a jobs/XLIFF. *(Investigat 2026-08-05 — **conclusió negativa**: el namespace `wpml/tm/v1` existeix de debò (`xliff/fetch/{jobId}`, `jobs`, `jobs/assign`, `tp/apply-translations`...) però rebutja l'autenticació via Application Password fins i tot per a un Administrador complet (confirmat empíricament contra producció — `403` a `/wpml/tm/v1/jobs` amb un compte que sí té accés complet a `/wp/v2/settings`). No s'ha pogut confirmar cap nom de classe/mètode PHP intern. Es descarta cridar aquests endpoints; veure `BIBLIOGRAFIA.md` §11 actualitzat i `MEMORIA.md` 2026-08-05.)*
- [x] **1.9** *(Nou, 2026-08-04)* `POST /create-job`, `GET /export-xliff/{job_id}`, `POST /import-xliff` a `gnss-bridge`. *(Fet 2026-08-05 com a stub deliberat — retornen `501 gnss_bridge_not_implemented` en lloc d'intentar cridar funcions internes de WPML no confirmades (risc real de fatal error en producció, veure 1.8). Es completaran si/quan es confirmi la via correcta.)*

**Sortida de la fase:** mu-plugin desplegat i verificat manualment amb un cas de prova real.

---

## FASE 2 — WordPress Connector (Python)

- [x] **2.1** `app/wordpress/client.py`: `WordPressClient` amb doble autenticació (Basic Auth de l'staging + Application Password de WP, la segona té prioritat quan totes dues estan disponibles) i retry automàtic en 429/503. *(Fet 2026-07-23 — encara sense Application Password real creada; de moment només s'usa el Basic Auth de l'staging.)*
- [x] **2.2** `app/wordpress/content.py`: `get_post()`, `get_page()`, `get_pages()`, `get_post_meta()`, `get_page_meta()`. *(Fet 2026-07-23 — un sol fitxer `content.py` en lloc de `posts.py`/`pages.py` separats, ja que la lògica és pràcticament idèntica; `create_translation()` ajornat fins tenir Application Password amb permisos d'escriptura.)*
- [x] **2.3** `get_elementor_data(meta)`: **redissenyat com a funció pura** sobre un `dict` de meta ja obtingut (no torna a fer cap crida HTTP) — descobert durant una prova real contra l'staging que la versió inicial només funcionava amb posts, no amb pages (bug real, corregit amb TDD). **Confirmat empíricament contra l'staging real: `_elementor_data` NO s'exposa via REST per defecte** (calen `register_post_meta()` al mu-plugin, tal com ja preveia `BIBLIOGRAFIA.md` §6). *(Fet 2026-07-23.)*
- [x] **2.4** `app/wordpress/wpml.py`: `get_wpml_status()` i `link_translation()`. *(Fet 2026-08-04 — implementat contra el contracte d'endpoints ja documentat a `ROADMAP.md` FASE 1, provat amb 7 tests amb HTTP mockejat (`tests/wordpress/test_wpml.py`), seguint el mateix patró que `test_content.py`. **No validat contra un `gnss-bridge` real** — WPML segueix sense instal·lar a l'staging (`AUDITORIA-INICIAL.md` §0.2); es revisarà quan ho estigui, igual que `woocommerce_extractor.py`.)*
- [~] **2.5** Test d'integració: fet manualment contra l'staging real (`scripts/inspect_staging_page.py`, provat amb la pàgina "Precision Agriculture" i el post "RTK GNSS for Robotics") — lectura confirmada. Crear/vincular traducció **bloquejat** fins tenir WPML + Application Password amb permisos d'escriptura.

**Sortida de la fase:** ✅ connector Python de lectura provat contra l'staging real (14 tests nous, 74 en total al projecte). Pendent: 2.4 (bloquejat per WPML), escriptura/creació de traduccions (bloquejat per WPML + Application Password).

---

## FASE 3 — Content Extraction Engine

- [x] **3.1** `app/extraction/protected_content.py` (`is_protected_content()`) + `app/extraction/html_parser.py` (`extract_blocks()`): extractor de blocs semàntics (headings, paràgrafs, list items, blockquotes, botons/CTA, alt text) amb el format `content_id`/`type`/`context`/`source`/`translate` (brief secció 6), amb breadcrumb de context construït des de la jerarquia d'encapçalaments. *(Fet 2026-07-24 — treballa sobre l'HTML renderitzat de la pàgina, no sobre `_elementor_data` cru, perquè aquest camp no s'exposa via REST en aquest lloc; Elementor mateix genera aquest HTML, així que és una font vàlida i disponible avui.)*
- [x] **3.2** `app/extraction/content_extractor.py` (`extract_page_content()`): orquestra l'extracció d'un `dict` de pàgina/post de la REST API (títol, SEO Yoast quan hi és, cos). Aplica el filtratge de contingut protegit (brief secció 7.2: URLs, emails, shortcodes) via `is_protected_content()`. *(Fet 2026-07-24.)*
- [x] **✅ 3.3 COMPLETA (2026-08-06).** `app/extraction/elementor_extractor.py`: parseja `_elementor_data` real (no una versió reduïda de dry-run) i en tradueix el text de widgets coneguts (heading, text-editor, button, icon-box, image-box, call-to-action, counter, alert, testimonial, icon-list, tabs/accordion, alt d'imatges), preservant estructura/estils/URLs intactes. `gnss-bridge.php` ampliat per exposar `_elementor_data` via REST (calia registrar-ho a `rest_api_init`, no `init` — Elementor registra els mateixos camps encara més tard). Format inline (negreta/cursiva/enllaços) preservat via HTML intern en lloc de text pla. Provat de cap a cap contra producció real (pàgines "Precision Agriculture" i "pa-test"), verificat visualment. 17 tests nous per a l'extractor + tests actualitzats de `html_parser`/`content_extractor`. Veure `MEMORIA.md` 2026-08-06.
- [x] **3.4** Provat contra 3 pàgines/posts reals de l'staging (`scripts/extract_staging_page.py`): "Precision Agriculture" (164 blocs), "Contact us" (5 blocs), i el post "RTK GNSS for Robotics" (74 blocs). Cap URL/email va quedar marcat com a traduïble per error (0 blocs protegits en aquestes mostres — els enllaços del contingut real sempre van incrustats dins de text, no com a blocs solts; el mecanisme de protecció ja està cobert amb tests unitaris pel cas en què sí que calgui). *(Fet 2026-07-24.)*

**Sortida de la fase:** ✅ Content Extraction Engine funcional i validat amb contingut real (27 tests nous, 103 en total al projecte). Pendent: 3.3 (bloquejat, sense objecte fins tenir `_elementor_data` accessible).

- [x] **3.5** Ampliada `extract_page_content()` amb tots els camps pendents de `MAPEIG-CAMPS.md`: `excerpt.rendered`, `og_title`/`og_description` de Yoast (via `seo_extractor.py`, ja compartit amb WooCommerce), alt/caption de la imatge destacada (paràmetre opcional `featured_media`), i nom/descripció de categories i etiquetes (paràmetres opcionals `categories`/`tags`, reutilitzant `extract_taxonomy_terms()`). L'extracció es manté pura/sense I/O — qui crida ha de resoldre `featured_media`/`categories`/`tags` per separat. **Provat contra dades reals de l'staging** (no només amb tests unitaris): pàgina "Precision Agriculture" (171 blocs) i post "RTK GNSS for Robotics" (78 blocs, amb categoria "News" correctament filtrada). *(Fet 2026-07-24.)*
- [x] **3.6** *(Nou, 2026-07-24, a petició de l'usuari: "s'ha d'implementar per a altres WordPress amb WooCommerce")* `app/extraction/woocommerce_extractor.py` (`extract_product_content()`): extracció genèrica de productes WooCommerce (`wc/v3/products`) — nom, descripció llarga/curta, nota de compra, atributs/opcions, alt d'imatges de galeria, categories/etiquetes, SEO. **No lligat a cap lloc concret** — pensat per funcionar amb qualsevol WordPress+WooCommerce. Refactor associat: `app/extraction/seo_extractor.py` (`extract_yoast_blocks()`) i `app/extraction/taxonomy_extractor.py` (`extract_taxonomy_terms()`) extrets com a mòduls compartits, reutilitzats tant per productes com per posts/pages. **Provat amb 10 tests i dades sintètiques** (esquema oficial `wc/v3/products`) — **no validat contra un lloc WooCommerce real**, perquè cap n'hi ha dins l'abast actual. Detall complet a `MAPEIG-CAMPS.md` §6.

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

- [x] **5.1** Poblat `glossary/gnss.json` (14 termes) i `glossary/surveying.json` (10 termes) amb els termes exemple del brief (secció 8) + terminologia GNSS/RTK/surveying ben establerta. *(Fet 2026-07-23, ampliat 2026-08-04 amb 14 termes addicionals ben establerts — multipath, cycle slip, ambiguity resolution, static/kinematic positioning, carrier phase, pseudorange, elevation mask, control point, topographic survey, leveling, geoid, ellipsoid, point cloud, traverse, azimuth — són glossaris llavor (seed), 24 termes; falta ampliar-los amb terminologia real de precision-gnss.com quan hi hagi accés a l'staging (FASE 0). `forestry.json`/`spanish.json`/`global.json` encara no creats — no hi ha contingut real per poblar-los sense inventar-se termes.)*
- [x] **5.2** `app/translation/glossary.py`: `GlossaryEntry` (model Pydantic), `load_glossary_files(paths)`, `get_relevant_terms(text, entries, language)` (matching per paraula completa, case-insensitive, filtrat per idioma) i `validate_translation(source_text, translated_text, entries, language)` (comprovació local determinista, sense crida a l'API, dels termes `mandatory`). *(Fet 2026-07-23.)*
- [x] **5.3** `get_relevant_terms()` ja retorna objectes `GlossaryTerm` directament compatibles amb `DeepSeekClient.translate()`/`.validate_terminology()` — no cal cap capa d'adaptació addicional. *(Fet 2026-07-23 — falta encara la integració end-to-end dins un pipeline orquestrat, que és FASE 8.)*
- [x] **5.4** Test: 12 tests (`tests/translation/test_glossary.py`) verifiquen que "base station"/"rover"/"fix" es filtren i validen correctament segons `mandatory`/`notes`, incloent matching de paraula completa (`fix` no fa match dins `prefix`/`suffix`) i filtratge per idioma. *(Fet 2026-07-23 — pendent ampliar amb frases reals del lloc quan hi hagi accés a l'staging.)*

**Sortida de la fase:** ✅ Glossary Engine funcional i provat — codi a `app/translation/glossary.py`, glossaris llavor a `glossary/*.json`, tests a `tests/translation/test_glossary.py`, pla a `docs/superpowers/plans/2026-07-23-glossary-engine.md`. Pendent: ampliar el glossari amb termes reals (bloquejat per accés a l'staging, FASE 0) i la integració end-to-end (FASE 8).

---

## FASE 6 — Translation Memory i detecció de canvis

- [x] **6.1** `app/storage/database.py` (`get_connection()`, `SCHEMA`) + `app/storage/models.py` (`upsert_source_content()`, `save_content_block()`, `get_content_block_hash()`): taules SQLite `source_content`, `content_blocks`, `translations`, `terminology`, `qa_results` (esquema exacte del brief secció 18). *(Fet 2026-07-24.)*
- [x] **6.2** `app/synchronization/change_detector.py`: `hash_text()` (SHA-256) + `detect_changed_blocks()`, funció pura (read-only) que retorna `"new"`/`"changed"`/`"unchanged"` per bloc, consumint `ContentBlock` de FASE 3 directament. *(Fet 2026-07-24.)*
- [ ] **6.3** **(Millora derivada de la investigació)** afegir contrast opcional amb `icl_translation_status.md5`/`needs_update` (via `gnss-bridge/v1/translation-status/{id}`) com a doble verificació a nivell de pàgina — **bloquejat**, `gnss-bridge` no existeix fins tenir WPML.
- [x] **6.4** Test: modificar un sol paràgraf i confirmar que només aquest bloc es marca `"changed"` (`test_detect_changed_blocks_marks_changed_when_only_one_paragraph_edited`) — exactament l'escenari que demana el brief. *(Fet 2026-07-24, amb SQLite en memòria, sense necessitat de contingut real per a aquest test concret.)*

**Sortida de la fase:** ✅ Translation Memory funcional (13 tests nous, 117 en total). Pendent: 6.3 (bloquejat per WPML).

---

## FASE 7 — QA Engine

- [x] **7.1** `app/qa/numerical_checker.py` (`check_numbers()`): compara valors numèrics/decimals/rangs, amb normalització del separador decimal EN (`.`) / ES (`,`) perquè no doni falsos positius. *(Fet 2026-07-24 — provat literalment amb l'exemple del brief secció 12.1: "1 cm accuracy"→"1 cm de precisión" PASS, →"2 cm de precisión" FAIL.)*
- [x] **7.2** `app/qa/terminology_checker.py` (`check_protected_terms()`): verifica que els termes protegits presents a l'original sobreviuen literalment (sensible a majúscules) a la traducció. *(Fet 2026-07-24.)*
- [x] **7.3** `app/qa/url_validator.py` (`check_urls()`): compara el conjunt d'URLs de l'original i la traducció, informa d'URLs perdudes o afegides. *(Fet 2026-07-24.)*
- [ ] **7.4** `app/qa/html_validator.py`: **ajornat** — els blocs extrets a FASE 3 són text pla (`BeautifulSoup.get_text()` ja elimina les etiquetes), així que ara mateix no hi ha HTML real a validar. Es reprendrà si una fase futura preserva HTML inline.
- [x] **7.5** `app/qa/semantic_checker.py`: **ja cobert per `DeepSeekClient.review()` (FASE 4.4)** — no s'ha duplicat codi; `scoring.py` consumeix directament el seu resultat `passed`.
- [x] **7.6** Sistema de puntuació (`app/qa/scoring.py`, `score_translation()`): combina els 3 checkers mecànics + el resultat del Reviewer en una puntuació 0-100 amb penalitzacions additives, i llindars exactes del brief secció 13 (`≥95 auto_approve / 85-94 human_review / <85 reject`). *(Fet 2026-07-24 — simplificació pragmàtica respecte a les "5 dimensions" del brief: en lloc d'inventar puntuacions independents per a 5 categories sense dades reals per calibrar-les, es combinen els 4 senyals objectius que sí es poden mesurar mecànicament.)*
- [x] **7.7** Test amb l'error exacte del brief (secció 12.1: "1 cm"→"2 cm") injectat deliberadament: `check_numbers` el detecta, `score_translation` dona puntuació 60 i decisió `reject`. *(Fet 2026-07-24.)*

**Sortida de la fase:** ✅ QA Engine complet i provat (19 tests nous, 136 en total). Detecta els 3 tipus d'error deliberats (numèric, terminològic, URL) més el fallback de revisió semàntica ja existent. Pendent: 7.4 (sense objecte encara).

---

## FASE 8 — Integració WPML (orquestració completa)

- [x] **✅ FASE 8 COMPLETA I VERIFICADA EN PRODUCCIÓ (2026-08-06).** `app/cli/translate.py` (`translate_page()`): Extract → Glossary → DeepSeek (Translator+Reviewer) → QA → Score → escriptura WordPress (`draft`) → `link-translation`. Provat de cap a cap contra `precision-gnss.com` real (pàgina de prova 6273 → nova traducció 6290, `draft`, vinculada correctament: `trid=13329`, `translation_exists=true`). 13 tests nous (`tests/cli/test_translate.py`), 196 tests en total. **Limitació coneguda i documentada al mòdul:** el cos HTML es reconstrueix a partir dels `ContentBlock` extrets (`heading`→`h2`, `paragraph`/`list_item`→`p`), perdent el nivell real de capçalera i qualsevol format/enllaç inline — vàlid per validar el pipeline, no encara un round-trip fidel d'Elementor (depèn de la 3.3, encara ajornada).
- [x] **8.1** `app/wordpress/wpml.py`: `link_translation()` orquestrat des de `translate_page()` després que la QA (FASE 7) doni `auto_approve`/`human_review` (mai s'escriu si `reject`).
- [x] **8.2** `app/cli/translate.py`: flux complet (brief secció 16) end-to-end sobre **una** pàgina de prova. *(Fet 2026-08-06, veure resum de fase amunt.)*
- [x] **8.3** `AUTO_PUBLISH` no és una variable d'entorn: la traducció es crea sempre com `draft`, sense excepció, codificat directament al mòdul (no és "un flag mal posat" de distància). *(Fet 2026-08-06.)*
- [x] **8.4** Logging complet de cada pas via el mòdul estàndard `logging` de Python (no una classe `Audit Logger` separada — no calia cap abstracció addicional). *(Fet 2026-08-06 — cada bloc traduït (decisió/puntuació/confiança), la decisió global, la creació de l'esborrany i la vinculació (o l'avís si no hi ha `trid` i no es pot vincular) queden registrats. Sortida doble: consola + fitxer `logs/translate_audit.log` (afegit a `.gitignore`, pot contenir contingut real). 3 tests nous amb `caplog`.)*
- [x] **8.5** Test end-to-end complet amb 1 pàgina simple: `translate_page(..., post_id=6273, ...)` fins a veure el draft ES (6290) correctament vinculat i amb contingut traduït dins `wp-admin`. *(Fet i verificat 2026-08-06.)*
- [x] **8.6** *(Nou, 2026-08-04)* `app/wordpress/xliff.py`: parseja XLIFF 1.2 (format d'export de WPML) cap a `ContentBlock` (FASE 3) i serialitza els blocs traduïts (sortida de FASE 4-7, sense modificar-los) cap a `<target>` dins l'XLIFF. *(Fet 2026-08-04 — `parse_xliff()`/`build_translated_xliff()`, tolerant amb i sense namespace XLIFF, 8 tests (`tests/wordpress/test_xliff.py`). **No validat encara contra un export XLIFF real de WPML** (WPML no instal·lat) — implementat contra l'especificació estàndard XLIFF 1.2, es revisarà quan hi hagi un export real disponible, igual que `woocommerce_extractor.py`.)*
- [x] **8.7** *(Nou, 2026-08-04)* Camí "traductor local": `start_job()` (crea job + exporta XLIFF + parseja a `ContentBlock`) i `complete_job()` (insereix traduccions + importa XLIFF) a `app/wordpress/wpml.py`. *(Fet 2026-08-04 — implementat com dues funcions seqüenciables, no una única `submit_via_job()`: entremig, qui crida ha d'executar el pipeline de traducció (FASE 4-7) sobre els `ContentBlock` que retorna `start_job()`, cosa que no pertany a aquest mòdul. 7 tests amb HTTP mockejat. **No validat contra WPML real.** Pendent per a `app/cli/translate.py` (8.2): triar entre aquest camí i `link_translation()` amb `.env` `WPML_WRITE_MODE=hooks|job`.)*
  - *Verificació (pendent, quan hi hagi WPML real):* sobre una pàgina de prova diferent de la de 8.5, confirmar que el job apareix com "Complete" al dashboard de WPML i que el resultat final a `icl_translations` és equivalent al del camí `hooks` (mateix `trid`, mateix contingut).

**Sortida de la fase:** una pàgina real traduïda de cap a cap, revisada manualment i aprovada.

---

## FASE 9 — Pilot (5 pàgines)

- [~] **9.1** Executar el flux complet sobre les 5 pàgines seleccionades a la FASE 0.6 (contra producció, no staging — veure `MEMORIA.md` 2026-08-05). **1 de 5 feta:** "Contact us" (id 4315) → esborrany 6291, `auto_approve` a totes les unitats (títol, extracte, SEO x4, capçalera, botó), vinculat correctament, original EN intacte. *(2026-08-06.)*
- [ ] **9.2** Revisió humana de cadascuna (nadiu/tècnic castellà) abans de publicar. **Pendent per a "Contact us" (6291)** i per a la resta.
- [ ] **9.3** Documentar resultats (puntuacions QA, temps, cost real en tokens) a `MEMORIA.md`. Puntuacions de la primera pàgina ja registrades (veure entrada 2026-08-06); falta el cost real en tokens.
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
