# Log del projecte — GNSS AI Translation Engine

> Registre cronològic de sessions de treball. Cada entrada nova s'afegeix **a sobre** (ordre invers, més recent primer). Format: data, qui/què, resum breu, resultat, següent pas.

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
