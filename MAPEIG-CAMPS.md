# Mapeig de camps de WordPress — què gestiona el motor i què falta

> Resposta a la pregunta de l'usuari (2026-07-24): "el sistema ha de poder mapejar tots els camps de WordPress involucrats... ja els tens tots detectats? Per posts, pàgines i productes de WordPress i WooCommerce?"
>
> **Resposta curta: no, encara no els teníem tots mapejats.** Fins ara el motor només gestionava títol, cos i 2 camps de Yoast (title/description). Aquest document és el resultat d'una auditoria real i completa contra `staging.precision-gnss.com` (via REST API) fet per tancar aquest buit. **No hi ha WooCommerce/productes en aquest lloc** (confirmat a `AUDITORIA-INICIAL.md` §0.2) — la secció corresponent explica què caldria si mai s'aplica a un lloc que sí en tingui (p. ex. una futura versió per ArduSimple).

---

## 1. Posts i Pages — camps natius de WordPress

Auditat contra `wp-json/wp/v2/pages/4309` (Precision Agriculture) i `wp-json/wp/v2/posts/5485` (RTK GNSS for Robotics).

| Camp | Contingut traduïble? | Gestionat pel motor actualment | Notes |
|---|---|---|---|
| `title.rendered` | ✅ Sí | ✅ Sí (`content_extractor.py`) | — |
| `content.rendered` | ✅ Sí | ✅ Sí (`html_parser.py`) | Headings, paràgrafs, llistes, cites, botons, alt text d'imatges inserides al cos |
| `excerpt.rendered` | ✅ Sí | ❌ **No** | Existeix i té contingut (sovint auto-generat del cos, però pot ser manual i diferent). **Falta afegir-lo a `content_extractor.py`.** |
| `meta` (custom fields) | Depèn | ✅ Parcial | Buit per defecte (`{"footnotes": ""}`) — cap custom field ACF en aquest lloc (confirmat, no hi ha ACF instal·lat) |
| `featured_media` (ID) | Indirecte | ❌ **No** | És només un ID; cal una crida a `/wp-json/wp/v2/media/{id}` per obtenir `alt_text`/`caption`/`title`/`description` de la imatge destacada |
| `categories` / `tags` (només posts) | ✅ Sí (nom + descripció del terme) | ❌ **No** | Veure secció 3 |
| `author`, `date`, `slug`, `status`, `template`, `comment_status` | ❌ No | — | Metadades tècniques/administratives, mai traduïbles |

## 2. Yoast SEO — tots els camps de `yoast_head_json`

Fins ara només fèiem servir `title` i `description`. L'auditoria mostra **9 camps** en total:

| Camp | Traduïble? | Gestionat actualment | Notes |
|---|---|---|---|
| `title` | ✅ Sí | ✅ Sí | — |
| `description` | ✅ Sí | ✅ Sí | — |
| `og_title` | ✅ Sí | ❌ **No** | Títol per a xarxes socials (Facebook/LinkedIn). Sovint idèntic a `title` per defecte, però es pot configurar diferent a Yoast. |
| `og_description` | ✅ Sí | ❌ **No** | Descripció per a xarxes socials. Mateixa observació. |
| `robots` | ❌ No | — | Directives tècniques (`index, follow`, etc.) |
| `og_locale`, `og_type`, `og_url`, `og_site_name` | ❌ No | — | Metadades tècniques/URLs |
| `twitter_card` | ❌ No | — | Només un identificador de tipus (`summary_large_image`), no text |
| `article_modified_time` | ❌ No | — | Data |
| `schema` (JSON-LD structured data) | ⚠️ Derivat | N/A | Conté `name`/`description` **duplicats** del títol/meta description — es genera dinàmicament per Yoast a partir d'aquests, no és una font pròpia. Un cop `title`/`description` estan traduïts i WPML serveix la versió ES, Yoast regenera aquest bloc automàticament. **No cal gestionar-lo per separat.** |

**Confirmat de nou (ja sabíem):** cap d'aquests camps és escrivible via REST per defecte — calen `register_post_meta()` al mu-plugin `gnss-bridge` per als camps `_yoast_wpseo_*` subjacents (lectura via `yoast_head_json` ja funciona, escriptura no).

## 3. Taxonomies — categories i etiquetes (només `post`, no `page`)

