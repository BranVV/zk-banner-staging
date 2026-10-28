# Формат на файла със задача

Един файл = една книга на един пазар. Име на файла: `КНИГА_ПАЗАР_ДАТА.json`,
например `RSEXCEL_RS_2026-10-28.json`.

Качването на такъв файл в `jobs/` пуска обработката автоматично.

```jsonc
{
  "book": "RSEXCEL",                  // код на книгата, както е в ZK_Campaign_Catalog
  "market": "RS",                     // RS | HR | BA | RO
  "date": "2026-10-28",               // по избор; по подразбиране днес
  "source_campaign": "…",             // по избор, за проследимост
  "source_account": "Zlaten Kluch 3", // по избор

  "defaults": {                       // важи за всички банери, презаписва се от банера
    "mode": "model",                  // model | overlay
    "output_format": "png",           // png | jpg
    "quality": "high",
    "input_fidelity": "high",
    "fit": "stretch",                 // stretch | pad
    "cover": "covers/RSEXCEL_RS_cover.png",
    "keep_as_is": ["MS Excel", "EPP"]
  },

  "banners": [
    {
      "source": "source/RSEXCEL/BGEXCEL_BG_banner_bolka.jpg",
      "format": "banner",             // banner | video-thumb | story | carousel …
      "angle": "bolka",               // една-две думи за ъгъла
      "translations": [
        { "source": "Научи Excel за 30 дни", "target": "Naučite Excel za 30 dana" },
        { "source": "Само днес: 49 лв.",     "target": "Samo danas: 2.490 RSD",
          "note": "цена и валута по ценовата листа за RS" }
      ]
    },
    {
      "source": "source/RSEXCEL/BGEXCEL_BG_banner_otziv.jpg",
      "format": "banner",
      "angle": "otziv",
      "mode": "overlay",
      "text_boxes": [
        {
          "box": [80, 620, 1000, 760],
          "text": "Naučite Excel za 30 dana",
          "font": "Montserrat-Bold.ttf",
          "colour": [255, 255, 255],
          "align": "center",
          "erase_with": [12, 70, 48],
          "max_font_size": 72,
          "min_font_size": 28
        }
      ]
    }
  ]
}
```

## Полета

| поле | режим | какво е |
|---|---|---|
| `source` | и двата | път до изходния банер, спрямо корена на репото |
| `format` | и двата | втората част от името на файла след пазара |
| `angle` | и двата | една-две думи за ъгъла; по подразбиране името на изходния файл |
| `mode` | — | `model` (пре-генериране от OpenAI) или `overlay` (нарисуване с Pillow) |
| `cover` | model | локализирана корица, подава се като референтно изображение |
| `references` | model | още референтни изображения |
| `translations` | model | двойки оригинал → превод; влизат дословно в промпта |
| `keep_as_is` | model | текстове, които остават непреведени |
| `extra_rules` | model | допълнителни правила към промпта |
| `prompt` | model | пълен промпт, който замества вградения |
| `fit` | model | `stretch` (по подразбиране) или `pad` при различно съотношение |
| `api_size` | model | ръчно: `1024x1024`, `1536x1024`, `1024x1536` |
| `text_boxes` | overlay | кутии с координати `[left, top, right, bottom]` и текст |

## Режими

**`model`** — целият банер минава през `gpt-image-1` с `input_fidelity: high`.
Ползва се, когато текстът е върху снимка или когато няма плоска локализирана
корица. Ако `cover` е зададен, моделът подменя корицата в банера с нея.

**`overlay`** — текстът се нарисува програмно върху оригинала. Корицата и
снимките остават едно към едно. Иска координати на кутиите, затова се ползва за
банери с текст върху плътен фон.

## Езици

| пазар | език | бележка |
|---|---|---|
| RS | сръбски | **латиница**, не кирилица |
| HR | хърватски | общ превод с BA |
| BA | босненски | общ превод с HR |
| RO | румънски | отделен превод |
