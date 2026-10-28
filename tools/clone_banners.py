#!/usr/bin/env python3
"""clone_banners.py — клониране на рекламни банери от един пазар на друг.

Взима изходен банер (обикновено BG), превежда текста върху него на целевия
език и записва готовия банер в <ПАЗАР>/<КНИГА>/<дата>/, откъдето се подава на
Meta през raw линк.

Два режима на банер:
  model   — целият банер се пре-генерира от OpenAI (gpt-image-1, images/edits)
            с висока вярност към оригинала; локализираната корица може да се
            подаде като референтно изображение.
  overlay — текстът се нарисува програмно върху оригинала (Pillow). Пази
            корицата и снимките едно към едно, но иска координати на кутиите.

Употреба:
    python tools/clone_banners.py jobs/ЗАДАЧА.json [--dry-run] [--force]
                                  [--only ИМЕ] [--root ПАПКА]

Ключът се чете от променливата на средата OPENAI_API_KEY. Никога не се пише
във файл в репото.

Форматът на файла със задачата е описан в jobs/_schema.md.
"""

from __future__ import annotations

import argparse
import base64
import copy
import datetime as _dt
import io
import json
import math
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("ГРЕШКА: липсва requests. Инсталирай: pip install -r tools/requirements.txt")

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("ГРЕШКА: липсва Pillow. Инсталирай: pip install -r tools/requirements.txt")


API_URL = "https://api.openai.com/v1/images/edits"
API_SIZES = {"1024x1024": 1.0, "1536x1024": 1.5, "1024x1536": 1024 / 1536}
VALID_MODES = {"model", "overlay"}
VALID_FIT = {"stretch", "pad"}

LANGUAGES = {
    "RS": ("Serbian (Latin script)", "сръбски, латиница"),
    "HR": ("Croatian", "хърватски"),
    "BA": ("Bosnian", "босненски"),
    "RO": ("Romanian", "румънски"),
    "BG": ("Bulgarian", "български"),
}

# Хърватският и босненският ползват общ превод — HR е водещ.
SHARED_TRANSLATION = {"BA": "HR"}


def die(msg: str) -> None:
    print(f"ГРЕШКА: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"ВНИМАНИЕ: {msg}")


# --------------------------------------------------------------------------
# Задача
# --------------------------------------------------------------------------

def load_job(path: Path) -> dict:
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"{path} не е валиден JSON: {exc}")
    except OSError as exc:
        die(f"{path} не може да се прочете: {exc}")

    for field in ("book", "market", "banners"):
        if not job.get(field):
            die(f"{path}: липсва задължителното поле '{field}'")

    market = str(job["market"]).upper()
    if market not in LANGUAGES:
        die(f"непознат пазар '{market}'. Позволени: {', '.join(sorted(LANGUAGES))}")
    job["market"] = market

    if not isinstance(job["banners"], list):
        die(f"{path}: 'banners' трябва да е списък")

    job.setdefault("date", _dt.date.today().isoformat())
    job.setdefault("defaults", {})
    return job


def merged(job: dict, banner: dict) -> dict:
    """Настройките по подразбиране на задачата, презаписани от тези на банера."""
    out = copy.deepcopy(job.get("defaults", {}))
    for key, value in banner.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


def out_name(book: str, market: str, fmt: str, angle: str) -> str:
    """КНИГА_ПАЗАР_формат_ъгъл — без размер и без версия в името."""
    parts = [book, market, fmt, angle]
    slug = "_".join(str(p).strip().replace(" ", "-") for p in parts if str(p).strip())
    return slug


# --------------------------------------------------------------------------
# Размери
# --------------------------------------------------------------------------

def pick_api_size(width: int, height: int) -> str:
    """Най-близкото позволено от API съотношение към оригинала."""
    ratio = width / height
    return min(API_SIZES, key=lambda s: abs(math.log(ratio / API_SIZES[s])))


