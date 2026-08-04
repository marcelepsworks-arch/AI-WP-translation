# Memòria del projecte — GNSS AI Translation Engine

> Registre viu de decisions, context i supòsits del projecte. **S'ha d'actualitzar cada vegada que es prengui una decisió rellevant o es descobreixi alguna cosa que canviï el pla.** No és un log cronològic detallat (això és `LOG.md`) — és el resum de "per què les coses són com són ara".

---

## Context del projecte

- **Client/lloc:** Precision-GNSS.com (WordPress + WPML + Elementor + Yoast). **Sense WooCommerce.**
- **Objectiu inicial:** traducció automàtica EN → ES (castellà europeu), amb arquitectura preparada per ampliar a FR/DE/IT/PT.
- **Motor de traducció:** DeepSeek API.
- **Entorn de desenvolupament:** un **staging de la pròpia web** precision-gnss.com (no es desenvolupa directament contra producció). Producció és WordPress + WPML (llicència de pagament) + Elementor.
- **Focus del contingut a traduir:** **el contingut (posts/pages/CPTs/Elementor), no el tema.** Les strings de tema/plugins (allò que gestiona `icl_strings`/String Translation — textos fixos del theme, labels de plugins, etc.) **queden fora de l'abast prioritari**; l'objectiu és el contingut editorial real del lloc.
- **Possible reutilització futura:** ArduSimple (mencionat al brief original, secció 24) — només s'anota aquí per no perdre'n la traça.
- **2026-07-24 — Canvi d'abast:** l'usuari ha demanat implementar suport a **WooCommerce per a altres llocs WordPress** (no `precision-gnss.com`, que confirmadament no en té). El motor d'extracció de productes es construeix com a **capacitat genèrica i reutilitzable**, basada en l'esquema estable de `wc/v3/products`, no lligada a cap lloc concret — vàlid per a qualsevol WordPress+WooCommerce futur (p. ex. ArduSimple). **No es pot validar empíricament ara** (cap lloc WooCommerce dins l'abast actual per fer-hi proves reals); es documenta i es prova amb dades sintètiques fidels a l'esquema oficial, i es marca per a validació real quan hi hagi un lloc real disponible.
- **Document font:** `brief_gnss_translation_engine_precision_gnss.pdf`, aportat pel client/usuari amb l'arquitectura, prompts, esquema de BD i roadmap inicials.

## Decisions clau preses

### 2026-07-23 — Llicència WPML confirmada
**Decisió:** el projecte farà servir WPML de pagament, pla que costa **99$/any per a 2 llocs de producció** (correspon al pla **Multilingual CMS**).
**Per què:** aclariment directe de l'usuari — WPML no té versió gratuïta permanent per a producció (només trial temporal o el complement gratuït "String Translation" per a temes/plugins, que no cobreix el cas d'ús).
**Com aplicar-ho:** el pla CMS **inclou la integració nativa amb Elementor** (veure `BIBLIOGRAFIA.md` §4), cosa que simplifica significativament l'arquitectura respecte al brief original (no cal reconstruir tot el parser d'Elementor des de zero).

