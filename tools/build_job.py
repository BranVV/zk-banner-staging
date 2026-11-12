#!/usr/bin/env python3
"""build_job.py - сглобява job JSON за нови банери (процес нови статични криейтиви, Стъпка 4).

Всеки промпт се сглобява САМО оттук, за да влизат задължителните правила винаги,
независимо от книгата или банера (решение на Bran 11.11.2026 - забележките да не се повтарят).

Употреба:
  python3 tools/build_job.py spec.json            # пише jobs/<BOOK>_<MARKET>_<DATE>[-suffix].json
  python3 tools/build_job.py spec.json --print    # само показва промптовете

spec.json:
{
  "book": "EXCEL", "market": "BG", "date": "2026-11-11", "suffix": "",      # suffix напр. "fix"
  "book_title": "MS Excel Експерт",
  "cover": "covers/EXCEL_BG_cover.png",
  "source_campaign": "CBO | EXCEL | INT | 50+ BANNERS - ...",
  "setting": "The setting is ... The people are ...",     # общ за всички банери (може и празен)
  "banners": [
    {"angle": "01-ugly-mladite", "format": "UGLY", "ref": "source/EXCEL/ref_EXCEL_ugly.jpg",
     "layout": "0-15% only background. 16-34% the headline. ...",
     "scene": "...", "text": "1) Headline ...\n2) CTA button: \"НАУЧИ EXCEL →\"",
     "book": "none" | "lying" | "held" | "standing",     # как е книгата (none = без корица)
     "format_note": "по желание - допълнение към описанието на формата",
     "setting": "по желание - замества общия setting",
     "crop_y": 0}
  ]
}

Задължителни блокове (винаги): SAFE ZONE + COMPOSITION, FORMAT по рецептата от banner_formats
(tools/banner_formats.json, износ от Creatives DB), SCREEN ORIENTATION, TYPOGRAPHY, PHOTO STYLE,
BOOK REALISM (за lying/held/standing), NO FAKE UI (12.11.2026, Spam - deceptive link), REVIEW правила (фон и подпис), POSITION CHECK, NO EXTRA TEXT.
Формат извън banner_formats се маркира като EXPERIMENT.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

HEAD = ("Create a NEW, finished Facebook/Instagram feed advertising banner for a Bulgarian audience, from scratch.\n"
        "IMAGE 1 is only a blank grey canvas used for size: ignore its content completely. The photo/background must fill the WHOLE frame edge to edge (no bars, no borders, no frames).\n"
        "LAYOUT SAFE ZONE (critical): the top 14% and the bottom 14% of the frame will be cut off afterwards. Put NOTHING important there - only continuation of the background. "
        "ALL text lines, faces, the book and the CTA button must be inside the middle 72% of the frame height. Keep about 6% side margins for text.\n"
        "COMPOSITION NOTE: frame the shot wide enough that there is calm empty background above the headline and below the CTA button. "
        "The headline starts around 18-20% from the top; the CTA button sits around 80-86% and is fully visible with space under it.\n")

SCREEN = ("SCREEN ORIENTATION (critical): every phone, laptop and monitor screen faces the person who uses it. We never see a screen from the front "
          "while the person sits or stands behind it. If the screen content must be visible, the camera is behind or beside the person "
          "(over-the-shoulder or side view), so we see the person and the screen together; otherwise we see only the back of the phone, laptop lid or monitor.\n")

TYPO = ("TYPOGRAPHY RULES (critical):\n"
        "- All text is Bulgarian Cyrillic. Render every text line EXACTLY as given, character by character, including punctuation and quotation marks. Do not translate, correct, shorten, re-order or add any words.\n"
        "- Use a heavy, clean, condensed sans-serif for headlines (like Oswald Bold / Bebas-style weight but with full Cyrillic), unless the format below says otherwise.\n"
        "- Text must be large and clearly legible on a phone at 380px width: headline lines at least ~6% of the banner height, subheadline ~3.5%, CTA text ~3.5%. Keep generous side margins (about 6% of the width).\n"
        "- Strong contrast only: white or near-black text; accent words in warm yellow #F5C518; no grey text on dark backgrounds.\n"
        "- CTA = rounded pill button in vivid red #E8232A with bold white uppercase text and an arrow →, centred near the bottom of the central area.\n"
        "- No other text, logos, watermarks, prices of the book, percentages or website addresses anywhere.\n\n")

PHOTO = ("PHOTO STYLE: realistic, natural-looking photo like a real Bulgarian everyday scene taken with a good phone camera; natural light, real skin texture; "
         "not glossy stock, no beauty filter. People have only two hands with five fingers each.\n\n")

BOOK_BASE = ("lit by the SAME light as the scene (same colour temperature, same direction of light, soft natural shadow under and next to it, a little light falloff and reflection on the glossy cover), "
             "with the same depth of field as the objects around it (slightly soft if it is not in the focus plane), realistic size relative to the cup, phone and hands (a normal 13x20 cm paperback), "
             "slightly worn edges, and partly overlapped by something in the scene (a pen lying on it, a coffee cup or a hand at its edge, or a sheet of paper under it). "
             "The cover design must still be recognisable (title readable), but it should look like a photo taken of a real book in a real room, not added later.\n\n")
BOOK = {
    "lying": "BOOK REALISM (critical - the book must NOT look pasted in like a sticker or a product render): the book is a real, physically present paperback that belongs to the scene. "
             "It lies casually at an angle (not facing the camera straight, not standing upright like a display), with correct perspective of the table/seat, " + BOOK_BASE,
    "held": "BOOK REALISM (critical - the book must NOT look pasted in like a sticker or a product render): the book is a real, physically present paperback that belongs to the scene. "
            "It is held naturally in the person's hands, slightly tilted (not perfectly flat to the camera), with fingers overlapping its edges, " + BOOK_BASE,
    "standing": "BOOK REALISM: the book stands as a real printed paperback with a natural shadow and correct perspective, lit like the rest of the image, like in the reference banner.\n\n",
}

NOFAKEUI = ("NOTIFICATIONS AND APP SCREENS (critical - Meta rejects it as 'Spam - deceptive link'): NEVER draw notification banners, message notification icons "
            "or red badge counters (little red circles with numbers) anywhere, not even small inside a photo. Do NOT make the banner look like a real app screen the viewer is typing in: "
            "no message input field, no text cursor, no selected text, no call/video/info buttons, no send arrow, no status bar. A conversation may be shown only as simple speech bubbles "
            "or as a clearly framed phone illustration. Any other phone in the scene is face down or its screen is dark/out of focus.\n")

REVIEW = ("REVIEW RULES: the background is an ordinary, slightly untidy real place (plain wall, ordinary furniture, everyday objects) - not a postcard, "
          "not decorated, no flowers or props arranged for the photo. The signature under the quote is ONLY the first name, nothing about what the person owns or does.\n")

STRICT = ("CRITICAL POSITION CHECK: the FIRST line of any text must start no higher than 17% of the frame height from the top. "
          "The CTA button must end no lower than 87% of the frame height.\n"
          "NO extra text anywhere in the scene: no posters, signs, wall lettering or written papers besides the book cover{extra}.\n")


def load_formats():
    with open(os.path.join(HERE, "banner_formats.json"), encoding="utf-8") as f:
        return json.load(f)


def build(spec):
    formats = load_formats()
    out = []
    for b in spec["banners"]:
        code = b["format"].upper()
        mode = b.get("book", "lying")
        has_cover = mode != "none"
        ref_n = 3 if has_cover else 2
        if code in formats:
            fm = formats[code]
            fmt = (f"FORMAT: {code} - {fm['description']}. Recipe: {fm['recipe']}. "
                   f"IMAGE {ref_n} is our reference banner for this format: copy its structure and feel, not its exact scene or text.")
        else:
            fmt = (f"FORMAT: {code} (EXPERIMENT - not in our format table). "
                   f"IMAGE {ref_n} is a reference for the look and feel only, not its text.")
        if b.get("format_note"):
            fmt += " " + b["format_note"]
        setting = b.get("setting", spec.get("setting", ""))
        p = HEAD
        p += "EXACT VERTICAL LAYOUT (percent of the full frame height, measured from the top): " + b["layout"] + " Do not put any text or the button outside these zones.\n"
        p += fmt + "\n"
        if setting:
            p += setting.rstrip("\n") + "\n"
        p += SCREEN
        p += NOFAKEUI
        p += "SCENE: " + b["scene"].strip() + "\n"
        p += "TEXT ON THE BANNER (exactly these lines, nothing else):\n" + b["text"].strip() + "\n"
        if has_cover:
            p += (f'IMAGE 2 is the real book cover of the book "{spec["book_title"]}". Reproduce it exactly on the physical book '
                  "(printed paperback, slightly three-dimensional, natural shadow): same design, colours and all cover lettering letter by letter. "
                  "Do not invent or change any cover text.\n")
        p += TYPO + PHOTO
        if has_cover:
            p += BOOK[mode]
        if code == "REVIEW":
            p += REVIEW
        extra = b.get("allowed_text", "")
        p += STRICT.format(extra=(" and " + extra) if extra else "")
        item = {"source": f"source/{spec['book']}/blank_1080x1350.png", "format": "banner", "angle": b["angle"],
                "prompt": p, "fit": "crop", "references": [b["ref"]]}
        if has_cover:
            item["cover"] = spec["cover"]
        if b.get("crop_y"):
            item["crop_y"] = b["crop_y"]
        out.append(item)
    return {"book": spec["book"], "market": spec["market"], "date": spec["date"],
            "check_layout": True, "source_campaign": spec.get("source_campaign", ""), "source_account": spec.get("source_account", "Zlaten Kluch 1"),
            "defaults": {"mode": "model", "output_format": "png", "quality": "high", "fit": "crop",
                         "model": "gpt-image-2.5-sunburst", "api_size": "1024x1536"},
            "banners": out}


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    job = build(spec)
    if "--print" in sys.argv:
        for b in job["banners"]:
            print("=" * 20, b["angle"]); print(b["prompt"])
        return
    for b in spec["banners"]:
        for k in ("ref",):
            if not os.path.exists(os.path.join(ROOT, b[k])):
                sys.exit(f"ГРЕШКА: липсва {b[k]}")
    blank = os.path.join(ROOT, f"source/{spec['book']}/blank_1080x1350.png")
    if not os.path.exists(blank):
        sys.exit(f"ГРЕШКА: липсва {blank} (копирай от source/GREEK/blank_1080x1350.png)")
    name = f"{spec['book']}_{spec['market']}_{spec['date']}" + (f"-{spec['suffix']}" if spec.get("suffix") else "") + ".json"
    path = os.path.join(ROOT, "jobs", name)
    json.dump(job, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("OK", path, len(job["banners"]), "банера")


if __name__ == "__main__":
    main()