def prepare_input(img: Image.Image, api_size: str, fit: str) -> tuple[Image.Image, dict]:
    """Привежда оригинала към размер, който API приема. Връща и данни за обратното."""
    target_w, target_h = (int(v) for v in api_size.split("x"))
    img = img.convert("RGB")

    if fit == "stretch":
        return img.resize((target_w, target_h), Image.LANCZOS), {"fit": "stretch"}

    # pad: вписваме оригинала и допълваме с бяло, после изрязваме обратно
    scale = min(target_w / img.width, target_h / img.height)
    new_w, new_h = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    off_x, off_y = (target_w - new_w) // 2, (target_h - new_h) // 2
    canvas.paste(img.resize((new_w, new_h), Image.LANCZOS), (off_x, off_y))
    return canvas, {"fit": "pad", "box": (off_x, off_y, off_x + new_w, off_y + new_h)}


def restore_output(img: Image.Image, size: tuple[int, int], meta: dict) -> Image.Image:
    """Връща генерираното изображение към оригиналните размери."""
    if meta.get("fit") == "pad":
        img = img.crop(meta["box"])
    return img.resize(size, Image.LANCZOS)


# --------------------------------------------------------------------------
# Промпт
# --------------------------------------------------------------------------

def build_prompt(cfg: dict, market: str, has_cover_ref: bool, padded: bool = False) -> str:
    lang_en, _ = LANGUAGES[market]

    if cfg.get("prompt"):
        return str(cfg["prompt"])

    lines = [
        f"Recreate this advertising banner with every piece of text translated into {lang_en}.",
        "",
        "ABSOLUTE RULES:",
        "- Keep the layout, composition, colours, fonts, font weights, photographs, "
        "graphics, badges and proportions EXACTLY as in the original image.",
        "- Change ONLY the text. Do not move, resize, recolour or restyle any element.",
        "- Translate EVERY piece of text. No word of the original language may remain "
        "anywhere in the image, including small print, badges, stickers and seals.",
        "- Keep each text inside its original block. If a translation is longer, reduce "
        "the font size slightly or tighten the letter spacing; never let text overflow, "
        "wrap into other elements, or shift the block.",
        "- Preserve diacritics exactly as written in the translations below.",
        "- Do not add watermarks, logos, borders, captions or any new element.",
        "- Do not alter faces, hands, skin tone or the physical shape of the book.",
    ]

    if has_cover_ref:
        lines.append(
            f"- The additional image provided is the official {lang_en} cover of this book. "
            "Replace the book cover shown in the banner with that cover, matching the "
            "original's position, size, rotation, perspective, lighting, reflections and "
            "shadows exactly, so the book looks physically unchanged."
        )
    else:
        lines.append(
            "- The book cover shown in the banner must also have its title and subtitle "
            f"translated into {lang_en}, keeping the cover's design, colours, typography "
            "and layout identical."
        )

    if padded:
        lines.append(
            "- The image has plain white bars added along two edges purely as padding. "
            "Leave them plain white and empty. Do not extend the artwork into them, do "
            "not re-centre or rescale the banner to fill them, and do not place any text "
            "or element inside them. The banner itself must stay exactly where it is."
        )

    for extra in cfg.get("extra_rules", []) or []:
        lines.append(f"- {extra}")

    pairs = cfg.get("translations") or []
    if pairs:
        lines.append("")
        lines.append("Use exactly these translations, character for character:")
        for pair in pairs:
            src = str(pair.get("source", "")).strip()
            tgt = str(pair.get("target", "")).strip()
            note = str(pair.get("note", "")).strip()
            line = f'  "{src}" -> "{tgt}"'
            if note:
                line += f"   ({note})"
            lines.append(line)

    keep = cfg.get("keep_as_is") or []
    if keep:
        lines.append("")
        lines.append("Leave these exactly as they are, untranslated:")
        for item in keep:
            lines.append(f'  "{item}"')

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Режим model
# --------------------------------------------------------------------------