### 2026-07-23 — Estratègia d'accés a la base de dades
**Decisió:** arquitectura híbrida: **lectura MySQL directa (read-only)** per a auditoria/diagnòstic + **WordPress REST API** per a operacions estàndard + **hooks PHP oficials de WPML, exposats via un mu-plugin propi (`gnss-bridge`)** per a l'escriptura de traduccions.
**Per què:** l'usuari va indicar que caldrà "atacar els camps de la base de dades del plugin WPML" (accés directe). La investigació (`BIBLIOGRAFIA.md` §1-3) confirma que WPML desaconsella oficialment escriure directament a `icl_translations` i taules relacionades (risc d'inconsistència entre `trid`, `icl_translation_status`, cache d'objectes de WP), i que **no existeix una REST API pública de WPML per crear traduccions** — només hooks PHP interns. Per tant es descarta l'opció 3 pura (SQL d'escriptura directa) i es combinen les opcions 1 i 2 tal com l'usuari va proposar.
**Com aplicar-ho:** veure `ROADMAP.md` §0 (diagrama d'arquitectura) i `PLA-ACCIO.md` FASE 1.

### 2026-07-23 — Abast del primer lliurament
**Decisió:** aquest cicle de treball només produeix documentació (bibliografia, roadmap, pla d'acció, memòria, logs) — **no s'escriu cap codi**.
**Per què:** petició explícita de l'usuari ("no comencis a desenvolupar rès").
**Com aplicar-ho:** el desenvolupament real (FASE 0 en endavant) no comença fins que l'usuari ho aprovi explícitament en una conversa futura.

### 2026-07-23 — Entorn de treball i abast del contingut confirmats
**Decisió:** (a) tot el desenvolupament i les proves es fan contra un **staging de precision-gnss.com**, mai directament contra producció; (b) el lloc **no té WooCommerce**; (c) la prioritat de traducció és **el contingut** (posts, pages, CPTs, widgets Elementor amb text editorial) i **no el tema/strings de plugins** (allò que WPML gestiona amb `icl_strings`/String Translation).
**Per què:** confirmació directa de l'usuari.
**Com aplicar-ho:**

- S'elimina la incertesa d'"entorn de staging disponible?" dels supòsits pendents — ja està confirmat que sí n'hi ha.
- FASE 0 (auditoria) i FASE 1 (`gnss-bridge`) es fan sempre sobre l'staging; el pas a producció és una decisió posterior explícita, no automàtica.
- Com que no hi ha WooCommerce, es descarten de l'abast els endpoints/particularitats de "WPML Multilingual & Multicurrency for WooCommerce" (`BIBLIOGRAFIA.md` §3) — són només una referència de com WPML filtra per `?lang=` a REST, no una dependència real del projecte.
- L'inventari de la FASE 0 (`PLA-ACCIO.md` 0.5) ha de **prioritzar** posts/pages/CPTs/Elementor/Yoast, i tractar l'extracció de strings de tema/plugins (`icl_strings`) com a **fora d'abast per defecte**, tret que el client identifiqui text de tema visible que també vulgui traduir.

### 2026-07-23 — App externa vs. plugin WordPress "tot en un"
**Decisió:** el motor de traducció (extracció, glossari, crides DeepSeek, QA, translation memory) viu en una **app externa** (Python, fora de WordPress). El plugin WordPress (`gnss-bridge`) es manté **mínim**, només com a pont per als hooks WPML i els camps Yoast — mai s'hi afegeix lògica de traducció.
**Per què:** el brief demana 3 crides DeepSeek independents per bloc (traductor / revisor tècnic / validador de terminologia, secció 9), cada una potencialment lenta. Fer-ho dins de PHP/WordPress té problemes reals: timeouts d'execució de PHP en hosting compartit, sense cues/retries robustos, i bloqueig del worker PHP mentre s'espera resposta de l'API. Una app externa permet SDK Python adequat, rate limiting, cues, tests i execució per cron sense dependre dels límits de l'hosting. El pont PHP és imprescindible igualment perquè vincular traduccions a WPML només és possible amb hooks interns que s'executen dins de WordPress (veure decisió "Estratègia d'accés a la base de dades").
**Com aplicar-ho:** cap canvi a `ROADMAP.md`/`PLA-ACCIO.md` — ja descriuen aquesta separació (§0 del roadmap, FASE 1 vs. FASE 2-8 del pla d'acció); aquesta entrada només fa explícit el raonament perquè no calgui redescobrir-lo en una sessió futura.

### 2026-07-23 — Accés a l'staging confirmat: FASE 0 desbloquejada
**Decisió/fet:** l'usuari ha proporcionat accés a `staging.precision-gnss.com`, protegit amb HTTP Basic Auth. Accés verificat (HTTP 200, WordPress detectat amb Yoast SEO Premium). L'usuari indica que a continuació donarà també accés d'administrador de WordPress.
**Per què:** desbloqueja la FASE 0 (auditoria) del `PLA-ACCIO.md`, aturada fins ara.
**Com aplicar-ho:** credencials guardades **només** en `.env` local (mai versionat — confirmat amb `git check-ignore`). `.env.example` actualitzat amb l'estructura (`STAGING_URL`, `STAGING_BASIC_AUTH_USER`, `STAGING_BASIC_AUTH_PASSWORD`, `WP_USERNAME`, `WP_APPLICATION_PASSWORD`) sense cap valor real. **Recordatori de seguretat permanent:** cap credencial (contrasenyes, API keys, tokens) s'escriu mai a `MEMORIA.md`, `LOG.md`, `ROADMAP.md`, `PLA-ACCIO.md` ni cap altre fitxer versionat — només a `.env` local.

### 2026-08-04 — DeepSeek com a "proveïdor natiu" de WPML: es descarta el Translation Partners Program, s'amplia `gnss-bridge`
**Decisió:** no es persegueix que DeepSeek aparegui com a servei de traducció visible a `WPML → Translation Dashboard → Translation Services` (això requeriria el Translation Partners Program: registre públic, mínim 5 projectes — excessiu per a ús intern d'una sola web). En comptes d'això, s'amplia el mateix mu-plugin `gnss-bridge` (ja dissenyat a FASE 1) amb tres endpoints nous (`create-job`, `export-xliff`, `import-xliff`) que criden directament les funcions internes de WPML de creació de jobs i export/import d'XLIFF, perquè `translation_bot` operi com a **"traductor local"** dins del flux natiu de Translation Management de WPML (sense partnership). El bridge d'hooks pur (FASE 1 original) es manté sense canvis com a camí alternatiu.
**Per què:** el client va demanar explorar l'opció de "proveïdor natiu"; la investigació (`BIBLIOGRAFIA.md` §11) confirma que la via de partner és desproporcionada per aquest cas, però que WPML sí ofereix un flux de "traductor local" + jobs accessible sense partnership. Automatitzar la pujada/descàrrega manual d'XLIFF de l'admin de WPML (sense API documentada) es descarta per fràgil/poc professional; en lloc d'això es crida les funcions internes reals des del bridge, igual que ja es fa amb els hooks de vinculació. El client ha prioritzat explícitament l'opció "més segura i professional" per sobre de la més ràpida, i reutilitzar el 100% del pipeline Python ja construït (FASE 3-7).
**Com aplicar-ho:** veure `ROADMAP.md` (FASE 1 i FASE 8 ampliades), `PLA-ACCIO.md` (tasques 1.8, 1.9, 8.6, 8.7) i `BIBLIOGRAFIA.md` §11. Els noms exactes de les funcions PHP internes de WPML a embolcallar encara s'han de confirmar quan WPML estigui instal·lat (FASE 0, encara bloquejada).

### 2026-08-04 — `app/wordpress/wpml.py` construït contra el contracte documentat (sense WPML instal·lat)
**Decisió/fet:** s'ha implementat `app/wordpress/wpml.py` amb els dos camins d'escriptura documentats (hooks: `get_wpml_status()`/`link_translation()`; traductor local/XLIFF: `create_job()`/`export_xliff()`/`import_xliff()`, més els helpers `start_job()`/`complete_job()`), i s'ha afegit `WordPressClient.post()` (fins ara el client només tenia `get()`). Tot provat amb 11 tests nous d'HTTP mockejat.
**Per què:** era feina ja prevista a `PLA-ACCIO.md` (2.4, 8.1, 8.7) i el client va demanar continuar amb tot el que es pogués fer sense el plugin `gnss-bridge`/WPML real. Es va descartar la idea original d'un únic mètode `submit_via_job()` (tal com estava esbossat a `ROADMAP.md`) perquè crear el job i exportar-ne l'XLIFF ha de passar **abans** que el pipeline de traducció (FASE 4-7) processi els blocs, i tornar-los a inserir/importar ha de passar **després** — un únic mètode no li dona a qui crida el punt d'enganxe per fer la traducció enmig. Es va dividir en `start_job()` (crea job + exporta + parseja a `ContentBlock`) i `complete_job()` (insereix traduccions + importa), deixant clar que la traducció pròpiament dita és responsabilitat de l'orquestrador (FASE 8.2, encara sense fer).
**Com aplicar-ho:** cap d'aquest codi està validat contra un `gnss-bridge`/WPML real (no instal·lat encara). Es marca igual que `woocommerce_extractor.py`: fet i provat contra el contracte documentat/sintètic, pendent de validació empírica. Veure `PLA-ACCIO.md` tasques 2.4/8.1/8.7.

## Supòsits pendents de verificar (a la FASE 0 real)

- Versió exacta de WPML instal·lada a l'staging/producció (s'assumeix 4.9.x; **no** 5.0 Beta) — pendent de confirmació directa contra el lloc.
- Existència i abast real de camps ACF o altres custom fields no documentats al brief.
- Si l'hosting permet crear un usuari MySQL amb permisos només de lectura per a l'script (a l'staging).
- Confirmar que l'staging és una còpia fidel i actualitzada de producció (WPML, Elementor i plugins amb les mateixes versions) abans de donar per bones les proves fetes allà.

## Glossari de termes propis del projecte (per no confondre's en futures sessions)

- **`gnss-bridge`**: nom provisional del mu-plugin pont que exposa endpoints REST propis embolcallant els hooks WPML. No existeix encara — és una peça de disseny, no codi desplegat.
- **`trid`**: "translation group ID" de WPML — l'identificador que agrupa totes les versions d'idioma d'un mateix contingut a `icl_translations`.
- **Hooks WPML "dels 3 passos"**: `wpml_element_type` → `wpml_element_language_details` → `wpml_set_element_language_details`. Patró oficial per vincular una traducció al seu original (veure `BIBLIOGRAFIA.md` §2).

## Documents relacionats

- `BIBLIOGRAFIA.md` — totes les fonts investigades amb resums.
- `ROADMAP.md` — full de ruta per fases (QUÈ i EN QUIN ORDRE).
- `PLA-ACCIO.md` — tasques concretes amb criteris de verificació (COM).
- `LOG.md` — registre cronològic de sessions de treball.
- `brief_gnss_translation_engine_precision_gnss.pdf` — document original del client.