| Element | Traduïble? | Gestionat actualment |
|---|---|---|
| Nom del terme (p. ex. "RTK Applications", "News") | ✅ Sí | ❌ **No** |
| Descripció del terme | ✅ Sí (si n'hi ha; buides en aquest lloc) | ❌ **No** |

4 categories reals detectades: `news`, `quick-start`, `rtk-applications`, `uncategorized`. `pages` no tenen taxonomies pròpies (`wp-json/wp/v2/types` confirma `taxonomies: []` per a `page`).

**Prioritat:** baixa/mitjana — són elements estructurals/de navegació, no contingut editorial extens, però haurien d'estar traduïts perquè els menús/arxius en ES tinguin sentit.

## 4. Media (imatges) — camps de la mediateca

Auditat contra `wp-json/wp/v2/media`.

| Camp | Traduïble? | Gestionat actualment | Notes |
|---|---|---|---|
| `alt_text` | ✅ Sí | ⚠️ **Parcial** | Ja el capturem **quan la imatge està inserida al cos** (l'HTML renderitzat inclou `<img alt="...">` i `html_parser.py` ja ho extreu). **NO el capturem** per a la imatge destacada (`featured_media`), que no apareix al cos renderitzat. |
| `caption.rendered` | ✅ Sí | ❌ **No** | Peu de foto — no capturat encara (poques imatges en tenen, però cal preveure-ho) |
| `title.rendered` | ⚠️ Rarament visible | ❌ **No** | Títol intern de l'arxiu, gairebé mai visible al públic — prioritat baixa |
| `description.rendered` | ⚠️ Rarament visible | ❌ **No** | Descripció interna de l'arxiu — prioritat baixa |

## 5. Elementor — `_elementor_data`

Ja documentat a `AUDITORIA-INICIAL.md` §0.5 i confirmat de nou en aquesta auditoria: **no s'exposa via REST per defecte**. El nostre `html_parser.py` treballa sobre l'HTML ja renderitzat (que Elementor mateix genera), no sobre el JSON cru — per això capturem el contingut visible igualment, però **no captura configuracions no renderitzades com a text** (per exemple, un atribut `title` d'un botó que no es mostra al DOM, si n'hi hagués).

## 6. WooCommerce / Productes — **no aplicable en aquest lloc, però mapejat sencer per si cal**

Confirmat a `AUDITORIA-INICIAL.md`: **cap plugin de WooCommerce instal·lat, cap post type `product`** a `precision-gnss.com`. Com que no hi ha cap lloc real amb WooCommerce dins l'abast actual, **aquesta secció no s'ha pogut auditar empíricament** (a diferència de les seccions 1-5, fetes contra dades reals) — es basa en l'esquema oficial i estable de l'API REST de WooCommerce (`wp-json/wc/v3/products`, diferent de `wp/v2`). Es documenta sencer ara perquè, si el projecte s'estén mai a un lloc amb botiga (p. ex. una futura versió per a ArduSimple.com — veure `MEMORIA.md`), no calgui redescobrir-ho.

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

### 6.8 Resum de prioritats (si mai s'implementa)

| Prioritat | Camps |
|---|---|
| Alta | `name`, `description`, `short_description`, `attributes` (noms i valors), imatges (alt) |
| Mitjana | `purchase_note`, categories/etiquetes/marca, SEO (igual que posts/pages) |
| Baixa / cas per cas | Tabs personalitzats (cal inventariar-los al lloc real primer) |
| **Explícitament fora d'abast** | Reviews/ressenyes d'usuaris |

Aquesta secció sencera es reprendrà **només si el projecte s'amplia formalment a un lloc amb WooCommerce** (fora d'abast actual, confirmat a `MEMORIA.md`) — en aquell moment caldrà **validar-la empíricament** contra el lloc real, igual que s'ha fet amb les seccions 1-5 aquí.

---

## Resum — accions pendents per a la propera iteració de FASE 3

| Acció | Fitxer | Prioritat |
|---|---|---|
| Afegir `excerpt.rendered` a l'extracció | `app/extraction/content_extractor.py` | Alta — és contingut visible real |
| Afegir `og_title`/`og_description` de Yoast | `app/extraction/content_extractor.py` | Mitjana — sovint duplicat de title/description, però no sempre |
| Afegir alt/caption de la imatge destacada (`featured_media`) | `app/extraction/content_extractor.py` + nova crida a `get_media()` | Mitjana |
| Afegir nom/descripció de categories i etiquetes | Nou: `app/wordpress/taxonomies.py` + extractor | Baixa/mitjana |
| Camps de WooCommerce | — | **Fora d'abast** fins que s'ampliï el projecte |

Aquestes accions **no depenen de WPML** i es poden fer en qualsevol moment. Es proposaran com a properes tasques si l'usuari ho confirma.
