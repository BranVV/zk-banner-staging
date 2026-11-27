"""docx (стилове на Ани) -> HTML фрагмент с класове; картинки в сиво."""
import docx, html, os, re
from docx.oxml.ns import qn
from PIL import Image

d = docx.Document('src/ms.docx')
part = d.part
os.makedirs('out/img', exist_ok=True)
CLS = {'H1': 'h1', 'H2': 'h2', 'H3': 'h3', 'Body': 'p', 'Small': 'small', 'Tiny': 'tiny',
       'Bullet': 'bullet', 'Eyebrow': 'eyebrow', 'ProjectNum': 'pnum', 'Image': 'imgp', 'Normal': 'p'}

def run_html(r):
    t = ''.join((x.text or '') if x.tag == qn('w:t') else ('\t' if x.tag == qn('w:tab') else '')
                for x in r.iter() if x.tag in (qn('w:t'), qn('w:tab')))
    t = html.escape(t)
    rpr = r.find(qn('w:rPr'))
    if rpr is not None and t.strip():
        if rpr.find(qn('w:b')) is not None and rpr.find(qn('w:b')).get(qn('w:val')) not in ('0', 'false'): t = f'<b>{t}</b>'
        if rpr.find(qn('w:i')) is not None and rpr.find(qn('w:i')).get(qn('w:val')) not in ('0', 'false'): t = f'<i>{t}</i>'
    return t

imgs = []
def img_html(blip):
    rid = blip.get(qn('r:embed')); ip = part.related_parts[rid]
    name = os.path.basename(ip.partname); dst = 'out/img/' + os.path.splitext(name)[0] + '.png'
    if not os.path.exists(dst):
        open('/tmp/_i', 'wb').write(ip.blob)
        im = Image.open('/tmp/_i').convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im)
        bg.convert('L').save(dst)
    im = Image.open(dst); imgs.append((dst, im.size))
    return f'<img src="img/{os.path.basename(dst)}" data-w="{im.width}" data-h="{im.height}">'

def para(el):
    ppr = el.find(qn('w:pPr')); sty = None
    if ppr is not None and ppr.find(qn('w:pStyle')) is not None: sty = ppr.find(qn('w:pStyle')).get(qn('w:val'))
    parts = []
    for ch in el.iter():
        if ch.tag == qn('w:r'): parts.append(run_html(ch))
        elif ch.tag == qn('a:blip'): parts.append(img_html(ch))
    inner = ''.join(parts).strip()
    brk = any(b.get(qn('w:type')) == 'page' for b in el.iter(qn('w:br')))
    return sty, inner, brk

def table(el):
    rows = []
    for tr in el.iter(qn('w:tr')):
        cells = []
        for tc in tr.findall(qn('w:tc')):
            cells.append('<br>'.join(para(p)[1] for p in tc.findall(qn('w:p'))))
        rows.append(cells)
    if not rows: return ''
    h = '<table><thead><tr>' + ''.join(f'<th>{c}</th>' for c in rows[0]) + '</tr></thead><tbody>'
    h += ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows[1:]) + '</tbody></table>'
    return h

out = []; skip_toc = False
for el in d.element.body:
    tag = el.tag.split('}')[1]
    if tag == 'p':
        sty, inner, brk = para(el)
        if sty == 'H1' and re.sub('<[^>]+>', '', inner).strip() == 'Съдържание': skip_toc = True; continue
        if skip_toc:
            if brk: skip_toc = False
            continue
        if not inner: continue
        c = CLS.get(sty, 'p')
        if c == 'bullet': inner = re.sub(r'^[•·]\s*', '', inner)
        out.append(f'<div class="{c}">{inner}</div>')
    elif tag == 'tbl':
        if not skip_toc: out.append(table(el))
open('out/body.html', 'w', encoding='utf-8').write('\n'.join(out))
print(len(out), 'blocks', len(imgs), 'images')
