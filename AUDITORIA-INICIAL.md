# Auditoria inicial — FASE 0

> Resultat de l'auditoria real contra `staging.precision-gnss.com`, fet amb accés d'administrador de WordPress i l'usuari de Basic Auth de l'staging. Correspon a `PLA-ACCIO.md` FASE 0. **Cap credencial apareix en aquest document** — es guarden només a `.env` local.

**Data de l'auditoria:** 2026-07-23
**Mètode:** WP REST API (`wp/v2`) + interfície `wp-admin` (via automatització de navegador), autenticat amb Basic Auth de l'staging + sessió d'administrador de WordPress.

---

## 0.0 — Fidelitat de l'staging respecte a producció

- El contingut de l'staging (pàgines RTK application: archaeology, precision-agriculture, drones-and-uav, etc.; posts de notícies) **coincideix amb el que es va veure a producció** (precision-gnss.com) durant la investigació de la sessió del resum executiu. No sembla una còpia obsoleta pel que fa a contingut.
- **Diferència crítica trobada: la versió/configuració de plugins de l'staging NO coincideix amb el que teníem assumit.** Veure secció 0.2.

## 0.1 — Accessos

- ✅ Basic Auth de protecció de l'staging: funcional (verificat amb `requests`, HTTP 200).
- ✅ Login d'administrador de WordPress (`/login_secure/`): funcional, sessió iniciada correctament.
- ⚠️ Encara no tenim credencials MySQL de només lectura — pendent per completar 0.4 (`DESCRIBE` de taules `icl_*`, que ara mateix tampoc existirien perquè WPML no està instal·lat, veure més avall).
- ⚠️ Encara no tenim un `DEEPSEEK_API_KEY` guardat de forma permanent (l'usuari n'ha compartit una puntualment en una sessió anterior, no desada).

## 0.2 — 🛑 Troballa crítica: WPML no està instal·lat

**WPML no apareix enlloc**: ni a la llista de 22 plugins (actius o inactius), ni als 3 mu-plugins, ni als namespaces de la REST API (`wp-json` no exposa `wpml/tm/v1` ni `wpml/st/v1`, que sí exposaria si WPML estigués actiu).

**Estat comunicat a l'usuari i decisió presa (2026-07-23):** avançar en les parts de l'auditoria/disseny que no depenen de WPML mentre no s'instal·la. **Tot el treball relacionat directament amb WPML (`gnss-bridge`, hooks, taules `icl_*`) queda pendent fins que WPML estigui instal·lat i actiu a l'staging.**

## 0.3 — Plugins rellevants confirmats

| Plugin | Versió | Estat | Rellevància |
|---|---|---|---|
| Elementor | 4.1.5 | Actiu | Constructor de pàgines — coincideix amb el brief |
| **Elementor Pro** | 4.0.4 | Actiu | Confirma que és la versió Pro, no Free |
| Yoast SEO | 28.0 | Actiu | Metadades SEO |
| Yoast SEO Premium | 27.1 | Actiu | — |
| WPS Hide Login | 1.9.18 | Actiu | Explica la URL d'admin personalitzada (`/login_secure/`) — **no afecta la REST API**, que continua a `/wp-json/` normal |
| Post Type Switcher | 4.0.1 | Actiu | Eina d'admin; no s'han trobat custom post types propis en ús (veure 0.5) |
| Fluent Forms | 6.2.5 | Inactiu | Formularis — si s'activa en un futur, cal valorar si el seu contingut necessita traducció |
| FluentCRM / FluentCRM Pro | 3.1.8 | Actiu | Marqueting per correu — fora d'abast de traducció de contingut web |
| Code Snippets | 3.9.6 | Actiu | Podria ser rellevant per desplegar codi PHP puntual (alternativa/complement a un mu-plugin) |
| UpdraftPlus | 1.26.5 | Actiu | Backups — recomanable fer-ne un abans de tocar res en FASE 1+ |
| **WooCommerce** | — | No instal·lat | Confirma la decisió ja presa a `MEMORIA.md` |
| **WPML** | — | **No instal·lat** | Veure 0.2 |
| ACF (Advanced Custom Fields) | — | No instal·lat | No hi ha custom fields ACF a auditar |

## 0.4 — Base de dades

