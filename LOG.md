# Log del projecte — GNSS AI Translation Engine

> Registre cronològic de sessions de treball. Cada entrada nova s'afegeix **a sobre** (ordre invers, més recent primer). Format: data, qui/què, resum breu, resultat, següent pas.

---

## 2026-07-24 — FASE 3.5: tots els camps pendents de posts/pages, tancats

**Fet per:** Claude (Claude Code), a petició de l'usuari ("fes el que puguis que no depengui de WPML").

**Fets:**

1. Skill `writing-plans`/`executing-plans` → pla a `docs/superpowers/plans/2026-07-24-posts-pages-field-expansion.md` (5 tasques, TDD).
2. `excerpt.rendered` afegit com a bloc traduïble a `content_extractor.py`.
3. `seo_extractor.py` ampliat amb `og_title`/`og_description` — automàticament disponible també per a WooCommerce, ja que comparteix el mateix mòdul.
4. `extract_page_content()` ampliada amb dos paràmetres **opcionals**, `featured_media` i `categories`/`tags`, que reben dades ja obtingudes pel qui crida (l'extracció es manté pura, sense fer cap crida HTTP ella mateixa) — coherent amb el disseny de la resta d'`app/extraction/`.
5. **Validació contra dades reals de l'staging** (no només tests sintètics): la pàgina "Precision Agriculture" va passar de 164 a 171 blocs (excerpt + og_title + og_description + 4 categories del lloc); el post "RTK GNSS for Robotics", provat amb un flux realista (resoldre només els IDs de categoria assignats al post, no totes les categories del lloc), va extreure correctament la categoria "News".
6. Suite completa: **164 tests, tots passant** (154 anteriors + 10 nous).
7. `MAPEIG-CAMPS.md` i `PLA-ACCIO.md` actualitzats: **FASE 3 sencera (incloent-hi WooCommerce) ja completa.**

**Resultat:** amb això es tanca tot el que es pot fer sense WPML instal·lat. El motor pot traduir, revisar, validar terminologia, detectar canvis, fer QA i extreure absolutament tot el contingut traduïble (posts, pages i productes WooCommerce) de qualsevol WordPress. L'únic que falta és la connexió final amb WordPress via WPML (FASES 1, 2.4, 8, 9).

**Següent pas:** esperar que s'instal·li WPML a l'staging, o (si l'usuari ho vol) escriure l'esquelet PHP del `gnss-bridge` sense poder-lo provar encara.

---

## 2026-07-24 — Implementació del motor d'extracció de productes WooCommerce

**Fet per:** Claude (Claude Code), a petició de l'usuari ("s'ha d'implementar per a altres WordPress amb WooCommerce").

**Fets:**

1. Actualitzat `MEMORIA.md`: canvi d'abast explícit — el suport a WooCommerce ja no és "possible reutilització futura sense construir", sinó una **capacitat genèrica implementada ara**, pensada per a qualsevol WordPress+WooCommerce (no `precision-gnss.com`, que confirmadament no en té).
2. Skill `writing-plans`/`executing-plans` → pla a `docs/superpowers/plans/2026-07-24-woocommerce-extraction.md` (4 tasques, TDD).
3. `app/extraction/taxonomy_extractor.py` (`extract_taxonomy_terms()`): extractor **genèric** de termes de taxonomia (categories/etiquetes), reutilitzable tant per productes com per posts/pages en el futur (FASE 3.5).
4. **Refactor DRY**: la lògica de blocs Yoast, fins ara duplicada dins `content_extractor.py`, s'ha extret a `app/extraction/seo_extractor.py` (`extract_yoast_blocks()`) — provat que el refactor no trenca cap dels 5 tests existents de `content_extractor.py` abans de continuar.
5. `app/extraction/woocommerce_extractor.py` (`extract_product_content()`): nom, descripció llarga/curta (reutilitzant `extract_blocks()`, ja que les descripcions de WooCommerce són HTML WYSIWYG igual que el cos d'un post), nota de compra, atributs/opcions, alt d'imatges de galeria, categories/etiquetes, SEO. **Mai extreu** SKU/preus/estoc/pes/dimensions (provat amb test dedicat).
6. Suite completa: **154 tests, tots passant** (136 anteriors + 18 nous).
7. Actualitzats `MAPEIG-CAMPS.md` (secció 6 passa d'"a fer" a "implementat, pendent validació real") i `PLA-ACCIO.md` (nova tasca 3.6).

**Resultat:** el motor ja pot extreure contingut traduïble de productes WooCommerce de qualsevol lloc que en tingui, tot i que **encara no s'ha pogut validar contra un lloc real** (cap dins l'abast actual) — es prova amb dades sintètiques fidels a l'esquema oficial de l'API.

**Següent pas:** aplicar el mateix patró (`extract_taxonomy_terms()`, camps pendents) a posts/pages (FASE 3.5), o esperar un lloc WooCommerce real per validar-ho empíricament.

---

## 2026-07-24 — Ampliació del mapeig de camps WooCommerce (tabs, atributs, variants)

**Fet per:** Claude (Claude Code), a petició de l'usuari ("has valorat també tot el que representen els camps de productes: descripció, tabs, contingut, etc.?").

**Fets:** la secció 6 de `MAPEIG-CAMPS.md` només llistava 3-4 camps de nivell superior. Ampliada amb: els tabs estàndard de la fitxa de producte (Description/Additional Information — auto-generat/Reviews — recomanat fora d'abast per ser contingut d'usuari/tabs personalitzats de plugins — cal inventariar-los al lloc real), atributs i variants de producte, categories/etiquetes/marca, galeria d'imatges, paritat amb Yoast SEO, i la llista de camps que mai s'han de traduir. **Deixat explícit que aquesta secció no s'ha pogut validar empíricament** (a diferència de les seccions 1-5) perquè no hi ha cap WooCommerce real dins l'abast — es basa en l'esquema oficial i estable de `wc/v3/products`.

**Resultat:** mapeig de productes ara complet a nivell de disseny, pendent de validació real si el projecte s'amplia mai a un lloc amb botiga.

**Següent pas:** esperar confirmació de l'usuari per implementar les accions pendents de posts/pages ja identificades (`excerpt`, `og_title`/`og_description`, imatge destacada, categories) — el treball de WooCommerce queda com a referència, no com a tasca activa.

---

## 2026-07-24 — Auditoria completa de camps WordPress/Yoast/Media/Taxonomies

**Fet per:** Claude (Claude Code), a petició de l'usuari ("el sistema ha de poder mapejar tots els camps de WordPress... ja els tens tots detectats?").

**Fets:**

1. Resposta honesta: **no**, fins ara només gestionàvem títol, cos i 2 camps de Yoast. Es fa una auditoria real contra l'staging per tancar el buit.
2. Inspecció completa via REST API d'una pàgina (Precision Agriculture) i un post: tots els camps de primer nivell, els 9 camps de `yoast_head_json` (no només title/description — falten `og_title`/`og_description`), l'`excerpt` (existeix i no es capturava), `featured_media` (necessita crida separada a l'endpoint de media), taxonomies de posts (`category`/`post_tag`, 4 categories reals), i camps de la mediateca (`alt_text`, `caption`, `title`, `description`).
3. Confirmat que `schema` (JSON-LD de Yoast) és **derivat** dinàmicament del title/description — no cal gestionar-lo per separat.
4. Confirmat de nou que **no hi ha WooCommerce/productes** en aquest lloc; documentats els camps que caldria mapejar (`wp-json/wc/v3/products`) només com a referència per a una futura ampliació (ArduSimple), sense construir-ho ara.
5. Creat `MAPEIG-CAMPS.md` amb la taula completa camp-per-camp, estat actual, i una llista d'accions pendents priolitzades per a la propera iteració de FASE 3 (afegir `excerpt`, `og_title`/`og_description`, alt/caption d'imatge destacada, noms/descripcions de categories).

**Resultat:** buit de cobertura identificat i documentat amb precisió; cap codi nou encara (l'usuari no ho ha demanat explícitament, només el mapeig).

**Següent pas:** esperar confirmació de l'usuari per implementar les accions pendents de `MAPEIG-CAMPS.md` (no depenen de WPML, es poden fer ara).

---

## 2026-07-24 — README.md (presentació del sistema a GitHub, en anglès)

**Fet per:** Claude (Claude Code), a petició de l'usuari.

**Fets:** creat `README.md` (anglès) amb filosofia del projecte, diagrames Mermaid (arquitectura + pipeline de traducció), taula de decisions de disseny amb el "per què", anàlisi de costos real (reutilitzant les dades empíriques ja calculades), taula de funcionalitats, estat del projecte per fase, i instruccions d'instal·lació/ús. Confirmat que la convenció de missatges de commit en anglès ja s'havia seguit consistentment durant tota la sessió (verificat contra els últims 20 commits) — sense canvis necessaris, només es manté endavant.

**Resultat:** el repositori ja té una pàgina de presentació completa a GitHub.

**Següent pas:** el mateix que abans — esquelet del `gnss-bridge` o esperar WPML.

---

## 2026-07-24 — FASE 7: QA Engine

**Fet per:** Claude (Claude Code), continuant "Fase 6 i 7" en la mateixa sessió.

**Fets:**

1. Skill `writing-plans`/`executing-plans` → pla a `docs/superpowers/plans/2026-07-24-qa-engine.md` (5 tasques, TDD).
2. `app/qa/numerical_checker.py`: `check_numbers()`, provat literalment amb l'exemple del propi brief (secció 12.1): "1 cm accuracy" → "1 cm de precisión" PASS; → "2 cm de precisión" FAIL. Normalitza el separador decimal (`.`/`,`) perquè EN/ES no donin fals positiu.
3. `app/qa/terminology_checker.py`: `check_protected_terms()` — termes protegits (GNSS, RTK, codis de producte) han de sobreviure literalment; sensible a majúscules expressament (un codi de producte en minúscules és un error).
4. `app/qa/url_validator.py`: `check_urls()` — compara el conjunt d'URLs origen/traducció.
5. `app/qa/scoring.py`: `score_translation()` combina els 3 checkers + el resultat ja existent de `DeepSeekClient.review()` (FASE 4.4, no duplicat) en una puntuació 0-100 amb els llindars exactes del brief secció 13. **Simplificació conscient documentada:** en lloc de les "5 dimensions" independents del brief (que requeririen dades reals per calibrar-les sense inventar-se-les), es combinen els 4 senyals que es poden mesurar mecànicament ara mateix.
6. Suite completa: **136 tests, tots passant** (117 anteriors + 19 nous).
7. `PLA-ACCIO.md` FASE 7 actualitzada (7.1/7.2/7.3/7.5/7.6/7.7 fets; 7.4 ajornat perquè no hi ha HTML real a validar encara).

**Resultat:** amb FASES 4-7 fetes, el motor ja pot traduir, revisar, detectar canvis i puntuar automàticament una traducció — només falta l'orquestració completa (FASE 8) i la integració amb WordPress/WPML per publicar-ho de veritat, ambdues bloquejades fins tenir WPML instal·lat.

**Següent pas:** amb FASES 4, 5, 6 i 7 fetes pel costat no-WPML, l'únic que queda raonablement per fer sense staging és el disseny/esquelet del mu-plugin `gnss-bridge` (FASE 1) sense desplegar-lo. La resta (FASE 2.4, 3.3, 8, 9) depenen totes de tenir WPML instal·lat a l'staging.

---

## 2026-07-24 — FASE 6: Translation Memory i detecció de canvis

**Fet per:** Claude (Claude Code), a petició de l'usuari ("Fase 6 i 7").

**Fets:**

1. Skill `writing-plans`/`executing-plans` → pla a `docs/superpowers/plans/2026-07-24-translation-memory.md` (4 tasques, TDD).
2. `app/storage/database.py`: esquema SQLite exacte del brief secció 18 (`source_content`, `content_blocks`, `translations`, `terminology`, `qa_results`), amb `sqlite3` de la llibreria estàndard (sense dependència nova).
3. `app/storage/models.py`: funcions de repositori (`upsert_source_content`, `save_content_block`, `get_content_block_hash`) amb SQL parametritzat i `ON CONFLICT ... DO UPDATE` per als upserts.
4. `app/synchronization/change_detector.py`: `hash_text()` (SHA-256) + `detect_changed_blocks()` — funció **pura** (read-only) que compara el hash actual de cada `ContentBlock` (reutilitzat directament de FASE 3) amb el guardat, sense mai escriure.
5. Provat exactament l'escenari que demana el brief secció 5: modificar un sol paràgraf d'una pàgina de dos blocs → només aquest es marca `"changed"`, l'altre `"unchanged"`.
6. Suite completa: **117 tests, tots passant** (103 anteriors + 14 nous).
7. `PLA-ACCIO.md` FASE 6 actualitzada (6.1/6.2/6.4 fets; 6.3 bloquejat per manca de `gnss-bridge`/WPML).

**Resultat:** el motor ja pot decidir, per bloc, si cal retraduir-lo o no — la peça que falta per no re-traduir mai una pàgina sencera per un canvi petit.

**Següent pas:** FASE 7 (QA Engine), a continuació en la mateixa sessió.

---

## 2026-07-24 — FASE 3: Content Extraction Engine, validat amb contingut real

**Fet per:** Claude (Claude Code), a petició de l'usuari ("Pots fer el punt 2?" — FASE 3).

**Fets:**

1. Aclariment puntual: l'usuari va preguntar per "articles de WooCommerce" — confusió amb `ardusimple.com` (que sí té un `product-sitemap.xml`, no `precision-gnss.com`). Confirmat que és una consideració de futur, sense canvi d'abast ara.
2. Skill `writing-plans`/`executing-plans` → pla a `docs/superpowers/plans/2026-07-24-content-extraction.md` (6 tasques, TDD).
3. `app/extraction/protected_content.py` (`is_protected_content()`): detecta URLs, emails i shortcodes solts.
4. `app/extraction/schemas.py` (`ContentBlock`) i `app/extraction/html_parser.py` (`extract_blocks()`): extractor que camina l'HTML renderitzat (no `_elementor_data` cru, que segueix sense exposar-se) i construeix el `context` a partir de la jerarquia d'encapçalaments.
5. Bug real trobat i corregit durant el TDD (no contra staging, sinó en la pròpia implementació): `_block_type_for_tag("p")` retornava `"p"` en lloc de `"paragraph"` — detectat pels propis tests abans de cap commit.
6. `app/extraction/content_extractor.py` (`extract_page_content()`): orquestra títol + SEO Yoast (quan hi és) + cos.
7. **Validat contra 3 continguts reals de l'staging**: "Precision Agriculture" (164 blocs), "Contact us" (5 blocs), post "RTK GNSS for Robotics" (74 blocs) — cap fals positiu de contingut protegit.
8. Suite completa: **103 tests, tots passant** (74 anteriors + 29 nous... nota: 12+2+10+5=29 tests d'extracció).
9. `PLA-ACCIO.md` FASE 3 actualitzada (3.1/3.2/3.4 fets; 3.3 ajornat perquè `_elementor_data` no és accessible).

**Resultat:** ja es pot convertir contingut real de WordPress en la llista ordenada de blocs semàntics que el brief demana, a punt per alimentar `DeepSeekClient.translate()` un cop es desbloquegi l'escriptura (WPML).

**Següent pas:** amb FASES 2 i 3 fetes pel costat de lectura, les opcions raonables són: (a) FASE 6 (Translation Memory / SQLite) o FASE 7 (QA Engine — numèric/unitats/URLs), totes dues independents de WPML, o (b) crear l'Application Password des del wp-admin per preparar l'escriptura quan WPML estigui instal·lat.

---

## 2026-07-23 — FASE 2: WordPress Connector (lectura), provat contra l'staging real

**Fet per:** Claude (Claude Code), continuant l'auditoria de FASE 0 cap a FASE 2 mentre WPML no està instal·lat.

**Fets:**

1. Skill `writing-plans`/`executing-plans` → pla a `docs/superpowers/plans/2026-07-23-wordpress-connector.md` (4 tasques, TDD).
2. `app/wordpress/client.py`: `WordPressClient` amb doble autenticació (Basic Auth de l'staging + Application Password de WP) i retry en 429/503.
3. `app/wordpress/content.py`: `get_post()`, `get_page()`, `get_pages()`, `get_post_meta()`, `get_page_meta()`, `get_elementor_data()`.
4. **Bug real trobat en provar contra l'staging** (`scripts/inspect_staging_page.py`): `get_post_meta` només consultava l'endpoint de posts; en cridar-lo amb l'ID d'una pàgina (Precision Agriculture, 4309) va donar 404. Corregit amb TDD: `get_elementor_data` ara és una funció pura sobre un `dict` de meta ja obtingut, i s'ha afegit `get_page_meta()` en paral·lel a `get_post_meta()`.
5. **Confirmat empíricament, no només per documentació:** `_elementor_data` no s'exposa via REST per a cap contingut de l'staging (ni posts ni pages) — validant una altra vegada la troballa de `BIBLIOGRAFIA.md` §6.
6. Suite completa: **74 tests, tots passant** (60 anteriors + 14 nous).
7. `PLA-ACCIO.md` FASE 2 actualitzada (2.1-2.3 i 2.5 parcial fets; 2.4 bloquejat per manca de WPML).

**Resultat:** connector de lectura de WordPress funcional i validat contra dades reals de l'staging (no mockejades).

**Següent pas:** sense WPML ni Application Password d'escriptura, les properes opcions raonables són: (a) FASE 3 (extracció de blocs semàntics d'Elementor/contingut, ja tenim contingut real per provar-hi), (b) esperar que s'instal·li WPML per desbloquejar FASE 1/2.4/8, o (c) crear una Application Password des del wp-admin ja accessible per preparar l'escriptura.

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