def call_openai(api_key: str, images: list[tuple[str, bytes]], prompt: str,
                api_size: str, cfg: dict, retries: int = 3) -> bytes:
    files = []
    for name, blob in images:
        suffix = Path(name).suffix.lower()
        mime = {".png": "image/png", ".webp": "image/webp"}.get(suffix, "image/jpeg")
        files.append(("image[]", (name, blob, mime)))

    data = {
        "model": cfg.get("model", "gpt-image-1"),
        "prompt": prompt,
        "size": api_size,
        "quality": cfg.get("quality", "high"),
        "input_fidelity": cfg.get("input_fidelity", "high"),
        "n": "1",
    }
    if cfg.get("background"):
        data["background"] = cfg["background"]

    headers = {"Authorization": f"Bearer {api_key}"}
    last = ""

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(API_URL, headers=headers, data=data, files=files, timeout=600)
        except requests.RequestException as exc:
            last = str(exc)
        else:
            if resp.status_code == 200:
                payload = resp.json()
                b64 = (payload.get("data") or [{}])[0].get("b64_json")
                if not b64:
                    die(f"API върна отговор без изображение: {json.dumps(payload)[:400]}")
                return base64.b64decode(b64)

            last = f"HTTP {resp.status_code}: {resp.text[:400]}"
            # 400/401/403 не се оправят с повтаряне
            if resp.status_code in (400, 401, 403, 404):
                die(f"API отказа заявката. {last}")

        if attempt < retries:
            wait = 5 * attempt
            warn(f"опит {attempt} неуспешен ({last}); нов опит след {wait} сек.")
            time.sleep(wait)

    die(f"API не отговори след {retries} опита. Последна грешка: {last}")
    return b""  # недостижимо


def run_model(cfg: dict, job: dict, root: Path, src_path: Path,
              api_key: str, dry: bool) -> Image.Image | None:
    with Image.open(src_path) as src:
        src.load()
        orig_size = src.size
        api_size = cfg.get("api_size") or pick_api_size(*orig_size)
        if api_size not in API_SIZES:
            die(f"непознат api_size '{api_size}'. Позволени: {', '.join(API_SIZES)}")
        fit = cfg.get("fit", "pad")
        if fit not in VALID_FIT:
            die(f"непознат fit '{fit}'. Позволени: {', '.join(VALID_FIT)}")
        prepared, meta = prepare_input(src, api_size, fit)

    refs: list[tuple[str, bytes]] = []
    cover = cfg.get("cover")
    if cover:
        cover_path = (root / cover).resolve()
        if not cover_path.is_file():
            die(f"липсва файлът с корицата: {cover}")
        refs.append((cover_path.name, cover_path.read_bytes()))

    for extra in cfg.get("references", []) or []:
        extra_path = (root / extra).resolve()
        if not extra_path.is_file():
            die(f"липсва референтният файл: {extra}")
        refs.append((extra_path.name, extra_path.read_bytes()))

    prompt = build_prompt(cfg, job["market"], has_cover_ref=bool(cover),
                          padded=meta.get("fit") == "pad" and meta.get("box") is not None
                          and meta["box"] != (0, 0, *prepared.size))

    if dry:
        print(f"      размер: {orig_size[0]}x{orig_size[1]} -> API {api_size} (fit={fit})")
        print(f"      референции: {len(refs)}")
        print(f"      преводи: {len(cfg.get('translations') or [])}")
        print("      --- промпт ---")
        for line in prompt.splitlines():
            print(f"      {line}")
        return None

    buf = io.BytesIO()
    prepared.save(buf, format="PNG")
    images = [(src_path.stem + ".png", buf.getvalue())] + refs

    raw = call_openai(api_key, images, prompt, api_size, cfg)
    with Image.open(io.BytesIO(raw)) as generated:
        generated.load()
        return restore_output(generated, orig_size, meta)


# --------------------------------------------------------------------------
# Режим overlay
# --------------------------------------------------------------------------

