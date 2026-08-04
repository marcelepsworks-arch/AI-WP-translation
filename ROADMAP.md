# Roadmap — GNSS AI Translation Engine

> Full de ruta de desenvolupament, revisat i ampliat a partir del brief original (`brief_gnss_translation_engine_precision_gnss.pdf`) i de la investigació documentada a `BIBLIOGRAFIA.md`. Aquest document defineix **QUÈ** es construeix i **EN QUIN ORDRE**. El detall operatiu de **COM** fer cada pas és a `PLA-ACCIO.md`.

**Estat del document:** investigació completada, disseny proposat, **pendent d'aprovació — no s'ha escrit cap línia de codi encara.**

**Confirmat amb el client (2026-07-23):** precision-gnss.com és WordPress + WPML (llicència de pagament) + Elementor, **sense WooCommerce**. Tot el desenvolupament i les proves es fan contra un **staging propi del lloc**, no contra producció directament. La prioritat és traduir **el contingut** (posts/pages/CPTs/Elementor), **no el tema ni les strings de plugins**. Detall a `MEMORIA.md`.

---

## 0. Decisió arquitectònica clau (diferència respecte al brief original)

El brief proposa un `Python service / CLI` pur connectat via WordPress REST API. La investigació (`BIBLIOGRAFIA.md`, §10) mostra que això **no és suficient** per a l'escriptura de traduccions WPML: crear/vincular una traducció només és suportat oficialment via hooks PHP que s'executen *dins* de WordPress, i escriure certs metacamps (Yoast) via REST requereix registrar-los prèviament amb `register_post_meta()`.

**Arquitectura resultant (3 components, no 2):**

```
┌──────────────────────────┐
│  PRECISION-GNSS WORDPRESS │
│  WPML (CMS, $99/any) +    │
│  Elementor + Yoast        │
│                            │
│  ┌──────────────────────┐ │
│  │ gnss-bridge (mu-plugin)│ │  ← NOU component (no era al brief)
│  │ - Endpoints REST propis│ │
│  │   que embolcallen hooks │ │
│  │   WPML                 │ │
│  │ - register_post_meta() │ │
│  │   per a camps Yoast     │ │
│  │ - wpml-config.xml       │ │
│  └──────────────────────┘ │
└──────────┬─────────────────┘
           │ WordPress REST API (wp/v2/* + gnss-bridge/v1/*)
           │ + lectura MySQL directa (read-only) per a diagnòstic/auditoria
           ▼
┌────────────────────────────────┐
│  GNSS TRANSLATION ENGINE        │
│  (Python service/CLI, fora de WP)│
└──────────────┬───────────────────┘
               ▼
        DEEPSEEK API
```

- **Lectura de BD (MySQL, read-only):** permesa i útil per a auditoria (FASE 0), diagnòstic i validació de consistència (comparar el que diu la REST API amb el que hi ha realment a `icl_translations`). **No s'hi escriu mai directament.**
- **Escriptura de traduccions WPML:** sempre via el mu-plugin pont (`gnss-bridge`), que crida els hooks oficials (`wpml_set_element_language_details`, etc.) des de dins de WordPress.
- **Contingut Elementor:** es reutilitza la integració nativa WPML↔Elementor (disponible al pla CMS que ja es paga) mitjançant `wpml-config.xml`, en lloc de reconstruir tot el parser de JSON des de zero com proposava el brief. L'extractor propi (`elementor_extractor.py`) queda com a peça secundària només per a diagnòstic/dry-run (comptar blocs, estimar cost) i per a widgets no estàndard.

Això respon directament a la teva resposta ("triarem 1 i 3 o totes dues"): **s'aplica una combinació d'opció 1 (REST API) i opció 2 (lectura MySQL directa)**, evitant l'opció 3 (escriptura SQL directa a taules WPML) pel risc de corrupció documentat oficialment.

---

## FASE 0 — Auditoria i validació d'entorn (sobre l'staging, mai producció)

**Objectiu:** confirmar que els supòsits de la investigació es compleixen a l'**staging de precision-gnss.com** abans de dissenyar res més en detall.

