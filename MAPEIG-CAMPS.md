# Mapeig de camps de WordPress — què gestiona el motor i què falta

> Resposta a la pregunta de l'usuari (2026-07-24): "el sistema ha de poder mapejar tots els camps de WordPress involucrats... ja els tens tots detectats? Per posts, pàgines i productes de WordPress i WooCommerce?"
>
> **Resposta curta: no els teníem tots mapejats el 2026-07-24, però ja sí (2026-07-24, més tard la mateixa sessió).** El motor gestiona ara títol, cos, excerpt, tots els camps traduïbles de Yoast (title/description/og_title/og_description), imatge destacada (alt/caption) i categories/etiquetes, per a posts, pages **i productes WooCommerce** (secció 6). Aquest document és el resultat d'una auditoria real i completa contra `staging.precision-gnss.com` (via REST API).

---

## 1. Posts i Pages — camps natius de WordPress

Auditat contra `wp-json/wp/v2/pages/4309` (Precision Agriculture) i `wp-json/wp/v2/posts/5485` (RTK GNSS for Robotics).

| Camp | Contingut traduïble? | Gestionat pel motor actualment | Notes |
|---|---|---|---|
| `title.rendered` | ✅ Sí | ✅ Sí (`content_extractor.py`) | — |
| `content.rendered` | ✅ Sí | ✅ Sí (`html_parser.py`) | Headings, paràgrafs, llistes, cites, botons, alt text d'imatges inserides al cos |
| `excerpt.rendered` | ✅ Sí | ✅ Sí *(2026-07-24)* | Provat contra dades reals de l'staging |
| `meta` (custom fields) | Depèn | ✅ Parcial | Buit per defecte (`{"footnotes": ""}`) — cap custom field ACF en aquest lloc (confirmat, no hi ha ACF instal·lat) |
| `featured_media` (ID) | Indirecte | ✅ Sí *(2026-07-24)* | `extract_page_content()` accepta ara un paràmetre opcional `featured_media` (dict ja obtingut de `/wp-json/wp/v2/media/{id}`) — extreu `alt_text` i `caption`. L'extracció segueix sent pura (sense I/O): **qui crida ha de fer la crida a l'endpoint de media i passar-li el resultat.** |
| `categories` / `tags` (només posts) | ✅ Sí (nom + descripció del terme) | ✅ Sí *(2026-07-24)* | Paràmetres opcionals `categories`/`tags` (llistes de termes ja resolts), reutilitzant `extract_taxonomy_terms()`. Provat amb dades reals: cal que qui crida filtri només els termes assignats al post concret (`post["categories"]` dona només IDs; cal resoldre'ls contra `/wp-json/wp/v2/categories`). |
| `author`, `date`, `slug`, `status`, `template`, `comment_status` | ❌ No | — | Metadades tècniques/administratives, mai traduïbles |

## 2. Yoast SEO — tots els camps de `yoast_head_json`

Fins ara només fèiem servir `title` i `description`. L'auditoria mostra **9 camps** en total:

| Camp | Traduïble? | Gestionat actualment | Notes |
|---|---|---|---|
| `title` | ✅ Sí | ✅ Sí | — |
| `description` | ✅ Sí | ✅ Sí | — |
| `og_title` | ✅ Sí | ✅ Sí *(2026-07-24)* | Títol per a xarxes socials (Facebook/LinkedIn). Sovint idèntic a `title` per defecte, però es pot configurar diferent a Yoast. |
| `og_description` | ✅ Sí | ✅ Sí *(2026-07-24)* | Descripció per a xarxes socials. Mateixa observació. |
| `robots` | ❌ No | — | Directives tècniques (`index, follow`, etc.) |
| `og_locale`, `og_type`, `og_url`, `og_site_name` | ❌ No | — | Metadades tècniques/URLs |
| `twitter_card` | ❌ No | — | Només un identificador de tipus (`summary_large_image`), no text |
| `article_modified_time` | ❌ No | — | Data |
| `schema` (JSON-LD structured data) | ⚠️ Derivat | N/A | Conté `name`/`description` **duplicats** del títol/meta description — es genera dinàmicament per Yoast a partir d'aquests, no és una font pròpia. Un cop `title`/`description` estan traduïts i WPML serveix la versió ES, Yoast regenera aquest bloc automàticament. **No cal gestionar-lo per separat.** |

**Confirmat de nou (ja sabíem):** cap d'aquests camps és escrivible via REST per defecte — calen `register_post_meta()` al mu-plugin `gnss-bridge` per als camps `_yoast_wpseo_*` subjacents (lectura via `yoast_head_json` ja funciona, escriptura no).

## 3. Taxonomies — categories i etiquetes (només `post`, no `page`)

| Element | Traduïble? | Gestionat actualment |
|---|---|---|
| Nom del terme (p. ex. "RTK Applications", "News") | ✅ Sí | ✅ Sí *(2026-07-24)* |
| Descripció del terme | ✅ Sí (si n'hi ha; buides en aquest lloc) | ✅ Sí *(2026-07-24)* |

4 categories reals detectades: `news`, `quick-start`, `rtk-applications`, `uncategorized`. `pages` no tenen taxonomies pròpies (`wp-json/wp/v2/types` confirma `taxonomies: []` per a `page`).

**Prioritat:** baixa/mitjana — són elements estructurals/de navegació, no contingut editorial extens, però haurien d'estar traduïts perquè els menús/arxius en ES tinguin sentit.

## 4. Media (imatges) — camps de la mediateca

Auditat contra `wp-json/wp/v2/media`.

| Camp | Traduïble? | Gestionat actualment | Notes |
|---|---|---|---|
| `alt_text` | ✅ Sí | ✅ Sí | Al cos (via `html_parser.py`) i a la imatge destacada (via el paràmetre opcional `featured_media`, *2026-07-24*) |
| `caption.rendered` | ✅ Sí | ✅ Parcial *(2026-07-24)* | Capturat per a la imatge destacada; les imatges dins del cos no porten peu de foto en HTML estàndard (només `alt`) |
| `title.rendered` | ⚠️ Rarament visible | ❌ **No** | Títol intern de l'arxiu, gairebé mai visible al públic — prioritat baixa |
| `description.rendered` | ⚠️ Rarament visible | ❌ **No** | Descripció interna de l'arxiu — prioritat baixa |

## 5. Elementor — `_elementor_data`

Ja documentat a `AUDITORIA-INICIAL.md` §0.5 i confirmat de nou en aquesta auditoria: **no s'exposa via REST per defecte**. El nostre `html_parser.py` treballa sobre l'HTML ja renderitzat (que Elementor mateix genera), no sobre el JSON cru — per això capturem el contingut visible igualment, però **no captura configuracions no renderitzades com a text** (per exemple, un atribut `title` d'un botó que no es mostra al DOM, si n'hi hagués).

## 6. WooCommerce / Productes — **implementat de forma genèrica (2026-07-24), pendent de validació real**

Confirmat a `AUDITORIA-INICIAL.md`: **cap plugin de WooCommerce instal·lat, cap post type `product`** a `precision-gnss.com`. A petició explícita de l'usuari ("s'ha d'implementar per a altres WordPress amb WooCommerce"), aquesta secció ja **té codi funcional** (`app/extraction/woocommerce_extractor.py`), pensat per funcionar amb **qualsevol** WordPress+WooCommerce, no només un lloc concret. Com que no hi ha cap lloc real amb WooCommerce dins l'abast actual, **el codi s'ha provat amb dades sintètiques fidels a l'esquema oficial** (`wp-json/wc/v3/products`), no contra un lloc real — es marca per a validació empírica quan n'hi hagi un de disponible (p. ex. una futura versió per a ArduSimple.com — veure `MEMORIA.md`).

### 6.1 Contingut principal del producte

| Camp | Traduïble? | Correspon a |
|---|---|---|
| `name` | ✅ Sí | Títol del producte |
| `description` | ✅ Sí | **Tab "Description"** — contingut llarg en HTML (WYSIWYG), sovint amb imatges/taules incrustades |
| `short_description` | ✅ Sí | Resum breu que apareix al costat del botó "Afegir a la cistella" |
| `purchase_note` | ✅ Sí | Text mostrat després de completar la compra (p. ex. instruccions de descàrrega/activació) |
| `menu_order` | ❌ No | Ordre de visualització, no textual |

### 6.2 Tabs de la fitxa de producte (plantilla estàndard de WooCommerce)

WooCommerce mostra per defecte 2-3 pestanyes a la fitxa; una quarta és habitual amb plugins:

| Tab | Origen del contingut | Traduïble? |
|---|---|---|
| **Description** | Camp `description` (§6.1) | ✅ Sí — ja cobert si es tradueix `description` |
| **Additional information** | **Generada automàticament** per WooCommerce a partir de `attributes[]` (mida, pes, dimensions) i dels atributs personalitzats (Color, Voltatge, etc.) | ✅ Sí, però indirecte — cal traduir els **noms i valors dels atributs** (§6.3), no aquest "tab" en si, que és només una taula auto-generada |
| **Reviews** | Contingut generat pels usuaris (ressenyes/valoracions) | ⚠️ **Normalment fora d'abast** — és contingut de tercers, no editorial del propietari del lloc; traduir-lo automàticament seria qüestionable (canviaria paraules d'un client real). Es recomana **no traduir-lo automàticament**; si es vol, seria un flux completament separat amb consideracions ètiques pròpies. |
| **Tabs personalitzats** (afegits per tema/plugin, p. ex. "Especificacions tècniques", "Descàrregues") | Normalment `meta_data` propi del plugin que afegeix el tab — **no formen part de l'esquema estàndard de WooCommerce** | ✅ Sí, però **cal inventariar-los al lloc real** quan existeixi, perquè cada plugin guarda el contingut d'una manera diferent (custom meta key, shortcode, camp ACF...) |

### 6.3 Atributs i variants (productes variables — p. ex. "Color: Vermell / Blau", "Mida: S / M / L")

| Camp | Traduïble? | Notes |
|---|---|---|
| `attributes[].name` | ✅ Sí | Nom de l'atribut (p. ex. "Color", "Longitud del cable") |
| `attributes[].options[]` | ✅ Sí | Valors de l'atribut (p. ex. "Vermell", "1.5 m") — **sensible**: si l'atribut és un "atribut global" (`pa_color`, gestionat com a taxonomia pròpia `product_attribute`), el valor es tradueix com un terme de taxonomia (secció 3), no com a text lliure dins del producte |
| `variations[].description` | ✅ Sí | Cada variant pot tenir la seva pròpia descripció (poc habitual però possible) |
| `variations[].sku`, `.price`, `.stock_quantity` | ❌ No | Igual que al producte pare — mai traduïbles |

### 6.4 Categories, etiquetes i taxonomies pròpies

| Element | Traduïble? |
|---|---|
| `categories[].name` / `.description` | ✅ Sí (mateix mecanisme que §3, però és la taxonomia `product_cat`) |
| `tags[].name` | ✅ Sí (`product_tag`) |
| Taxonomies personalitzades (p. ex. "Marca" / `product_brand`, habitual amb plugins de marca) | ✅ Sí, si n'hi ha — cal inventariar-les al lloc real |

### 6.5 Imatges del producte

| Camp | Traduïble? |
|---|---|
| `images[].alt` (imatge destacada + galeria sencera) | ✅ Sí — mateix mecanisme que §4 (media), però un producte sol tenir **diverses** imatges de galeria, no només una destacada |

### 6.6 SEO

Idèntic a §2 (Yoast): els productes són `post_type=product` per sota, així que Yoast els tracta igual (`title`, `description`, `og_title`, `og_description`, `schema` derivat).

### 6.7 Camps que **mai** s'han de traduir (contingut protegit)

`sku`, `price`, `regular_price`, `sale_price`, `stock_quantity`, `stock_status`, `weight`, `dimensions` (length/width/height), `download_url` dels fitxers descarregables, `variations[].sku`/`.price`. El **nom** d'un fitxer descarregable (`downloads[].name`, l'etiqueta que veu l'usuari, p. ex. "Manual d'usuari (PDF)") sí és traduïble; la seva URL no.

### 6.8 Estat d'implementació

| Camp/element | Gestionat pel motor | Fitxer |
|---|---|---|
| `name`, `description`, `short_description`, `purchase_note` | ✅ Sí (`extract_product_content()`) | `app/extraction/woocommerce_extractor.py` |
| `attributes[].name` / `.options[]` | ✅ Sí | íd. |
| `images[].alt` (galeria sencera) | ✅ Sí | íd. |
| `categories[].name`/`.description`, `tags[].name` | ✅ Sí (via `extract_taxonomy_terms()`, genèric i reutilitzat) | `app/extraction/taxonomy_extractor.py` |
| SEO (Yoast) | ✅ Sí (via `extract_yoast_blocks()`, genèric i reutilitzat amb posts/pages) | `app/extraction/seo_extractor.py` |
| Tabs personalitzats de plugins | ❌ No — impossible de fer genèric sense un lloc real per inventariar-los | — |
| `variations[].description` per variant | ❌ No — cas rar, s'afegirà si un lloc real ho necessita | — |
| Reviews/ressenyes d'usuaris | ❌ **Explícitament fora d'abast** (contingut de tercers) | — |
| Camps mai traduïbles (SKU, preus, estoc...) | ✅ Mai extrets (provat amb test dedicat) | — |

**Provat amb 10 tests** i dades sintètiques fidels a l'esquema oficial (`tests/extraction/test_woocommerce_extractor.py`) — **no encara amb un lloc WooCommerce real**, ja que cap n'hi ha dins l'abast actual. Es marca per a validació empírica quan n'hi hagi un de disponible.

---

## Estat final (2026-07-24) — totes les accions de FASE 3 completades

| Acció | Fitxer | Estat |
|---|---|---|
| `excerpt.rendered` | `app/extraction/content_extractor.py` | ✅ Fet |
| `og_title`/`og_description` de Yoast | `app/extraction/seo_extractor.py` | ✅ Fet (compartit amb WooCommerce) |
| Alt/caption de la imatge destacada | `app/extraction/content_extractor.py` (paràmetre opcional `featured_media`) | ✅ Fet |
| Nom/descripció de categories i etiquetes | `app/extraction/content_extractor.py` (paràmetres opcionals `categories`/`tags`) | ✅ Fet |
| WooCommerce (productes) | `app/extraction/woocommerce_extractor.py` | ✅ Fet, pendent validació real |

**Nota d'arquitectura important:** `extract_page_content()` es manté **pur i sense I/O** — `featured_media`/`categories`/`tags` són paràmetres opcionals que **qui crida** ha d'obtenir per separat (crides a `/wp-json/wp/v2/media/{id}` i `/wp-json/wp/v2/categories`/`tags`) i passar-hi ja resolts. Encara **no hi ha cap orquestrador** que faci aquestes crides automàticament — això és feina de FASE 8, bloquejada per WPML.

Tot **provat contra dades reals de l'staging** (no només amb dades sintètiques): la pàgina "Precision Agriculture" (171 blocs amb excerpt+og+categories) i el post "RTK GNSS for Robotics" (78 blocs, amb la categoria "News" correctament filtrada als termes assignats).