def load_font(root: Path, name: str | None, size: int) -> ImageFont.FreeTypeFont:
    candidates = []
    if name:
        candidates += [root / "fonts" / name, Path(name)]
    candidates += [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for cand in candidates:
        if cand.is_file():
            try:
                return ImageFont.truetype(str(cand), size)
            except OSError:
                continue
    if name:
        warn(f"шрифтът '{name}' не е намерен; ползвам вградения")
    return ImageFont.load_default()


def wrap_to_box(draw: ImageDraw.ImageDraw, text: str, root: Path, font_name: str | None,
                box: tuple[int, int, int, int], max_size: int, min_size: int,
                line_spacing: float) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Най-големият шрифт, при който текстът се събира в кутията."""
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    words = text.split()

    for size in range(max_size, min_size - 1, -1):
        font = load_font(root, font_name, size)
        lines, current = [], ""
        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=font) <= box_w or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        if any(draw.textlength(ln, font=font) > box_w for ln in lines):
            continue
        line_h = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
        if len(lines) * line_h * line_spacing <= box_h:
            return font, lines

    return load_font(root, font_name, min_size), [text]


def run_overlay(cfg: dict, job: dict, root: Path, src_path: Path, dry: bool) -> Image.Image | None:
    boxes = cfg.get("text_boxes") or []
    if not boxes:
        die(f"режим overlay иска 'text_boxes' за {src_path.name}")

    if dry:
        print(f"      кутии с текст: {len(boxes)}")
        for item in boxes:
            print(f"        {item.get('box')}  \"{item.get('text', '')[:60]}\"")
        return None

    with Image.open(src_path) as src:
        src.load()
        canvas = src.convert("RGB")

    draw = ImageDraw.Draw(canvas)

    for item in boxes:
        box = item.get("box")
        text = str(item.get("text", ""))
        if not box or len(box) != 4:
            die("всяка кутия иска 'box': [left, top, right, bottom]")
        box = tuple(int(v) for v in box)

        fill_colour = item.get("erase_with")
        if fill_colour:
            draw.rectangle(box, fill=tuple(fill_colour) if isinstance(fill_colour, list) else fill_colour)

        if not text:
            continue

        font, lines = wrap_to_box(
            draw, text, root, item.get("font"), box,
            int(item.get("max_font_size", max(12, (box[3] - box[1])))),
            int(item.get("min_font_size", 10)),
            float(item.get("line_spacing", 1.15)),
        )

        colour = item.get("colour", [255, 255, 255])
        colour = tuple(colour) if isinstance(colour, list) else colour
        align = item.get("align", "center")
        line_h = (font.getbbox("Ay")[3] - font.getbbox("Ay")[1]) * float(item.get("line_spacing", 1.15))
        total_h = line_h * len(lines)
        y = box[1] + max(0, ((box[3] - box[1]) - total_h) / 2)

        for line in lines:
            width = draw.textlength(line, font=font)
            if align == "left":
                x = box[0]
            elif align == "right":
                x = box[2] - width
            else:
                x = box[0] + ((box[2] - box[0]) - width) / 2
            draw.text((x, y), line, font=font, fill=colour)
            y += line_h

    return canvas


# --------------------------------------------------------------------------
# Основен ход
# --------------------------------------------------------------------------

def process(job: dict, root: Path, args: argparse.Namespace) -> list[dict]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    book, market, date = job["book"], job["market"], job["date"]
    out_dir = root / market / book / date
    results: list[dict] = []

    for index, banner in enumerate(job["banners"], start=1):
        cfg = merged(job, banner)
        source = cfg.get("source")
        if not source:
            die(f"банер №{index}: липсва 'source'")

        src_path = (root / source).resolve()
        if not src_path.is_file():
            die(f"банер №{index}: липсва изходният файл {source}")

        fmt = cfg.get("format", "banner")
        angle = cfg.get("angle") or Path(source).stem
        name = out_name(book, market, fmt, angle)

        if args.only and args.only.lower() not in name.lower():
            continue

        mode = cfg.get("mode", "model")
        if mode not in VALID_MODES:
            die(f"банер №{index}: непознат режим '{mode}'. Позволени: {', '.join(VALID_MODES)}")

        ext = cfg.get("output_format", "png").lower().lstrip(".")
        dest = out_dir / f"{name}.{ext}"

        print(f"  [{index}/{len(job['banners'])}] {name}  ({mode})")

        if dest.exists() and not args.force:
            print(f"      вече съществува, пропускам ({dest.relative_to(root)})")
            results.append({"name": name, "path": str(dest.relative_to(root)), "status": "skipped"})
            continue

        if mode == "model":
            if not api_key and not args.dry_run:
                die("липсва OPENAI_API_KEY в средата. В GitHub Actions се подава като "
                    "secret; на компютъра се задава с setx OPENAI_API_KEY \"…\"")
            image = run_model(cfg, job, root, src_path, api_key, args.dry_run)
        else:
            image = run_overlay(cfg, job, root, src_path, args.dry_run)

        if args.dry_run or image is None:
            results.append({"name": name, "path": str(dest.relative_to(root)), "status": "dry-run"})
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = {"quality": 95, "subsampling": 0} if ext in ("jpg", "jpeg") else {}
        image.save(dest, **save_kwargs)
        print(f"      записан: {dest.relative_to(root)}  ({image.width}x{image.height})")
        results.append({
            "name": name,
            "path": str(dest.relative_to(root)).replace(os.sep, "/"),
            "source": source,
            "mode": mode,
            "status": "ok",
        })

    return results


def write_manifest(job: dict, root: Path, results: list[dict], repo: str, branch: str) -> Path:
    out_dir = root / job["market"] / job["book"] / job["date"]
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "manifest.json"

    base = f"https://raw.githubusercontent.com/{repo}/{branch}/"
    for item in results:
        if item.get("status") == "ok":
            item["raw_url"] = base + item["path"]

    manifest.write_text(json.dumps({
        "book": job["book"],
        "market": job["market"],
        "date": job["date"],
        "source_campaign": job.get("source_campaign"),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "banners": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Клониране на банери между пазари")
    parser.add_argument("job", help="път до файла със задачата (jobs/*.json)")
    parser.add_argument("--root", default=None, help="корен на репото (по подразбиране: родителят на tools/)")
    parser.add_argument("--dry-run", action="store_true", help="само проверка и промпт, без повикване на API")
    parser.add_argument("--force", action="store_true", help="презаписва вече съществуващи банери")
    parser.add_argument("--only", default=None, help="обработва само банерите, чието име съдържа този текст")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "BranVV/zk-banner-staging"))
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", "main"))
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = (root / args.job) if not job_path.exists() else job_path.resolve()

    job = load_job(job_path)
    lang_en, lang_bg = LANGUAGES[job["market"]]
    shared = SHARED_TRANSLATION.get(job["market"])

    print(f"Задача: {job_path.name}")
    print(f"Книга: {job['book']}   Пазар: {job['market']} ({lang_bg})   Дата: {job['date']}")
    if shared:
        print(f"Бележка: {job['market']} ползва общ превод с {shared}.")
    if job.get("source_campaign"):
        print(f"Изходна кампания: {job['source_campaign']}")
    print(f"Банери: {len(job['banners'])}")
    print()

    results = process(job, root, args)

    print()
    if args.dry_run:
        print("DRY RUN — нищо не е генерирано и нищо не е записано.")
        return

    done = [r for r in results if r.get("status") == "ok"]
    if done:
        manifest = write_manifest(job, root, results, args.repo, args.branch)
        print(f"Готови банери: {len(done)}")
        print(f"Списък с линковете: {manifest.relative_to(root)}")
        for item in done:
            print(f"  {item['raw_url']}")
    else:
        print("Няма нови банери.")


if __name__ == "__main__":
    main()
