# Log del projecte — GNSS AI Translation Engine

> Registre cronològic de sessions de treball. Cada entrada nova s'afegeix **a sobre** (ordre invers, més recent primer). Format: data, qui/què, resum breu, resultat, següent pas.

---

## 2026-07-23 — FASE 0: primera auditoria real de l'staging (WPML no instal·lat)

**Fet per:** Claude (Claude Code), amb accés d'administrador de WordPress proporcionat per l'usuari.

**Fets:**

1. Login real a `staging.precision-gnss.com/login_secure/` via automatització de navegador (Playwright), confirmat (Dashboard carregat correctament).
2. Auditoria de plugins (`wp-admin/plugins.php` + REST API `wp-json` namespaces): 22 plugins, 3 mu-plugins.
3. 🛑 **Troballa crítica: WPML no està instal·lat enlloc** (ni actiu, ni inactiu, ni mu-plugin, ni namespace REST `wpml/*`). Contradiu el supòsit de `MEMORIA.md`. Comunicat a l'usuari immediatament amb `AskUserQuestion`.
4. Decisió de l'usuari: continuar amb el que no depengui de WPML mentre no s'instal·la.
5. Inventari de contingut via REST API: 24 pages + 17 posts + 390 media, sense custom post types propis. Confirmat empíricament (no només per documentació) que els camps Yoast i `_elementor_data` no estan exposats per defecte a la REST API — validant la troballa de `BIBLIOGRAFIA.md` §6.
6. Creat `AUDITORIA-INICIAL.md` amb tots els resultats. `PLA-ACCIO.md` FASE 0 actualitzada (0.0, 0.1, 0.2, 0.3, 0.5, 0.6 fets; 0.4 bloquejat per manca de WPML i credencials MySQL).

**Resultat:** FASE 0 gairebé completa. Desviació importat respecte al pla original: WPML no hi és, cosa que bloqueja FASE 1 (`gnss-bridge`) i FASE 8 (orquestració WPML) fins que s'instal·li.

**Següent pas:** avançar en FASE 2 (WordPress Connector) per a les parts no-WPML (`get_post`, `get_pages`, `get_post_meta`) contra l'staging real, mentre s'espera la instal·lació de WPML.

---

## 2026-07-23 — Accés a l'staging rebut, seguiment reactivat

**Fet per:** Claude (Claude Code), a petició de l'usuari ("ja podem continuar amb el projecte, torna a activar seguiment i commits").

**Fets:**

1. L'usuari va proporcionar credencials de Basic Auth per a `staging.precision-gnss.com`. Aclarit que no eren credencials SSH/MySQL/wp-admin sinó el gate de protecció HTTP davant de tot el lloc.
2. Accés verificat amb una petició `GET` (HTTP 200, WordPress + Yoast SEO Premium detectat). Cap altra acció feta encara sobre l'staging.
3. Credencials guardades **només** en `.env` local (confirmat gitignored amb `git check-ignore`). **Cap credencial s'ha escrit ni s'escriurà mai a cap fitxer versionat.**
4. `.env.example` ampliat amb l'estructura necessària (`STAGING_URL`, `STAGING_BASIC_AUTH_USER/PASSWORD`, `WP_USERNAME`, `WP_APPLICATION_PASSWORD`) sense valors reals.
5. `MEMORIA.md` actualitzada amb la decisió/fet i un recordatori de seguretat permanent sobre credencials.
6. Pendent: l'usuari ha indicat que tot seguit donarà accés d'administrador de WordPress. Un cop rebut, es pot començar la FASE 0 real (auditoria) del `PLA-ACCIO.md`.

**Resultat:** FASE 0 desbloquejada (accés bàsic confirmat). Seguiment de documentació i commits a git reactivats a partir d'ara (havien quedat en pausa explícita durant la tasca puntual d'ardusimple.com).

