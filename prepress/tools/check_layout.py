"""Проверки на оформлението през WeasyPrint layout: разделени малки таблици, запълване на страници, разделени картинки/заглавия."""
import sys, re
from weasyprint import HTML
doc = HTML('out/v3.html', base_url='out/').render()
H = 210 - 2*0  # mm
def walk(b):
    yield b
    for c in getattr(b, 'children', []) or []:
        yield from walk(c)
tables = {}; fill = []
for i, p in enumerate(doc.pages):
    root = p._page_box
    ys = []
    for b in (x for c in root.children if c.__class__.__name__ != 'MarginBox' for x in walk(c)):
        el = getattr(b, 'element', None)
        if el is not None and el.tag == 'table':
            tables.setdefault(id(el), [el, set()])[1].add(i+1)
        if b.__class__.__name__ in ('LineBox', 'ImageBox', 'InlineReplacedBox', 'BlockReplacedBox') or (el is not None and el.tag in ('img', 'svg')):
            try: ys.append(b.position_y + b.height)
            except Exception: pass
    bottom = max(ys) if ys else 0
    ch = root.children[0] if root.children else None
    area_top = root.content_box_y() if hasattr(root, 'content_box_y') else 0
    fill.append((i+1, bottom))
split = []
for el, pages in tables.values():
    rows = len(el.findall('.//tr'))
    if len(pages) > 1: split.append((sorted(pages), rows))
print('TABLES:', len(tables), 'SPLIT:', split)
pts = [b for _, b in fill]; mx = max(pts)
print('FILL', sorted(b for _,b in fill)[:3], mx)
print('LOW FILL (<45% of max bottom):', [(n, round(b/mx*100)) for n, b in fill if b < mx*0.45])
