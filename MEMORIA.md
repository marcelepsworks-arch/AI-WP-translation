# Memòria del projecte — GNSS AI Translation Engine

> Registre viu de decisions, context i supòsits del projecte. **S'ha d'actualitzar cada vegada que es prengui una decisió rellevant o es descobreixi alguna cosa que canviï el pla.** No és un log cronològic detallat (això és `LOG.md`) — és el resum de "per què les coses són com són ara".

---

## Context del projecte

- **Client/lloc:** Precision-GNSS.com (WordPress + WPML + Elementor + Yoast). **Sense WooCommerce.**
- **Objectiu inicial:** traducció automàtica EN → ES (castellà europeu), amb arquitectura preparada per ampliar a FR/DE/IT/PT.
- **Motor de traducció:** DeepSeek API.
- **Entorn de desenvolupament:** un **staging de la pròpia web** precision-gnss.com (no es desenvolupa directament contra producció). Producció és WordPress + WPML (llicència de pagament) + Elementor.
- **Focus del contingut a traduir:** **el contingut (posts/pages/CPTs/Elementor), no el tema.** Les strings de tema/plugins (allò que gestiona `icl_strings`/String Translation — textos fixos del theme, labels de plugins, etc.) **queden fora de l'abast prioritari**; l'objectiu és el contingut editorial real del lloc.
- **Possible reutilització futura:** ArduSimple (mencionat al brief original, secció 24) — **no forma part de l'abast actual**, només s'anota aquí per no perdre'n la traça si en el futur es reprèn.
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
