# Pla d'acció — GNSS AI Translation Engine

> Desglossament operatiu de `ROADMAP.md` en tasques concretes i verificables. Cada tasca té un criteri de "fet" explícit. **Cap d'aquestes tasques s'ha començat a executar encara** — aquest document és la guia per quan s'aprovi engegar el desenvolupament.

Llegenda d'estat: `[ ]` pendent · `[~]` en curs · `[x]` fet

---

## FASE 0 — Auditoria i validació d'entorn

- [ ] **0.0** Confirmar amb el client/equip d'hosting que l'**staging** és una còpia fidel i actualitzada de producció (mateixes versions de WordPress, WPML, Elementor i plugins actius) — si no ho és, sol·licitar que es regeneri abans de continuar.
- [ ] **0.1** Confirmar credencials i accessos necessaris abans de tocar res (**tots contra l'staging, no producció**):
  - Application Password de WordPress (usuari `translation_bot`, rol Editor) a l'staging.
  - Credencials MySQL **només lectura** de l'staging (per auditoria; verificar amb el proveïdor d'hosting que es pot crear un usuari read-only).
  - `DEEPSEEK_API_KEY` de prova amb quota limitada.
  - *Verificació:* poder fer `curl -u user:app_password https://staging.precision-gnss.com/wp-json/wp/v2/posts?per_page=1` amb resposta 200 (substituir per la URL real de l'staging).
- [ ] **0.2** Confirmar versió exacta de WPML instal·lada a l'staging i el pla actiu (CMS/Agency) des de `wp-admin → WPML → Support` o `wp plugin list` si hi ha accés WP-CLI.
  - *Verificació:* anotar número de versió (esperat: 4.9.x segons `BIBLIOGRAFIA.md` §1) i comprovar que **no** és la 5.0 Beta.
- [ ] **0.3** Confirmar versió d'Elementor (Free/Pro) i llistar plugins actius que puguin registrar contingut traduïble (ACF, formularis, popups). Confirmar que no hi ha WooCommerce ni cap plugin de botiga actiu (ja confirmat pel client, però verificar-ho a l'staging real).
- [ ] **0.4** Amb l'accés MySQL read-only, fer `DESCRIBE` de totes les taules `icl_*` reals i comparar amb la taula de `BIBLIOGRAFIA.md` §1. Documentar qualsevol diferència a `AUDITORIA-INICIAL.md`.
- [ ] **0.5** Generar l'inventari de contingut traduïble en format JSON tal com mostra el brief secció 4, **prioritzant posts/pages/CPTs/Elementor/Yoast** (el contingut editorial). Registrar l'existència de strings de tema/plugins com a referència, però marcar-les explícitament com a **fora d'abast** del primer lliurament.
- [ ] **0.6** Seleccionar les 5-10 pàgines de prova (has d'incloure com a mínim: 1 simple, 1 Elementor complexa, 1 article, 1 amb taula/bloc especial, 1 amb molts enllaços interns).
  - *Verificació:* llista d'URLs concretes documentada a `AUDITORIA-INICIAL.md`.

**Sortida de la fase:** `AUDITORIA-INICIAL.md` amb inventari real + confirmació que els supòsits del `ROADMAP.md` són vàlids (o llista de desviacions a incorporar-hi).

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

- [ ] **2.1** `app/wordpress/client.py`: client HTTP base amb Application Password auth, retries i gestió d'errors 401/403/429.
- [ ] **2.2** `app/wordpress/posts.py` / `pages.py`: `get_post()`, `get_pages()`, `get_post_meta()`, `create_translation()` (crea com a `draft`).
- [ ] **2.3** `app/wordpress/elementor.py`: `get_elementor_data()` (lectura de `_elementor_data` via `meta` a REST, cal `show_in_rest` per aquest camp — verificar a FASE 0/1 si ja ho exposa Elementor o cal afegir-ho al mu-plugin).
- [ ] **2.4** `app/wordpress/wpml.py`: `get_wpml_status()` i `link_translation()`, ambdós consumint `gnss-bridge/v1/*` (FASE 1).
- [ ] **2.5** Test d'integració: llegir una pàgina real, crear una traducció buida, vincular-la, i confirmar via `wp-admin` que WPML la reconeix correctament (sense encara contingut traduït — això és FASE 8).

**Sortida de la fase:** connector Python provat contra l'entorn real (o staging), capaç de llegir i crear/vincular sense encara traduir res.

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
- [ ] **4.5** `app/translation/chunking.py`: divisió de contingut llarg en blocs per no superar límits de context/cost, preservant context (secció 6 del brief: `"context": "RTK Applications > Archaeology"`).
- [~] **4.6** Test unitari: 39 tests automatitzats (mockejats) cobrint settings/schema/prompt/client (translate + review + validate_terminology). **Pendent:** provar amb 10-15 frases tècniques reals extretes de precision-gnss.com i una crida real a l'API (`scripts/translate_sample.py`, requereix `DEEPSEEK_API_KEY` real de l'usuari).

**Sortida de la fase:** ✅ client DeepSeek complet (Translator + Reviewer + Terminology Validator) funcional i provat (mockejat) — codi a `app/config/settings.py`, `app/translation/{schemas,prompt_builder,deepseek_client}.py`, tests a `tests/`, plans d'implementació a `docs/superpowers/plans/2026-07-23-deepseek-translation-client.md` i `2026-07-23-deepseek-reviewer-terminology-validator.md`. Pendent: 4.5 (chunking) i validació amb crida real (4.6).

---

## FASE 5 — Glossary Engine

- [ ] **5.1** Poblar `glossary/gnss.json`, `surveying.json`, `forestry.json`, `spanish.json`, `global.json` amb els termes exemple del brief (secció 8) com a punt de partida, ampliats amb terminologia real de precision-gnss.com (extreure'ls de la FASE 0).
- [ ] **5.2** `app/translation/glossary.py`: `get_relevant_terms(text)` (matching per keyword/lematització simple) i `validate_translation(text)`.
- [ ] **5.3** Integrar el glossari filtrat dins el `prompt_builder.py` (FASE 4.2) — només el subconjunt rellevant, no el glossari sencer.
- [ ] **5.4** Test: verificar que "base station" sempre es tradueix "estación base" i que "rover" i "fix" respecten les regles `mandatory`/`notes` del brief.

**Sortida de la fase:** glossari amb ≥30-50 termes reals del domini, validat contra 10 frases de prova.

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