- Confirmar que l'staging és una còpia fidel i actualitzada de producció (mateixes versions de WPML/Elementor/plugins) — si no ho és, refer-lo abans de continuar.
- Confirmar versió exacta de WPML instal·lada (4.9.x esperat) i el seu pla actiu (CMS).
- Confirmar versió d'Elementor i si és Free o Pro.
- Fer un `DESCRIBE` de les taules `icl_*` reals (accés lectura) i contrastar-les amb `BIBLIOGRAFIA.md` §1.
- Inventariar tipus de contingut traduïble, **prioritzant contingut editorial** (posts, pages, CPTs, widgets Elementor amb text, meta Yoast, camps ACF si n'hi ha). Les strings de tema/plugins (`icl_strings`) es documenten com a **fora d'abast per defecte** — només s'hi entra si el client ho demana explícitament.
- Seleccionar 5-10 pàgines de prova representatives (una simple, una Elementor complexa, un article, una pàgina amb taules, una amb molts enllaços).
- Verificar accés: credencials Application Password de l'staging, credencials MySQL read-only de l'staging, DEEPSEEK_API_KEY de prova.

**Resultat esperat:** document `AUDITORIA-INICIAL.md` (es crearà quan comenci l'execució) amb l'inventari real i qualsevol desviació respecte a aquest roadmap.

---

## FASE 1 — Component pont a WordPress (`gnss-bridge`)

**Objectiu:** desplegar el mu-plugin que fa de frontera segura entre l'script Python i els hooks interns de WPML/WordPress.

- Endpoint `POST /wp-json/gnss-bridge/v1/link-translation` → embolcalla `wpml_set_element_language_details`.
- Endpoint `GET /wp-json/gnss-bridge/v1/translation-status/{post_id}` → llegeix `trid`, idiomes existents, `needs_update`.
- `register_post_meta()` per a `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw` (lectura+escriptura via REST estàndard).
- `wpml-config.xml` amb `_elementor_data` (action=`translate`, encoding=`json`) i els camps ACF/custom que aparegui a l'auditoria de la FASE 0.
- Autenticació: reutilitza Application Passwords (mateix mecanisme que la resta de l'script), amb un usuari dedicat `translation_bot` amb rol mínim necessari (Editor, no Administrador).

**Camí addicional (2026-08-04, veure `BIBLIOGRAFIA.md` §11 i `MEMORIA.md`):** a banda del bridge d'hooks pur, `gnss-bridge` s'amplia amb endpoints que permeten que `translation_bot` operi com a **"traductor local"** dins del flux natiu de Translation Management de WPML (jobs + XLIFF), sense necessitat del Translation Partners Program:

- Endpoint `POST /wp-json/gnss-bridge/v1/create-job` → crida la funció interna de WPML que crea un job de Translation Management i l'assigna a `translation_bot`.
- Endpoint `GET /wp-json/gnss-bridge/v1/export-xliff/{job_id}` → crida la funció interna de WPML que genera l'XLIFF d'un job (la mateixa que usa el botó "Export" de l'admin), evitant automatitzar la pujada/descàrrega manual de fitxers.
- Endpoint `POST /wp-json/gnss-bridge/v1/import-xliff` → crida la funció interna d'importació d'XLIFF de WPML, perquè el job quedi com a "Complete" al dashboard natiu de WPML.
- Els noms exactes de les funcions/classes PHP internes a embolcallar es confirmen durant la FASE 0 (auditoria), inspeccionant el codi de `wpml-translation-management` un cop instal·lat.

**Per què primer:** totes les fases posteriors que escriuen a WordPress en depenen.

---

## FASE 2 — WordPress Connector (Python)

Equivalent a la FASE 2 del brief, ampliat perquè parli amb `gnss-bridge` a més de `wp/v2`:

```
get_post() / get_pages() / get_post_meta()
get_elementor_data() / get_yoast_metadata() / get_media()
get_wpml_status(post_id)         # NOU — via gnss-bridge
create_translation()             # crea el post ES via wp/v2 (status=draft)
link_translation(post_id, trid)  # NOU — via gnss-bridge, no SQL
```

## FASE 3 — Content Extraction Engine

- Parser d'Elementor **simplificat**: només per a `--dry-run` (comptar blocs/paraules, estimar cost) i per detectar widgets no coberts per la integració nativa de WPML.
- Extractor de blocs semàntics per a la resta de contingut (títols, paràgrafs, meta SEO, alt text) seguint el format `content_id`/`type`/`context`/`source` del brief (secció 6).
- Llista explícita de contingut protegit (secció 7.2 del brief): URLs, emails, SKUs, model numbers, CSS/JS, shortcodes, API keys, IDs.

## FASE 4 — Translation Engine (DeepSeek)

- `DeepSeekClient`: SDK compatible OpenAI, `base_url=https://api.deepseek.com`, model configurable (`deepseek-v4-pro` per traducció/QA, `deepseek-v4-flash` per metadades simples — noms vàlids post-migració 2026-07-24, veure `BIBLIOGRAFIA.md` §8).
- **JSON mode obligatori** per garantir el format de resposta estructurat (secció 11 del brief: `translation`, `confidence`, `issues`, `terminology_used`).
- Separació estricta Translator / Reviewer / Terminology Validator (secció 9 del brief) — 3 crides independents, no una de combinada.
- Retries, timeouts, rate limiting, tracking de tokens/cost.

## FASE 5 — Glossary Engine

- Fitxers JSON per domini (`gnss.json`, `surveying.json`, `forestry.json`, `spanish.json`) tal com defineix el brief (secció 8).
- `get_relevant_terms(text)`: filtratge per keyword matching abans d'enviar el subconjunt rellevant a DeepSeek (evitar enviar tot el glossari sencer a cada crida).
- `validate_translation(text)`: audita ús de terminologia obligatòria post-traducció.

## FASE 6 — Translation Memory i detecció de canvis

- Base SQLite pròpia (taules `source_content`, `content_blocks`, `translations`, `terminology`, `qa_results` — secció 18 del brief).
- Hash SHA-256 per bloc (granularitat fina) **+ contrast opcional amb el `md5`/`needs_update` de `icl_translation_status`** (trobat a la investigació) per detecció de canvis a nivell de pàgina sencera com a doble verificació.

## FASE 7 — QA Engine

- Verificació numèrica, unitats, termes crítics (GNSS, RTK, NTRIP, ZED-F9P...), URLs, QA semàntic via DeepSeek (secció 12 del brief).
- Sistema de puntuació amb llindars `≥95 auto-approve / 85-94 revisió humana / <85 rebuig` (secció 13).

## FASE 8 — Integració WPML (orquestració completa)

- `WPMLAdapter` que crida `gnss-bridge` per crear/vincular traduccions un cop la QA ha passat.
- Flux complet (secció 16 del brief): Scan → Change Check → Extract → Detect language → Glossary → DeepSeek → Structural QA → Technical QA → Score → PASS/REVIEW → Create/update WPML translation → Log.
- `AUTO_PUBLISH=false` per defecte — les traduccions es creen com `draft`/`pending review`, mai es publiquen soles.
- **`WPMLAdapter` amb dos camins d'escriptura triables per configuració (`.env`: `WPML_WRITE_MODE=hooks|job`, 2026-08-04):**
  - `link_translation()` — camí original via hooks purs (`gnss-bridge/v1/link-translation`).
  - `submit_via_job()` — camí "traductor local": crea job → exporta XLIFF → tradueix amb el pipeline ja construït (FASE 3-7, sense modificar) via el nou mòdul `app/wordpress/xliff.py` (adaptador `ContentBlock` ↔ XLIFF) → importa XLIFF via `gnss-bridge`, deixant el job com a "Complete" al dashboard natiu de WPML. Veure `BIBLIOGRAFIA.md` §11.

## FASE 9 — Pilot (5 pàgines reals)

- Una pàgina simple, una Elementor complexa, un article, una pàgina de use case, una pàgina amb taules/blocs especials — seguint exactament la selecció del brief (secció 21, FASE 9).
- Revisió humana de les 5 abans d'considerar el pilot un èxit.

## FASE 10 — Escalat i manteniment

- Mode `sync.py` en cru/cron per detectar contingut nou/modificat/eliminat.
- Ampliació a fr/de/it/pt un cop validat es/en.
- Possible reutilització a ArduSimple (mencionat al brief, secció 24) — **fora d'abast d'aquest projecte per ara**, es deixa anotat a `MEMORIA.md`.

---

## Dependències entre fases

```
FASE 0 (auditoria)
   │
   ▼
FASE 1 (gnss-bridge) ──► FASE 2 (WP Connector) ──► FASE 3 (Extraction)
                                                          │
        FASE 5 (Glossary) ◄───────────────────────────────┤
                │                                          ▼
                └──────────────────────────────────► FASE 4 (DeepSeek)
                                                          │
                                                          ▼
                                                   FASE 6 (Translation Memory)
                                                          │
                                                          ▼
                                                    FASE 7 (QA Engine)
                                                          │
                                                          ▼
                                                    FASE 8 (WPML Integration)
                                                          │
                                                          ▼
                                                    FASE 9 (Pilot)
                                                          │
                                                          ▼
                                                    FASE 10 (Escalat)
```

## Criteris d'èxit (heretats del brief, secció 22)

- 0 canvis de significat tècnic no intencionats.
- ≥98% consistència del glossari obligatori.
- 0 errors d'HTML/Elementor introduïts pel sistema.
- 0 URLs alterades accidentalment.
- 0 discrepàncies numèriques no justificades.
- 0 hreflang trencats / 0 canonicals incorrectes.
- Revisió humana disponible abans de publicar (`AUTO_PUBLISH=false`).
