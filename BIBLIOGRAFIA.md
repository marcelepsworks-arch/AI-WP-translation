# Bibliografia i fonts d'investigació

> Recull de totes les fonts consultades per dissenyar l'arquitectura del GNSS AI Translation Engine, amb un resum del que aporta cada font. Data de la investigació: 2026-07-23.

---

## 1. WPML — Base de dades i versió actual

### Versió actual del plugin (investigat 2026-07-23)
Font: [WPML Changelog](https://wpml.org/category/changelog/), [WPML 4.9.5](https://wpml.org/changelog/2026/06/wpml-4-9-5-full-php-8-5-support-and-a-smoother-site-migration-experience/), [WPML 5.0 Beta](https://wpml.org/changelog/2026/07/wpml-5-0-beta/)

- **Versió estable actual: WPML 4.9.5** (publicada 2026-06-10) — suport complet PHP 8.5, fixes de migració de lloc.
- **WPML 5.0** està en **Beta** (anunciada 2026-07) — reescriu la navegació/configuració i fa la traducció automàtica el mode per defecte en llocs nous. Els seus autors adverteixen explícitament: *"this beta should be installed on a testing site only, not on a live site"*.
- **Recomanació pel projecte:** desenvolupar i validar el pipeline contra **WPML 4.9.x** (la que hi haurà en producció a precision-gnss.com), i tractar 5.0 com a risc de trencament futur a vigilar (secció "Riscos" del `PLA-ACCIO.md`) — 5.0 promet canvis a com es gestiona el motor de traducció intern, cosa que podria afectar l'esquema de BD i/o els hooks.

### [WPML's Database Tables](https://wpml.org/documentation/support/wpml-tables/) (font oficial)
Documentació oficial de l'esquema de BD de WPML. **Nota important:** WPML no publica un diccionari de dades complet (CREATE TABLE) per a totes les taules — és una decisió deliberada, coherent amb el seu avís de "no manipular la BD directament". Els noms de columna d'aquesta llista provenen de la documentació oficial i de codi font consultat (mòdul `sitepress-multilingual-cms`, la base lliure/legacy de WPML a `wordpress.org`/GitHub); **cal verificar-los amb un `DESCRIBE` real contra la instal·lació de precision-gnss.com durant la FASE 0 (auditoria)**, perquè poden variar lleugerament entre versions (4.9.x vs. la futura 5.0).

**Taules clau identificades i localitzades:**

| Taula (prefix `wp_`) | Propòsit | Columnes conegudes |
|---|---|---|
| `icl_translations` | Taula central de mapeig de traduccions. Cada post/page/CPT/taxonomia traduïble té una fila aquí. | `translation_id` (PK), `element_type` (`post_{tipus}` / `tax_{taxonomia}`), `element_id` (= `post_id` o `term_taxonomy_id`), `trid` (translation group ID — agrupa totes les traduccions d'un mateix contingut entre idiomes), `language_code`, `source_language_code` |
| `icl_translation_status` | Estat de cada tasca de traducció: `status`, **`needs_update`** (flag booleà — **exactament el mecanisme de "detecció de canvis" que demana el brief, ja existent dins WPML**), **`md5`** (hash del contingut origen — WPML ja fa internament el mateix que el brief proposa amb SHA-256 a la secció 5), `translation_service`, `translation_package`, `timestamp`, `links_fixed` | — |
| `icl_strings` | Strings traduïbles fora de contingut (temes, plugins, widgets, textos d'Elementor no vinculats a camps registrats) | `id`, `language`, `context`, `name`, `value`, `string_package_id`, `type`, `status` |
| `icl_string_translations` | Traduccions de les strings anteriors | `id`, `string_id`, `language`, `status`, `value`, `translator_id`, `translation_service`, `batch_id` |
| `icl_flags` | Icones de bandera per idioma | `id` (PK autoincrement), `lang_code` (varchar 10, UNIQUE), `flag` (varchar 32), `from_template` (tinyint) — **única taula amb `CREATE TABLE` complet confirmat al codi font** |
| `icl_languages` | Idiomes actius al lloc | — (confirmar amb `DESCRIBE`) |
| `icl_locale_map` | Mapeig de codis d'idioma (`es`) a locales complets (`es_ES`) | — |
| `icl_node` | Relacions jeràrquiques de contingut (menús, etc.) | — |
| `icl_translate`, `icl_translate_job` | Cues de treball de l'Advanced Translation Editor / Translation Management. **Poden créixer molt de mida** (reportat als fòrums oficials com a problema recurrent) | — |
| `icl_content_status`, `icl_core_status` | Estat de sincronització de contingut/core | — |

**⚠️ Advertència oficial:** *"Direct database manipulation is not recommended. Use WPML's admin interface (o l'API oficial de hooks) per mantenir la integritat de les dades."* Això reforça el principi arquitectònic del brief (secció 2): no escriure directament a MySQL.

**🔎 Troballa clau per al disseny:** la columna `md5` de `icl_translation_status` demostra que WPML **ja implementa un sistema de hash de contingut per detectar canvis**, molt semblant al que el brief demana construir des de zero (SHA-256 per bloc, secció 5). Això obre una tercera via de disseny a avaluar a la FASE 1: en lloc de mantenir un hash propi *només*, el Change Detector del motor pot **llegir també aquest `md5`/`needs_update` de WPML per contrastar-lo** amb el propi (doble verificació), o fins i tot delegar-hi parcialment la detecció a nivell de pàgina sencera, i reservar el hash SHA-256 propi per a la granularitat de bloc (paràgraf, CTA, alt text) que WPML no ofereix nativament.

---

## 2. WPML — API oficial (hooks PHP)

### [wpml_set_element_language_details](https://wpml.org/wpml-hook/wpml_set_element_language_details/) (font oficial)
Action hook per crear/actualitzar la relació d'idioma d'un element (vincular una traducció al seu original).

**Paràmetres clau:**
- `element_id`: ID del post/element traduït
- `element_type`: `post_post`, `post_page`, `post_{cpt}`, `tax_{taxonomia}`, etc.
- `trid`: ID del grup de traducció (si es passa `FALSE`, es crea un `trid` nou i es trenquen relacions existents — **perillós, cal sempre reutilitzar el `trid` de l'original**)
- `language_code` / `source_language_code`

### [wpml_object_id](https://wpml.org/wpml-hook/wpml_object_id/) (font oficial)
Filter per obtenir l'ID d'un objecte traduït a partir de l'ID original i l'idioma destí. Útil per comprovar si ja existeix traducció abans de crear-ne una de nova (evitar duplicats).

### [How to programmatically insert translation? (fòrum WPML)](https://wpml.org/forums/topic/how-to-programatically-insert-translation/)
Confirma el patró de 3 passos oficial:
1. `apply_filters('wpml_element_type', 'post')` → obtenir el tipus d'element que WPML espera.
2. `apply_filters('wpml_element_language_details', null, ['element_id' => ID, 'element_type' => 'post'])` → obtenir el `trid` i `language_code` de l'original.
3. `do_action('wpml_set_element_language_details', [...])` → vincular el nou post traduït al `trid` de l'original.

### [Programmatically link multilingual WordPress posts With WPML — Ashar Irfan](https://asharirfan.com/programmatically-link-multilingual-wordpress-posts-with-wpml/)
Exemple de codi PHP complet que implementa el patró dels 3 passos anteriors. Aquesta és **la via oficialment suportada per crear/vincular traduccions**, en lloc d'un `INSERT` SQL directe a `icl_translations`.

```php
// 1. Element type
$wpml_element_type = apply_filters('wpml_element_type', 'post');

// 2. Dades d'idioma de l'original
$original_lang_info = apply_filters('wpml_element_language_details', null, [
    'element_id'   => $original_post_id,
    'element_type' => 'post',
]);

// 3. Vincular la traducció
do_action('wpml_set_element_language_details', [
    'element_id'           => $translated_post_id,
    'element_type'         => $wpml_element_type,
    'trid'                 => $original_lang_info->trid,
    'language_code'        => 'es',
    'source_language_code' => $original_lang_info->language_code,
]);
```

**Implicació arquitectònica important:** aquests hooks són codi PHP que s'ha d'executar *dins* de WordPress (com a plugin propi, mu-plugin, o via `wp eval`/WP-CLI), no des d'un script Python extern pur. Això afecta el disseny del "WordPress Connector" (FASE 2 del brief).

---

## 3. WPML — REST API pròpia

### [Features in WPML that Depend on the WordPress REST API](https://wpml.org/documentation/support/rest-api-dependencies/) (font oficial)
- Namespace `wpml/tm/v1`: usat per l'Advanced Translation Editor i Translation Management jobs.
- Namespace `wpml/st/v1`: usat per la importació/generació de fitxers `.mo` i configuració de String Translation.
- WPML només accedeix a la REST API com a usuari autenticat, mai anònimament.
- **No hi ha un endpoint REST públic i documentat per crear traduccions de contingut de manera programàtica** (a diferència dels hooks PHP de la secció 2). Els namespaces `tm/v1` i `st/v1` són interns per al funcionament de l'ATE (Advanced Translation Editor), no estan pensats com a API pública per a integracions de tercers.

### [WPML Multilingual & Multicurrency for WooCommerce — REST API](https://wpml.org/documentation/related-projects/woocommerce-multilingual/using-wordpress-rest-api-woocommerce-multilingual/) (font oficial)
Exemple del patró `?lang=es` que WPML afegeix als endpoints estàndard de WooCommerce REST per filtrar per idioma. Confirma que el mecanisme general de WPML amb REST és afegir el paràmetre `lang` a les crides estàndard de `wp/v2/*`, no crear un CRUD de traduccions propi.

**Conclusió:** per **crear** traduccions cal, o bé (a) els hooks PHP dins WP, o (b) l'Advanced Translation Editor / interfície d'admin. Per **llegir** contingut per idioma, la REST API estàndard `wp/v2/posts?lang=es` funciona bé un cop WPML està actiu.

---

## 4. WPML — Elementor (integració oficial)

### [How to Translate an Elementor Website with WPML](https://wpml.org/documentation/plugins-compatibility/elementor/) (font oficial)
WPML té una **integració nativa amb Elementor** integrada al seu Translation Editor: en seleccionar una pàgina Elementor des del Translation Dashboard, WPML detecta i exposa automàticament tots els widgets i el seu contingut traduïble, sense que calgui parsejar manualment el JSON de `_elementor_data`.

**Requisit de llicència:** aquesta integració completa (Global Widgets, templates, traducció automàtica) requereix el pla **Multilingual CMS o Agency** — **coincideix amb el pla de pagament triat pel projecte ($99/any = pla CMS)**, així que la integració nativa és viable.

### [A New Way to Translate Elementor Pages With WPML (elementor.com)](https://elementor.com/blog/translate-elementor-with-wpml/)
Confirma que WPML tradueix els widgets "in place" com a part de la traducció de la pàgina sencera, mantenint layout, IDs i estils.

### [WPML Language Configuration Files — Custom Fields Translation Options](https://wpml.org/documentation/support/language-configuration-files/custom-fields-translation-options/) (font oficial)
El fitxer **`wpml-config.xml`** permet declarar com WPML ha de tractar camps personalitzats (custom fields) com `_elementor_data` o els meta de Yoast:

```xml
<wpml-config>
  <custom-fields>
    <custom-field action="translate" style="visual" label="Content">
      _elementor_data
    </custom-field>
    <custom-field action="translate" label="SEO Title">
      _yoast_wpseo_title
    </custom-field>
    <custom-field action="copy">product_sku</custom-field>
  </custom-fields>
</wpml-config>
```

Accions disponibles: `translate` (envia a l'editor de traducció), `copy` (sincronitza sempre), `copy once` (còpia inicial, no sincronitza), `ignore`. Suporta atribut `encoding="json"` per a camps que contenen JSON serialitzat com `_elementor_data`.

**Implicació arquitectònica clau:** aquest fitxer ja resol nativament gran part del que el brief proposa construir a mà a `elementor_extractor.py` (secció 6 del brief). **Recomanació:** usar `wpml-config.xml` + la integració nativa d'Elementor com a capa base, i reservar l'extractor propi només per al contingut que WPML *no* exposa bé (camps ACF exòtics, popups, alguns strings de plugins).

### [Registering Custom Elementor Widgets for Translation (WPML Multilingual Tools)](https://wpml.org/documentation/support/multilingual-tools/registering-custom-elementor-widgets-for-translation/)
Per a widgets d'Elementor personalitzats (no estàndard) que WPML no detecta automàticament, cal registrar-los explícitament via el plugin "WPML Multilingual Tools".

---

## 5. WordPress REST API — Autenticació i contingut

### [Authentication — REST API Handbook (developer.wordpress.org)](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/) (font oficial)
Mètode recomanat per a scripts externs: **Application Passwords** (natiu des de WP 5.6), Basic Auth sobre HTTPS.

### [WordPress Application Passwords: Full Setup Guide (2026)](https://nextgrowth.ai/wordpress-application-passwords-setup-guide/)
Passos: `wp-admin → Users → Edit User → Application Passwords`, genera una contrasenya de 24 caràcters, revocable independentment de la contrasenya principal. Exemple Python:

```python
import requests, base64
credentials = f"{user}:{app_password}"
token = base64.b64encode(credentials.encode()).decode()
headers = {'Authorization': f'Basic {token}'}
requests.get(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers)
```

**Requisit:** el lloc ha d'anar sobre HTTPS (precision-gnss.com ja hi va).

---

## 6. Yoast SEO — REST API

### [Yoast SEO: REST API — Yoast Developer Portal](https://developer.yoast.com/customization/apis/rest-api/) (font oficial)
Yoast exposa un camp `yoast_head` (HTML ja renderitzat) a les respostes de `wp/v2/posts`, útil per a **lectura**.

### [Setting Yoast SEO fields via API for automated publishing (wordpress.org support)](https://wordpress.org/support/topic/setting-yoast-seo-fields-via-api-for-automated-wordpress-publishing/)
**Limitació important:** per defecte, els camps `_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw`, `_yoast_wpseo_title` **no són escrivibles via REST API** (`show_in_rest` no està activat de fàbrica). Cal registrar-los explícitament amb `register_post_meta()` (via `functions.php` d'un child theme o un mu-plugin) perquè el `POST /wp/v2/posts/{id}` amb `meta.{camp}` funcioni per **escriure**.

**Implicació:** cal desplegar un petit mu-plugin al WordPress de Precision-GNSS que exposi (a) els camps Yoast en escriptura via REST, i (b) opcionalment un endpoint personalitzat que embolcalli els hooks WPML de la secció 2, ja que aquests hooks només es poden cridar des de dins de WordPress.

---

## 7. Elementor — Estructura de dades

### [Data Structure — Elementor Developers](https://developers.elementor.com/docs/data-structure/) (font oficial)
El contingut d'una pàgina Elementor es guarda com a JSON al camp de postmeta `_elementor_data`. Estructura d'alt nivell: `{ "content": [...], "page_settings": {...}, "version": "...", "title": "...", "type": "..." }`.

### [Widget Element — Elementor Developers](https://developers.elementor.com/docs/data-structure/widget-element/)
Cada element té `id`, `elType` (`section`, `column`, `container`, `widget`), `widgetType` (per a widgets), i un objecte `settings` amb les claus pròpies de cada tipus de widget (varien segons la classe PHP del widget — cal consultar el codi font del widget per saber quines claus contenen text traduïble).

**Recomanació pràctica trobada:** "Direct manipulation of this JSON is possible but fragile — always back up first". Després de qualsevol modificació via WP-CLI cal invalidar la cache CSS d'Elementor (`wp elementor flush-css` o equivalent).

---

## 8. DeepSeek API

### [Models & Pricing — DeepSeek API Docs](https://api-docs.deepseek.com/quick_start/pricing/) (font oficial)
- API compatible amb el format **OpenAI Chat Completions** i amb el format **Anthropic Messages** (canvi d'endpoint base + 1-2 línies de codi per migrar des de qualsevol dels dos SDKs).
- Suporta: streaming, tool calling, **JSON mode** (sortida estructurada garantida), thinking/non-thinking modes, context llarg.
- **Avís de deprecació:** els noms de model `deepseek-chat` i `deepseek-reasoner` es deprequen el 2026-07-24; a partir d'ara cal usar `deepseek-v4-flash` (mode no-thinking / thinking respectivament). **El brief fa servir `deepseek-v4-pro` i `deepseek-v4-flash` als exemples de `.env`, que ja són noms vàlids post-migració.**
- El JSON mode no altera el preu — es paga la mateixa tarifa per token que una crida normal.

**Implicació pel `prompt_builder.py` / `deepseek_client.py`:** com que l'API és compatible amb el format OpenAI, es pot construir amb l'SDK oficial `openai` (Python) canviant `base_url` a `https://api.deepseek.com`, o amb `httpx`/`requests` directe. El JSON mode s'ha de fer servir per obtenir el format de resposta estructurat que demana el brief (secció 11: `translation`, `confidence`, `issues`, `terminology_used`).

---

## 9. WP-CLI i WPML

### Recerca: "WP-CLI WPML commands"
**Conclusió:** WPML **no publica un paquet WP-CLI oficial propi** (no hi ha `wp wpml ...`). Els comandaments WP-CLI relacionats amb idiomes (`wp language`, `wp site switch-language`) són del core de WordPress, no de WPML. Alguns usuaris reporten que cal l'opció `--url=` per fer que WP-CLI operi correctament en un lloc amb WPML actiu (per evitar que faci servir només l'idioma per defecte).

**Implicació:** l'automatització d'escriptura de traduccions WPML des de fora de la petició HTTP normal de WordPress s'ha de fer via (a) un endpoint REST personalitzat propi que embolcalli els hooks PHP, o (b) `wp eval-file` / `wp eval` cridant una funció pròpia que faci servir els hooks — no hi ha una drecera WP-CLI nativa de WPML.

---

## 11. WPML — Proveïdor de traducció natiu (Translation Proxy) vs. traductor local + XLIFF

> Investigació feta el 2026-08-04 arran de la pregunta del client sobre si DeepSeek es pot integrar com a "proveïdor de traducció natiu de WPML" en lloc del bridge d'hooks pur.

### [How Translation Service Integration with WPML Works](https://wpml.org/documentation/content-translation/how-integration-with-wpml-works/) (font oficial)
El "Translation Proxy" és el mecanisme intern que fa d'intermediari entre WPML i un servei de traducció professional: el contingut surt de WordPress com a fitxers XLIFF cap al proxy, i d'aquest cap als servidors del servei de traducció.

### [custom translation service — WPML forums](https://wpml.org/forums/topic/custom-translation-service/)
Es pot apuntar a una API de Translation Proxy pròpia des de `wp-config.php` (implementant l'API JSON del Translation Proxy de WPML), però **WPML confirma que no té previst fer disponibles serveis de traducció personalitzats fora del Translation Partners Program**. Fins i tot configurant-ho manualment, el servei personalitzat **no apareix** a `WPML → Translation Dashboard → Translation Services`.

### [WPML's Translation Hub](https://wpml.org/documentation/content-translation/translation-hub/)
Via alternativa "Instant Integration" pensada per a agències/serveis de traducció que volen gestionar clients i connectar-se sense desenvolupament (Activation Key + API Token). Pensada per a un negoci de traducció que dona servei a tercers, no per a una integració interna d'una sola web.

**Conclusió (Translation Partners Program):** el Translation Partners Program és gratuit per unir-s'hi, però requereix integració activa i un mínim de 5 projectes de traducció completats, i implica aparèixer públicament al directori de WPML. **Excessiu i no adequat per a l'ús intern d'una sola web (precision-gnss.com).** Es descarta com a via per a aquest projecte.

### [Using XLIFF Files in WPML](https://wpml.org/documentation/translating-your-contents/using-desktop-cat-tools/configuring-xliff-file-options/) i fòrums relacionats (font oficial + comunitat)
- Assignar un usuari com a **"traductor local"** (`WPML → Translation Management → Translators`) és una funció estàndard del pla CMS/Agency, **sense cap requisit de partnership**.
- L'exportació/importació d'XLIFF de jobs (`WPML → Translations → Import/Export XLIFF`) és una **funció d'admin basada en pujada/descàrrega manual de fitxer** — no hi ha una API REST o hook oficialment documentat per automatitzar-la des de fora de WordPress. Automatitzar-la simulant peticions al formulari d'admin seria fràgil (no professional, sense garanties d'estabilitat entre versions).
- Per a integracions de codi a mida, la pròpia comunitat/documentació de WPML recomana **treballar amb el fitxer XLIFF que WPML genera per segmentar el contingut i reinserir el contingut traduït usant els hooks oficials** (`wpml_set_element_language_details`, els mateixos de la secció 2) — és a dir, la via robusta per a un cas com aquest **convergeix amb el bridge d'hooks ja dissenyat**, afegint-hi la capa de "jobs"/XLIFF només per aconseguir seguiment natiu al dashboard de WPML.

**Decisió arquitectònica derivada (veure `MEMORIA.md`, entrada 2026-08-04):** no es persegueix el Translation Proxy/Partner Program. S'amplia el mateix `gnss-bridge` (mu-plugin ja dissenyat a FASE 1) amb endpoints propis que criden **directament les funcions internes de WPML** que ja fan la creació de jobs i l'exportació/importació d'XLIFF (les mateixes que usa la UI d'admin), en lloc d'automatitzar la pujada de fitxers via UI. Els noms exactes d'aquestes funcions/classes PHP s'han de confirmar quan WPML estigui instal·lat (Fase 0), inspeccionant el codi del plugin `wpml-translation-management`.

---

## 10. Resum de decisions arquitectòniques derivades de la investigació

| Pregunta | Resposta trobada | Font |
|---|---|---|
| Es pot escriure a `icl_translations` amb SQL directe? | Desaconsellat oficialment; risc d'inconsistència (`trid` compartit entre taules, `icl_translation_status`, cache d'objectes de WP) | §1, §2 |
| Quina és la via suportada per crear traduccions? | Hooks PHP (`wpml_set_element_language_details` + `wpml_element_language_details` + `wpml_element_type`), executats dins WordPress | §2 |
| Hi ha REST API pública de WPML per crear traduccions? | No: `wpml/tm/v1` i `wpml/st/v1` són interns de l'ATE, no un CRUD de traduccions per a tercers | §3 |
| Cal parsejar el JSON d'Elementor a mà? | Parcialment innecessari: WPML CMS/Agency (el pla contractat, $99/any) ja tradueix Elementor nativament si `_elementor_data` es declara a `wpml-config.xml` | §4 |
| Es pot escriure meta de Yoast via REST API estàndard? | No per defecte — cal `register_post_meta()` en un mu-plugin | §6 |
| Hi ha WP-CLI oficial de WPML? | No | §9 |
| Quin format ha de fer servir el client DeepSeek? | JSON mode, compatible OpenAI SDK, `base_url` personalitzat | §8 |

**Conclusió general:** el disseny "pur REST API des de Python" del brief xoca amb el fet que la creació/vinculació de traduccions WPML només és suportada des de dins de WordPress (PHP). Això obliga a un **component pont** (mu-plugin o plugin propi lleuger) instal·lat a precision-gnss.com, que exposi:
1. Endpoints REST personalitzats (protegits amb Application Passwords) que embolcallin els hooks WPML per crear/vincular traduccions.
2. `register_post_meta()` per als camps Yoast que calgui escriure.
3. Un `wpml-config.xml` que declari `_elementor_data` i els camps de Yoast/ACF rellevants.

Aquest component es documenta com a nova peça a l'arquitectura dins `ROADMAP.md` (FASE 2/8) i es detalla a `PLA-ACCIO.md`.
