"""Пренаписва номера на проекта в картинките (ПРОЕКТ NN, номер в ъгъла) и маха английските думи от надписите.
relabel(src, dst, old, new) -> списък с направени промени"""
import subprocess, csv, io, re
from PIL import Image, ImageDraw, ImageFont, ImageStat

FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
EN = re.compile(r'^[A-Z]{3,}$')

def ocr(path):
    out = subprocess.run(['tesseract', path, '-', '-l', 'rus+eng', '--psm', '11', 'tsv'], capture_output=True, text=True).stdout
    rows = [r for r in csv.DictReader(io.StringIO(out), delimiter='\t', quoting=csv.QUOTE_NONE) if r.get('text', '').strip()]
    for r in rows:
        for k in ('left', 'top', 'width', 'height', 'conf'): r[k] = float(r[k])
    return rows

def bg_and_fg(im, box):
    x0, y0, x1, y1 = box; pad = 6
    ring = [im.crop((max(0, x0 - pad), y0, x0, y1)), im.crop((x1, y0, min(im.width, x1 + pad), y1))]
    vals = [ImageStat.Stat(r.convert('L')).median[0] for r in ring if r.width > 0]
    bg = int(sorted(vals)[len(vals) // 2]) if vals else 255
    fg = 255 if bg < 128 else (110 if bg > 200 and im.crop(box).convert('L').getextrema()[0] > 60 else 30)
    return bg, fg

def fit_font(path, h): return ImageFont.truetype(path, max(8, int(h * 1.05)))

def corner_number(im, old):
    """Номерът в горния ляв ъгъл на AI рендерите: малко тъмно петно (цифри) в ъгъла."""
    import numpy as np
    W, H = im.size; a = np.array(im.crop((0, 0, int(W * .12), int(H * .2))))
    ys, xs = np.where(a < 90)
    if not len(xs): return None
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    if x1 - x0 > 70 or y1 - y0 > 35: return None
    return (float(x0), float(y0), float(x1 - x0 + 1), float(y1 - y0 + 1))

def put_num(im, d, q, new, bold):
    x, y, w, h = q['left'], q['top'], q['width'], q['height']
    box = (int(x) - 2, int(y) - 2, int(x + w) + 3, int(y + h) + 2)
    bg, fg = bg_and_fg(im, box); d.rectangle(box, fill=bg)
    f = ImageFont.truetype(FONT_B if (bold or fg == 255) else FONT_R, max(8, int(h / 0.72)))
    d.text((x, y + h), f'{new:02d}', font=f, fill=fg if not bold else (fg if fg == 255 else 30), anchor='ls')

def relabel(src, dst, old, new):
    im = Image.open(src).convert('L'); W, H = im.size; d = ImageDraw.Draw(im); log = []
    rows = ocr(src)
    for i, r in enumerate(rows):
        t = r['text'].strip(); x, y, w, h = r['left'], r['top'], r['width'], r['height']
        if t.upper().replace('0', 'О') in ('ПРОЕКТ', 'NPOEKT', 'MPOEKT', 'NMPOEKT') or re.match(r'^[ПNМ]{1,2}[РP]ОЕКТ$', t.upper()):
            num = next((q for q in rows[i+1:i+3] if re.match(r'^\d{1,2}$', q['text'].strip()) and abs(q['top'] - y) < h * 0.6), None)
            if num:
                num = dict(num); num['height'] = h; num['top'] = y
                put_num(im, d, num, new, False); log.append(f'ПРОЕКТ {old}->{new:02d}')
        elif EN.match(t) and t not in ('MDF', 'HDF', 'OSB', 'PVA', 'LED'):
            # махаме думата и разделителя след нея, после изместваме останалата част от реда наляво
            line = sorted([q for q in rows if abs((q['top'] + q['height'] / 2) - (y + h / 2)) < h * 0.6], key=lambda q: q['left'])
            prev = [q for q in line if q['left'] + q['width'] <= x + 1]
            nxt = [q for q in line if q['left'] >= x + w - 1]
            after = [q for q in nxt if len(q['text'].strip()) >= 3]
            if not prev or not after: continue
            gap_start = int(x)                              # началото на думата
            gap_end = int(after[0]['left'])                 # началото на следващата истинска дума
            y0 = int(min(q['top'] for q in line)) - 4; y1 = int(max(q['top'] + q['height'] for q in line)) + 4
            x_end = int(max(q['left'] + q['width'] for q in line)) + 4
            tail = im.crop((gap_end, y0, x_end, y1))
            bg, _ = bg_and_fg(im, (gap_start, y0, x_end, y1))
            d.rectangle((gap_start, y0, x_end, y1), fill=bg); im.paste(tail, (gap_start, y0))
            log.append(f'-{t}')
    cn = corner_number(im, old)
    if cn:
        x, y, w, h = cn; put_num(im, d, {'left': x, 'top': y, 'width': w, 'height': h}, new, True); log.append(f'ъгъл {old}->{new:02d}')
    im.save(dst); return log