**Següent pas:** rebre accés wp-admin, després començar `PLA-ACCIO.md` FASE 0 (versió WPML/Elementor, `DESCRIBE` de taules `icl_*`, inventari de contingut).

---

## 2026-07-23 — Afegit cost en euros als dos PDFs

**Fet per:** Claude (Claude Code), a petició de l'usuari.

**Fets:** taxa de canvi consultada ($1 = €0.876, 23/07/2026). Afegides xifres en EUR entre parèntesis al costat de cada xifra en USD (targetes, taules de preus DeepSeek, taula de pàgines reals, exemple treballat) als dos informes, sense substituir el dòlar (moneda de facturació real de DeepSeek). Ajustat l'espaiat de la pàgina de costos de l'informe llarg perquè seguís cabent en una sola pàgina A4 després d'afegir el text extra.

**Resultat:** ambdós PDFs actualitzats (7 i 1 pàgines) i pujats a GitHub.

**Nota:** la tasca prèvia de la mateixa sessió (recompte de caràcters d'ardusimple.com) es va fer explícitament **sense guardar ni commitejar res**, tal com va demanar l'usuari — no apareix als fitxers del projecte.

---

## 2026-07-23 — Redisseny dels PDFs (nivell "Apple") + exemple de cost treballat

**Fet per:** Claude (Claude Code), a petició de l'usuari ("la maquetació és horrible, vull un nivell Apple").

**Fets:**

1. Motor de renderització canviat: `xhtml2pdf` (CSS molt limitat, resultat "horrible" segons l'usuari) → Chromium real via Playwright MCP (`page.pdf()`), amb suport CSS complet (flexbox, gradients, ombres, border-radius).
2. Redisseny complet dels dos documents: paleta minimal (blanc, gris clar, un sol accent blau), molt espai en blanc, targetes d'estadístiques, diagrames de flux amb caixes arrodonides i fletxes, taules netes sense capçaleres pesades.
3. Afegida secció d'introducció en **llenguatge planer/genèric** (sense argot tècnic) explicant què fa l'eina, tal com va demanar l'usuari.
4. Verificació visual iterativa: captures de pantalla de cada pàgina abans d'exportar el PDF final (via `browser_run_code_unsafe` + `page.screenshot()`), per confirmar el disseny abans de donar-lo per bo.
5. L'usuari va demanar afegir un exemple de cost concret (pàgina "Precision Agriculture", 14.240 caràcters segons el seu càlcul). **Discrepància detectada i comunicada a l'usuari:** el recompte real de la pàgina (mesurat amb el mateix mètode que la resta del document) és 24.706 caràcters, no 14.240. S'ha fet servir la xifra verificada per mantenir el document internament consistent amb la taula ja publicada.
6. `requirements.txt`: eliminat `xhtml2pdf` (ja no s'usa), mantingut `pypdf` (verificació de pàgines).

**Resultat:** dos PDFs professionals, en anglès, guardats a l'arrel: `GNSS-AI-Translation-Engine-Executive-Summary.pdf` (7 pàgines) i `-Short.pdf` (1 pàgina). Fonts HTML actualitzades a `docs/reports/`.

**Següent pas:** el mateix que abans — esperar accés a l'staging, o avançar en FASE 6/7 si es prefereix.

---

## 2026-07-23 — Resum executiu PDF amb anàlisi de costos empírica

**Fet per:** Claude (Claude Code), a petició de l'usuari.

**Objectiu de la sessió:** produir un document professional (PDF, anglès) per a l'usuari amb resum executiu del projecte: què fa l'eina, tecnologies, lògica, funcionalitats implementades, i una anàlisi de costos de DeepSeek amb xifres reals.

**Fets:**

1. Prova empírica a petició de l'usuari: `browser-harness` no funciona en aquest entorn Windows (error `AF_UNIX` no suportat) — reportat com a limitació d'entorn, no solucionat (fora d'abast). Fallback a l'skill `firecrawl-scrape`, que sí ha funcionat.
2. Scraping de 4 pàgines reals de precision-gnss.com (homepage, `/rtk-application/archaeology/` — la mateixa que usa el brief original com a exemple —, `/rtk-application/precision-agriculture/`, i un article de notícies) guardades a `.firecrawl/` (afegit a `.gitignore`, no versionat).
3. `scripts/estimate_page_cost.py`: script d'anàlisi que fa servir el `chunk_text()` real i les mides reals dels system prompts (`app/translation/prompt_builder.py`) per calcular costos de DeepSeek amb dades reals, no inventades. Preus de DeepSeek verificats a `api-docs.deepseek.com/quick_start/pricing/` (v4-pro: $0.435/$0.87 per 1M tokens input/output; v4-flash: $0.14/$0.28).
4. **Resultat empíric clau:** cost molt consistent d'entre $0.00084-$0.00086 per 1.000 caràcters amb el pipeline complet (Translator+Reviewer+Validator) sobre `deepseek-v4-pro`, en les 4 pàgines reals provades. Una pàgina típica (~2.400 paraules) costa ~$0.006 (només traducció) a ~$0.013 (amb QA complet).
5. Document `GNSS-AI-Translation-Engine-Executive-Summary.pdf` (10 pàgines, anglès) generat amb `xhtml2pdf` (WeasyPrint no és viable en aquest Windows sense GTK) i guardat a l'arrel del projecte. Font HTML conservada a `docs/reports/executive-summary-2026-07-23.html` per poder-lo regenerar/editar.
6. Verificat que el PDF commitejat és idèntic byte a byte al fitxer local (l'avís de conversió CRLF de git no l'ha corromput); afegit `.gitattributes` per marcar els `*.pdf` com a binaris de cara al futur.

**Resultat:** document professional lliurat, amb dades de cost reals i verificables (reproduïbles amb `scripts/estimate_page_cost.py`), no estimacions inventades.

**Següent pas:** el mateix que abans — esperar accés a l'staging per continuar amb FASES 0-3/6-9, o avançar en peces independents (QA Engine FASE 7, Translation Memory FASE 6) si es prefereix.

---

## 2026-07-23 — Chunking de contingut llarg (FASE 4.5) → FASE 4 completa

**Fet per:** Claude (Claude Code), continuant a petició de l'usuari ("Continua per on tingui més lògica").

**Objectiu de la sessió:** completar l'última peça pendent de FASE 4 — dividir contingut llarg en trossos sense trencar frases/números a la meitat, i traduir-los preservant context i glossari.

**Fets:**

1. Skill `writing-plans` → pla a `docs/superpowers/plans/2026-07-23-chunking.md` (3 tasques, TDD).
2. Skill `executing-plans` → execució inline:
   - `app/translation/chunking.py`: `chunk_text()` (divisió per paràgrafs, amb fallback a frases per a un paràgraf massa llarg) i `translate_long_text()` (divideix, tradueix cada tros amb `DeepSeekClient.translate()` compartint `context`/glossari, torna a ajuntar).
   - Suite completa: **60 tests, tots passant** (51 anteriors + 9 nous).
3. **Incident:** durant el commit de la Task 2, es va descobrir un commit (`520fc05`) fet amb el mateix contingut però que no havia creat jo — l'usuari ha confirmat que va ser ell mateix des d'una altra eina/sessió sobre el mateix repositori, i que no tornarà a passar. Cap acció addicional necessària; working tree i tests verificats correctes després.
4. `PLA-ACCIO.md` FASE 4 marcada com a **completa** (4.1-4.6).

**Resultat:** FASE 4 (Translation Engine) tancada del tot. El motor de traducció (Translator + Reviewer + Terminology Validator + Glossary + Chunking) és funcional, provat i validat amb l'API real.

**Següent pas:** sense accés a l'staging, l'única feina de codi independent que queda raonablement és preparar l'esquelet PHP del mu-plugin `gnss-bridge` (FASE 1) sense desplegar-lo. La resta (FASES 2-3, 6-9) depenen de tenir contingut/estructura real de WordPress.

---

## 2026-07-23 — Primera crida real a DeepSeek (validació manual)

**Fet per:** Claude (Claude Code), amb una `DEEPSEEK_API_KEY` real proporcionada per l'usuari només per aquesta sessió (no s'ha guardat enlloc: no a `.env`, no a memòria, no a cap commit — verificat amb `git log --all -p | grep` sobre tot l'historial).

**Fets:**

1. Execució de `scripts/translate_sample.py` amb la clau real → traducció correcta amb `confidence: 0.98` i terminologia ben aplicada.
2. Detectat un bug de visualització: caràcters accentuats es veien malament a la consola (`m�dulo` en lloc de `módulo`). Verificat que era només codificació de la consola de Windows (cp1252), no un problema de les dades (el fitxer UTF-8 sortia correcte). **Fix aplicat:** `sys.stdout.reconfigure(encoding="utf-8")` a `scripts/translate_sample.py`.
3. Provades 3 frases tècniques addicionals (rover/fix, baseline/accuracy, correction stream/float solution) — totes amb `confidence` ≥0.95 i terminologia del glossari correcta.
4. **Troballa significativa:** a la frase "The rover achieves a fix **within** 5 seconds", el Translator ho va traduir com "en **menos de** 5 segundos" (canvi subtil de ≤5s a <5s). El `DeepSeekClient.review()` (FASE 4.4) **ho ha detectat correctament** (`passed: False`, `issue: information altered`), validant que el disseny de 3 crides separades (Translator + Reviewer + Terminology Validator) funciona tal com estava previst — el Reviewer atrapa matisos que el Translator sol passa per alt.
5. **Descoberta no relacionada:** el repositori local ja estava connectat a un remot de GitHub (`marcelepsworks-arch/AI-WP-translation`, afegit fora d'aquesta sessió — probablement via VS Code) i **tots els commits ja hi estaven sincronitzats**. Verificat que la clau API no apareix en cap commit de l'historial.

**Resultat:** primera validació end-to-end amb l'API real de DeepSeek, amb resultats consistents i el mecanisme de revisió funcionant com a xarxa de seguretat real (no només teòrica).

**Següent pas:** decidir amb l'usuari si el repositori a GitHub ha de ser públic/privat i si l'auto-sync és el comportament desitjat; després continuar amb FASE 4.5 (chunking) o preparar l'esquelet del mu-plugin `gnss-bridge` (FASE 1) sense desplegar-lo encara.

---

## 2026-07-23 — Glossary Engine (FASE 5)

**Fet per:** Claude (Claude Code), continuant a petició de l'usuari ("Continua, encara no tinc accés a l'staging").

**Objectiu de la sessió:** avançar en una peça independent de l'staging de WordPress — el Glossary Engine (FASE 5), que ja s'usava manualment (llistes de `GlossaryTerm` a mà) des de les sessions anteriors.

**Fets:**

1. Skill `writing-plans` → pla nou a `docs/superpowers/plans/2026-07-23-glossary-engine.md` (5 tasques, TDD).
2. Skill `executing-plans` → execució inline:
   - `glossary/gnss.json` (6 termes) i `glossary/surveying.json` (4 termes) — glossaris **llavor**, amb els exemples del brief + terminologia GNSS/RTK/surveying ben establerta. **Marcats explícitament com a punt de partida**, no com a glossari complet — calen termes reals de precision-gnss.com (bloquejat per FASE 0/staging).
   - `app/translation/glossary.py`: `GlossaryEntry` (model), `load_glossary_files()`, `get_relevant_terms()` (filtratge per paraula completa + idioma, retorna `GlossaryTerm` ja compatibles amb `DeepSeekClient`), `validate_translation()` (comprovació local determinista de termes obligatoris, sense cost d'API, complementària a `DeepSeekClient.validate_terminology()`).
   - Suite completa: **51 tests, tots passant** (39 anteriors + 12 nous).
3. `PLA-ACCIO.md` FASE 5 marcada com a feta (amb el matís que el glossari és una llavor petita, no els 30-50 termes previstos originalment — això depèn de contingut real).

**Resultat:** el Glossary Engine ja és funcional i es pot cridar des de codi (`load_glossary_files` + `get_relevant_terms` + `validate_translation`), encara no integrat en un pipeline end-to-end (això és FASE 8).

**Següent pas:** queden com a peces independents de l'staging: FASE 4.5 (chunking de contingut llarg) o una prova real amb `DEEPSEEK_API_KEY`. Quan hi hagi accés a l'staging, cal revisitar FASE 5.1 per ampliar el glossari amb terminologia real abans de considerar-lo complet.

---

## 2026-07-23 — Reviewer tècnic + Terminology Validator (FASE 4.4)

**Fet per:** Claude (Claude Code), continuant a petició de l'usuari ("Continua").

**Objectiu de la sessió:** completar la FASE 4.4 — les dues crides DeepSeek que faltaven (Technical Reviewer i Terminology Validator), independents de la crida Translator ja feta a la sessió anterior.

**Fets:**

1. Skill `writing-plans` → pla nou a `docs/superpowers/plans/2026-07-23-deepseek-reviewer-terminology-validator.md` (4 tasques, TDD).
2. Skill `executing-plans` → execució inline:
   - `app/translation/schemas.py`: `ReviewResult`, `TerminologyViolation`, `TerminologyValidationResult` (13 tests de schema, tots passant).
   - `app/translation/prompt_builder.py`: `build_reviewer_system_prompt()` (compara original vs. traducció, detecta informació afegida/eliminada/alterada, canvis de certesa/condicions/terminologia) i `build_terminology_validator_system_prompt()` (audita compliment del glossari obligatori) (12 tests de prompt, tots passant).
   - `app/translation/deepseek_client.py`: refactoritzat amb un mètode privat `_call()` compartit; nous mètodes `review()` i `validate_terminology()`; nou paràmetre `qa_model` al constructor (separat de `model`, tal com preveu `.env`: `DEFAULT_MODEL` per traduir, `QA_MODEL` per revisar/validar) (10 tests de client, tots passant).
   - Suite completa: **39 tests, tots passant** (21 anteriors + 18 nous).
3. `PLA-ACCIO.md` FASE 4.4 marcada com a feta; `PLA-ACCIO.md` FASE 4.1/4.3 actualitzades per reflectir el `qa_model`.

**Resultat:** les 3 crides DeepSeek del brief (secció 9: Translator / Technical Reviewer / Terminology Validator) ja existeixen com a mètodes independents de `DeepSeekClient`, cadascuna amb el seu propi system prompt i schema de resposta validat. Encara no hi ha cap orquestració que les encadeni (això és FASE 8, pendent de WPML).

**Següent pas:** igual que abans — decidir entre (a) prova real amb `DEEPSEEK_API_KEY`, (b) Glossary Engine (FASE 5) o chunking (FASE 4.5), o (c) accés a l'staging de precision-gnss.com per FASE 0/1.

---

## 2026-07-23 — Primer codi: client de traducció DeepSeek (FASE 4, parcial)

**Fet per:** Claude (Claude Code), a petició explícita de l'usuari de començar a programar.

**Objectiu de la sessió:** implementar la primera peça de codi real del projecte — la crida a DeepSeek per traduir contingut tècnic amb precisió — sense dependre encara de credencials de WordPress/WPML (que no tenim).

**Decisió d'abast:** en lloc d'intentar les 10 fases del `ROADMAP.md` de cop, es va acotar aquesta primera tanda al nucli de la FASE 4 (Translation Engine): `settings`, `schemas`, `prompt_builder`, `deepseek_client`. Queden fora d'aquesta tanda (i pendents per a properes sessions): la crida "Reviewer"/"Terminology Validator" (FASE 4.4), el Glossary Engine real (FASE 5), i tot el que depèn de WordPress/WPML/Elementor (FASES 1-3, 6-8) perquè encara no hi ha accés a l'staging.

**Fets:**

1. Skill `writing-plans` → pla escrit a `docs/superpowers/plans/2026-07-23-deepseek-translation-client.md` (5 tasques, TDD pas a pas).
2. Skill `executing-plans` → execució inline del pla:
   - Inicialitzat el repositori git (`git init`), primer commit amb tota la documentació prèvia.
   - Entorn virtual Python (`.venv`) + `requirements.txt` (`openai`, `pydantic`, `python-dotenv`, `pytest`, `pytest-mock`).
   - `app/config/settings.py` — càrrega de configuració des de variables d'entorn, amb tests (4 passed).
   - `app/translation/schemas.py` — models Pydantic pel contracte JSON de resposta de DeepSeek (brief secció 11), amb tests (7 passed).
   - `app/translation/prompt_builder.py` — construcció del system prompt amb les regles exactes del brief (secció 10) + injecció opcional de glossari, amb tests (5 passed).
   - `app/translation/deepseek_client.py` — `DeepSeekClient.translate()`, crida a l'API de DeepSeek en mode JSON via SDK compatible OpenAI, amb tests (5 passed, sense trucades reals — tot mockejat).
   - `scripts/translate_sample.py` — script manual per fer una crida real de prova (no s'executa en CI, requereix `DEEPSEEK_API_KEY` real).
   - Suite completa: **21 tests, tots passant.**
3. Cada tasca amb el seu propi commit atòmic (TDD: test fallant → implementació → test passant → commit).

**Resultat:** primer codi funcional del projecte, provat i commitejat. Encara no s'ha fet cap crida real a DeepSeek (calen credencials reals de l'usuari per fer-ho amb `scripts/translate_sample.py`).

**Següent pas:** decidir amb l'usuari si (a) es fa una prova manual real amb una `DEEPSEEK_API_KEY` de veritat, (b) es continua amb la següent peça independent de codi (Glossary Engine, FASE 5, o Reviewer/Terminology Validator, FASE 4.4), o (c) es prioritza aconseguir accés a l'staging de precision-gnss.com per poder començar la FASE 0/1 (WordPress/WPML).

---

## 2026-07-23 — Confirmació d'entorn (staging) i abast (contingut, no tema)

**Fet per:** Claude (Claude Code), a petició de l'usuari.

**Fets:** l'usuari confirma tres punts que afecten el disseny:

1. Es partirà de precision-gnss.com, un WordPress **sense WooCommerce**, amb Elementor.
2. Producció existeix, però **tot el desenvolupament i les proves es faran contra un staging** de la pròpia web, no directament contra producció.
3. Ja es té confirmada la llicència de pagament de WPML (amb suport Elementor), i **la prioritat és traduir el contingut, no el tema**.

**Canvis fets als documents:**
- `MEMORIA.md`: nova entrada de decisió amb context i "com aplicar-ho"; actualitzats els supòsits pendents (staging ja no és una incertesa).
- `ROADMAP.md`: nota de confirmació a la capçalera; FASE 0 actualitzada per treballar sobre staging i prioritzar contingut editorial sobre strings de tema.
- `PLA-ACCIO.md`: noves tasques 0.0 (verificar fidelitat de l'staging) i 0.3 ampliada (confirmar absència de WooCommerce); 1.7 simplificada (desplegament directe a staging, ja confirmat); 0.5 ajustada per marcar strings de tema com a fora d'abast.

**Resultat:** documentació sincronitzada amb els nous fets confirmats. Encara no s'ha escrit codi ni s'ha tocat cap entorn.

**Següent pas:** el mateix que abans — esperar llum verda de l'usuari per començar la FASE 0 real (auditoria) sobre l'staging.

---

## 2026-07-23 — Sessió d'investigació i disseny inicial

**Fet per:** Claude (Claude Code), a petició de l'usuari.

**Objectiu de la sessió:** investigar la millor manera d'implementar el GNSS AI Translation Engine descrit al brief PDF, centrant-se en la connexió amb WordPress/WPML a nivell de base de dades, i deixar-ho tot documentat (bibliografia, roadmap, pla d'acció, memòria) **sense escriure codi**.

**Fets:**
1. Lectura completa del brief PDF (`brief_gnss_translation_engine_precision_gnss.pdf`).
2. Preguntes de clarificació a l'usuari sobre: (a) tipus exacte de llicència WPML → confirmat pla de pagament $99/any per a 2 llocs; (b) nivell d'accés a BD desitjat → combinació de lectura MySQL directa + REST API; (c) abast del lliurament → bibliografia + roadmap + pla d'acció + memòria/logs.
3. Investigació web (10+ cerques + fetches) sobre:
   - Esquema de taules de BD de WPML (`icl_translations`, `icl_translation_status`, `icl_strings`, `icl_string_translations`, `icl_flags`, etc.) i la seva versió actual (4.9.5 estable, 5.0 en Beta).
   - API oficial de hooks PHP de WPML per crear/vincular traduccions programàticament (`wpml_set_element_language_details` i companyia).
   - REST API pròpia de WPML (`wpml/tm/v1`, `wpml/st/v1`) i les seves limitacions (no és un CRUD públic de traduccions).
   - Integració nativa WPML↔Elementor (disponible al pla CMS) i el mecanisme `wpml-config.xml`.
   - WordPress REST API + Application Passwords per autenticació d'scripts externs.
   - Limitacions d'escriptura de camps Yoast via REST API (cal `register_post_meta()`).
   - Estructura JSON de `_elementor_data`.
   - API de DeepSeek (compatibilitat OpenAI SDK, JSON mode, models `deepseek-v4-pro`/`deepseek-v4-flash`, deprecació de noms antics el 2026-07-24).
   - Confirmació que WPML no té paquet WP-CLI oficial propi.
4. Redacció de 4 documents nous al directori del projecte:
   - `BIBLIOGRAFIA.md` — totes les fonts amb resums i cites.
   - `ROADMAP.md` — full de ruta en 10 fases, amb una decisió arquitectònica clau (component pont `gnss-bridge`) no prevista al brief original.
   - `PLA-ACCIO.md` — tasques concretes per fase amb criteris de verificació i taula de riscos.
   - `MEMORIA.md` — context i decisions del projecte.
   - `LOG.md` — aquest fitxer.

**Resultat:** documentació completa i guardada. **Cap codi escrit, tal com es va demanar.**

**Troballa més rellevant de la sessió:** el brief original assumeix que tot es pot fer via WordPress REST API des de Python, però la investigació demostra que crear/vincular traduccions WPML només és suportat oficialment mitjançant hooks PHP executats dins de WordPress. Això obliga a afegir un component nou a l'arquitectura (mu-plugin pont, anomenat provisionalment `gnss-bridge`) no previst al brief. Detallat a `MEMORIA.md` i `ROADMAP.md` §0.

**Següent pas:** l'usuari ha de revisar `BIBLIOGRAFIA.md`, `ROADMAP.md`, `PLA-ACCIO.md` i `MEMORIA.md`, i donar llum verda explícita per començar la FASE 0 (auditoria real contra precision-gnss.com) del `PLA-ACCIO.md`.

---

<!--
Plantilla per a noves entrades — copiar el bloc de sota en afegir una nova sessió:

## YYYY-MM-DD — Títol breu de la sessió

**Fet per:**
**Objectiu de la sessió:**
**Fets:**
1.
**Resultat:**
**Següent pas:**
-->
