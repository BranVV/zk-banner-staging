#!/usr/bin/env python3
"""check_layout.py - автоматична проверка на ръбовете след генериране (решение на Bran 11.11.2026).

Намира първия ред текст и червения CTA бутон във всеки готов банер. Ако текстът или бутонът
са на по-малко от MIN_MARGIN (4%) от ръба, изрязва банера наново от суровия кадър в _raw/
(без ново генериране): прозорец, който побира текста и бутона с поле, при нужда по-висок
и с размазани странични ленти до 1080 px.

Употреба:
  python3 tools/check_layout.py BG/EXCEL/2026-11-11            # проверява и оправя
  python3 tools/check_layout.py BG/EXCEL/2026-11-11 --dry-run  # само отчет

Ограничение: откриването на текст е евристика (контрастни бели/жълти/тъмни пиксели в редове).
Отчетът не замества визуалната проверка по чеклиста (tools/CHECKLIST.md).
"""
import glob, os, sys
import numpy as np
from PIL import Image, ImageFilter

W_OUT, H_OUT = 1080, 1350
MIN_MARGIN = 0.04      # 4% от височината = ~54 px
PAD = 0.045            # желано поле при повторно изрязване (~60 px)


def cta_rows(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = (r > 190) & (g < 80) & (b < 80)
    cnt = red.sum(1)
    rows = np.where(cnt > a.shape[1] * 0.15)[0]
    rows = rows[rows > a.shape[0] * 0.5]
    if len(rows) == 0:
        return None
    return int(rows.min()), int(rows.max())


def text_top(a):
    h, w = a.shape[:2]
    f = a.astype(int)
    lum = f.mean(2)
    white = (f.min(2) > 225)
    yellow = (f[..., 0] > 210) & (f[..., 1] > 160) & (f[..., 2] < 90)
    dark = (f.max(2) < 45)
    col = white | yellow | dark
    grad = np.zeros_like(lum, dtype=bool)
    grad[:, 1:] = np.abs(np.diff(lum, axis=1)) > 70
    txt = (col & grad).sum(1) > w * 0.02
    lim = int(h * 0.55)
    run = 0
    for y in range(lim):
        run = run + 1 if txt[y] else 0
        if run >= 6:
            return y - 5
    return None


def margins(path):
    a = np.asarray(Image.open(path).convert("RGB"))
    h = a.shape[0]
    c = cta_rows(a)
    t = text_top(a)
    top = t / h if t is not None else None
    bot = (h - 1 - c[1]) / h if c else None
    return top, bot


def recrop(raw_path, out_path):
    r = Image.open(raw_path).convert("RGB")
    a = np.asarray(r)
    H, Wd = a.shape[:2]
    c = cta_rows(a)
    t = text_top(a)
    if c is None or t is None:
        return False, "не намерих текст или бутон в _raw"
    pad = int(PAD * H_OUT * Wd / W_OUT)
    need = (c[1] + pad) - (t - pad)
    win = max(int(Wd * H_OUT / W_OUT), need)
    win = min(win, H)
    y0 = (t - pad + c[1] + pad) // 2 - win // 2
    y0 = max(0, min(H - win, y0))
    crop = r.crop((0, y0, Wd, y0 + win))
    w = round(Wd * H_OUT / win)
    crop = crop.resize((w, H_OUT), Image.LANCZOS)
    out = Image.new("RGB", (W_OUT, H_OUT))
    if w >= W_OUT:
        x = (w - W_OUT) // 2
        out.paste(crop.crop((x, 0, x + W_OUT, H_OUT)), (0, 0))
    else:
        p = (W_OUT - w) // 2
        q = W_OUT - w - p
        out.paste(crop.crop((0, 0, p, H_OUT)).filter(ImageFilter.GaussianBlur(14)), (0, 0))
        out.paste(crop.crop((w - q, 0, w, H_OUT)).filter(ImageFilter.GaussianBlur(14)), (p + w, 0))
        out.paste(crop, (p, 0))
    out.save(out_path)
    return True, f"прозорец {win}px от y={y0}"


def main():
    d = sys.argv[1]
    dry = "--dry-run" in sys.argv
    for f in sorted(glob.glob(os.path.join(d, "*.png"))):
        name = os.path.basename(f)
        top, bot = margins(f)
        ok = top is not None and bot is not None and top >= MIN_MARGIN and bot >= MIN_MARGIN
        st = f"top={'?' if top is None else f'{top:.1%}'} bottom={'?' if bot is None else f'{bot:.1%}'}"
        if ok:
            print(f"OK    {name}  {st}")
            continue
        raw = os.path.join(d, "_raw", name)
        if dry or not os.path.exists(raw):
            print(f"ВНИМ. {name}  {st}" + ("" if dry else "  (няма _raw)"))
            continue
        done, msg = recrop(raw, f)
        t2, b2 = margins(f)
        print(f"FIX   {name}  {st} -> top={t2 if t2 is None else f'{t2:.1%}'} bottom={b2 if b2 is None else f'{b2:.1%}'}  ({msg})")


if __name__ == "__main__":
    main()