Pendent — requereix credencials MySQL de només lectura, no rebudes encara. Com que WPML no està instal·lat, les taules `icl_*` de `BIBLIOGRAFIA.md` §1 **encara no existeixen** a aquesta BD; aquesta part de la investigació es podrà validar/corregir només després d'instal·lar WPML.

## 0.5 — Inventari de contingut traduïble

**Tipus de contingut:** només `post` (articles/notícies) i `page` (pàgines fixes) — **no hi ha custom post types propis**. Els únics post types addicionals són interns d'Elementor (`elementor_library`, `elementor_snippet`, `e-floating-buttons`) i de FluentCRM (`fcrm-dummy`), cap dels quals conté contingut editorial de cara al públic.

| Tipus | Quantitat |
|---|---|
| Pages | 24 |
| Posts | 17 |
| Media (imatges, etc.) | 390 |

**Pages (24):**
Archaeology, RTK Application (índex), Precision GNSS – RTK news, Support Contact, Popup Mailchimp, Environmental Monitoring with GNSS RTK, Drones and UAV, Cookies Policy, Privacy Policy, Contact us, Home 2026, Sport Tracking, Forestry, Location-based Games, Railway, Maritime and Inland Waterways, Ground robots, Precision Agriculture, Research and Development, Automotive, Heavy Duty Vehicles, RTK Base Station (CORS), Survey and Mapping, Legal Advice.

**Posts (17, notícies/articles):** RTK GNSS for Robotics, ZED-X20D vs UM982 vs mosaic-G5, How 5G Gateways and RTK..., 6 Ways RTK Boundaries..., Navigating Without a Compass..., Breaking the Canopy Barrier, Low-Cost RTK in Archaeology, GNSS/RTK in Sport Tracking, Forestry (rtk-for-forestry), Base Station (CORS), Archaeology (precision-rtk-receivers-for-archaeology), Mapping utilities, How AI-Driven "Trust Metrics"..., Ground robots, Drones and UAV, Are you an surveyor?, Precision Farming.

**Camps Yoast via REST API — confirmació de la investigació prèvia:** el camp `meta` que retorna l'API per a una pàgina (`wp/v2/pages/{id}`) és pràcticament buit (`{"footnotes": ""}`); Yoast només exposa `yoast_head`/`yoast_head_json` (lectura, HTML/JSON ja renderitzat), **no els camps individuals editables** (`_yoast_wpseo_title`, `_yoast_wpseo_metadesc`, etc.). **Confirma exactament la troballa de `BIBLIOGRAFIA.md` §6**: caldrà `register_post_meta()` en un mu-plugin per poder-los llegir/escriure individualment via REST.

**`_elementor_data`:** tampoc apareix al camp `meta` per defecte — mateixa conclusió, caldrà exposar-lo explícitament (mu-plugin o `wpml-config.xml` un cop WPML estigui instal·lat).

## 0.6 — Pàgines candidates per al pilot (FASE 9)

Selecció provisional (a confirmar quan arribi la FASE 9), seguint els criteris del brief:

| Criteri | Pàgina |
|---|---|
| Simple | Contact us / Home 2026 |
| Elementor complexa | Precision Agriculture (`/precision-agriculture/`) |
| Article | RTK GNSS for Robotics: Getting Real 1-2 cm Accuracy |
| Amb taules/blocs especials | Survey and Mapping (a confirmar en revisar-la visualment) |
| Amb molts enllaços | RTK Application (pàgina índex, enllaça totes les aplicacions) |

---

## Resum i propers passos

- ✅ Accés WordPress i staging confirmat i funcional.
- ✅ Elementor Pro, Yoast Premium confirmats — sense WooCommerce ni ACF.
- ✅ Inventari de contingut complet (24 pages + 17 posts).
- ✅ Confirmada empíricament la necessitat del mu-plugin `gnss-bridge` per als camps Yoast/Elementor (ja prevista al disseny).
- 🛑 **WPML no instal·lat** — bloqueja FASE 1 (hooks WPML), FASE 8 (orquestració) i part de FASE 0 (taules `icl_*`) fins que s'instal·li.
- ⏳ Pendent: credencials MySQL de només lectura.

**Següent pas recomanat:** avançar en peces que no depenen de WPML — per exemple, el `WordPress Connector` (FASE 2) per a les parts no-WPML (`get_post`, `get_pages`, `get_post_meta`), ja que ara tenim un site real contra el qual provar-lo.
