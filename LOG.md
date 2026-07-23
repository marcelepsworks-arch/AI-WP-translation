# Log del projecte — GNSS AI Translation Engine

> Registre cronològic de sessions de treball. Cada entrada nova s'afegeix **a sobre** (ordre invers, més recent primer). Format: data, qui/què, resum breu, resultat, següent pas.

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
