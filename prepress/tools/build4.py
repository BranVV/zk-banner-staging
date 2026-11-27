"""v03: части, нова йерархия на главите, залепени подзаглавия, бележки до края на страницата.
python3 build3.py <pt> <lead>   (EXTRA_PDF=... за допълнителни проекти към PDF)"""
import re, sys, html, os, json, math
from weasyprint import HTML

FONT = float(sys.argv[1]); LEAD = float(sys.argv[2])
TO_PDF = {4, 5, 6, 12, 13, 16, 47, 49} | set(int(x) for x in os.environ.get('EXTRA_PDF', '').split(',') if x)
TITLE = 'Направи си сам: Дървени мебели'
SUB = 'Пълно ръководство за дърводелство - от основите до майсторските проекти'
ISBN = 'ISBN: 978-619-7808-29-2'
LINE_MM = 7.0

S = 'fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
def bars(n): return '<svg viewBox="0 0 24 24" class="ic">' + ''.join(
    f'<rect x="{2+i*7.5}" y="{15-i*5}" width="5.5" height="{7+i*5}" rx="1" '
    + ('fill="#000"/>' if i < n else 'fill="none" stroke="#000" stroke-width="1.6"/>') for i in range(3)) + '</svg>'
I_TIME = f'<svg viewBox="0 0 24 24" class="ic"><circle cx="12" cy="12" r="9" {S}/><path d="M12 7v5l3.5 2.5" {S}/></svg>'
I_DIM = (f'<svg viewBox="0 0 24 24" class="ic"><path d="M5 7.5l7-4 7 4v7.5l-7 4-7-4z M5 7.5l7 4 7-4 M12 11.5v7.5" {S}/>'
         f'<path d="M3 22h18 M3 20.5v3 M21 20.5v3" stroke="#000" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>')
I_CON = f'<svg viewBox="0 0 24 24" class="ic"><path d="M3 3h6v18H3z M9 15h12v6H9z" {S}/><path d="M6 13v5 M4.5 18.5h3" {S}/></svg>'
LEVELS = {1: 'Начинаещ', 2: 'Средно напреднал', 3: 'Напреднал'}
GROUPS = {1: 'Начинаещи', 2: 'Средно напреднали', 3: 'Напреднали - майсторски проекти'}
ADV_WORDS = ('чекмедже', 'врат', 'гардероб', 'кухнен', 'остров', 'скрин')
strip = lambda s: re.sub('<[^>]+>', '', s).strip()

body = open('out/body.html', encoding='utf-8').read().split('\n', 2)[2]
body = body.replace('<div class="tiny"><b>Пейка</b> <b>за</b> <b>коридор</b><b> с </b><b>ракла</b></div>', '<div class="h1">Пейка за коридор с ракла</div>')
def sz(m):
    w, h = int(m.group(2)), int(m.group(3)); mw = w / 250 * 25.4; mh = h / 250 * 25.4
    if h > w * 1.2:  # план за разкрой (страница A4) - на цяла страница, без белите полета
        k = min(114 / mw, 166 / mh); return f'<img class="plate" src="{m.group(1)}" style="width:{mw*k:.2f}mm;height:{mh*k:.2f}mm">'
    k = min(1, 114 / mw, 88 / mh); return f'<img src="{m.group(1)}" style="width:{mw*k:.2f}mm;height:{mh*k:.2f}mm">'
body = re.sub(r'<img src="([^"]+)" data-w="(\d+)" data-h="(\d+)">', sz, body)
body = re.sub(r'<table>((?:(?!</table>).)*)</table>',
              lambda m: f'<table class="{"keep" if m.group(1).count("<tr>") <= 9 else "long"}">{m.group(1)}</table>', body, flags=re.S)
B = body.split('\n')
HEADS = set()
for l in B:
    m = re.match(r'<div class="h3">(.*)</div>$', l)
    if m:
        t = strip(m.group(1))
        if len(t) <= 60 and not t.endswith('.'): HEADS.add(t)
def fixline(l):
    m = re.match(r'<div class="(h1|h2|h3)">(.*)</div>$', l)
    if m:
        t = strip(m.group(2))
        if len(t) > 70 or (t.endswith('.') and not t.endswith('W.E.B.')):
            return f'<div class="p">{re.sub(r"</?b>", "", m.group(2))}</div>'
    m = re.match(r'<div class="(p|small)">(.*)</div>$', l)
    if m and strip(m.group(2)) in HEADS: return f'<div class="h3">{strip(m.group(2))}</div>'
    # абзац, който е изцяло болд и кратък -> истинско заглавие
    m = re.match(r'<div class="(p|small|tiny|bullet)">(.*)</div>$', l)
    if m:
        c = re.sub(r'</b>(\s*)<b>', r'\1', m.group(2)).strip(); mb = re.fullmatch(r'<b>([^<]*)</b>', c)
        if mb and len(mb.group(1).strip()) <= 90 and not mb.group(1).strip().endswith('.'):
            t = re.sub(r'\s+', ' ', mb.group(1)).strip()
            if m.group(1) == 'bullet': return f'<div class="bullet">{t}</div>'
            if t.isupper(): return f'<div class="h1">{t.capitalize()}</div>'
            if re.match(r'^\d+\.\s', t): return f'<div class="h2">{t}</div>'
            if re.match(r'^Стъпка \d+', t) or re.match(r'^(Странични сачмени|Скрити водачи|Водачи с плавно|Панти за )', t): return f'<div class="h4">{t}</div>'
            return f'<div class="h3">{t}</div>'
    # разпадната таблица: всички редове в една клетка
    if l.startswith('<table') and l.count('<br>') > 3:
        def rows(mm):
            cells = re.findall(r'<td>(.*?)</td>', mm.group(1))
            if len(cells) == 2 and '<br>' in cells[0] and not strip(cells[1]):
                out = ''
                for line in cells[0].split('<br>'):
                    parts = re.split(r'\s{3,}|\t', line.strip(), maxsplit=1)
                    out += f'<tr><td>{parts[0]}</td><td>{parts[1] if len(parts) > 1 else ""}</td></tr>'
                return out
            return mm.group(0)
        l = re.sub(r'<tr>(.*?)</tr>', rows, l)
    return l
B = [fixline(l) for l in B]
# абзац, завършващ с „:“, последван от кратки абзаци -> списък с точки
for i in range(len(B) - 1):
    m = re.match(r'<div class="p">(.*)</div>$', B[i])
    if m and strip(m.group(1)).endswith(':'):
        j = i + 1; run = []
        while j < len(B):
            mm = re.match(r'<div class="p">(.*)</div>$', B[j])
            if not mm or len(strip(mm.group(1))) > 100 or re.match(r'(Не |Ако |При |Важно)', strip(mm.group(1))): break
            run.append(j); j += 1
        if len(run) >= 3:
            for k in run: B[k] = B[k].replace('<div class="p">', '<div class="bullet">', 1)

# --- сегменти: глави и проекти
segs = []; i = 0
while i < len(B):
    b = B[i]
    if b.startswith('<div class="eyebrow">'):
        segs.append(['chap', strip(b), []]); i += 1; continue
    m = re.match(r'<div class="pnum">ПРОЕКТ (\d+) / 50', b)
    if m: segs.append(['proj', int(m.group(1)), []]); i += 1; continue
    if segs: segs[-1][2].append(b)
    i += 1

BOLD_ONLY = re.compile(r'^<div class="(p|small|tiny)">(\s*<b>[^<]*</b>\s*)+</div>$')
def is_head(l): return bool(re.match(r'<div class="(h1|h2|h3|h4|sec)"', l)) or bool(BOLD_ONLY.match(l))
def is_caption(l): return l.startswith('<div class="tiny"><b>Изделие:')
def keep_with_next(lines):
    out = []; k = 0
    while k < len(lines):
        l = lines[k]
        if is_head(l) or is_caption(l):
            grp = [l]; k += 1
            while k < len(lines) and (is_head(lines[k]) or is_caption(lines[k])) and len(grp) < 4: grp.append(lines[k]); k += 1
            if k < len(lines) and 'class="long"' not in lines[k]: grp.append(lines[k]); k += 1
            out.append('<div class="kw">' + ''.join(grp) + '</div>'); continue
        out.append(l); k += 1
    return out

tid = [0]; toc = []; diffs = {}
def nid(): tid[0] += 1; return f't{tid[0]}'

def render_chap(label, lines):
    if label.startswith('ГЛАВА'):
        num, name = [x.strip() for x in label.split('·', 1)]; num = num.capitalize(); name = name.capitalize()
        rest = lines
    else:  # „За читателя“: името е първото h1
        num = label.capitalize(); name = strip(lines[0]); rest = lines[1:]
    a = nid(); toc.append((a, 'c', f'{num} · {name}' if label.startswith('ГЛАВА') else name))
    rest = [re.sub(r'^<div class="h1">', '<div class="sec">', l) for l in rest]
    items = keep_with_next(rest)
    return f'<section class="chap"><div class="kw"><div class="cnum" id="{a}">{num}</div><div class="cname">{html.escape(name)}</div>' + (items[0] if items else '') + '</div>' + '\n'.join(items[1:]) + '</section>'

def render_proj(num, lines):
    title = strip(lines[0]); l2, l3, l4 = strip(lines[1]), strip(lines[2]), strip(lines[3])
    time = re.search(r'Време:\s*(.+)', l2).group(1)
    time = time.replace('без времето за втвърдяване', '+ съхнене').replace('без времето за съхнене', '+ съхнене').strip()
    hrs = [int(x) for x in re.findall(r'\d+', time.split('ч')[0])]; mx = max(hrs) if hrs else 0
    lvl = 1 if mx <= 6 else (2 if mx <= 12 else 3)
    if any(w in title.lower() for w in ADV_WORDS): lvl = 3
    orig = l2.split('Трудност:')[1].split('·')[0].strip()
    lvl = max(lvl, {'Начинаещ': 1, 'Средно напреднал': 2, 'Напреднал': 3}.get(orig, 1))
    diffs[num] = (title, orig, LEVELS[lvl], time)
    dim = l3.replace('Габарит:', '').strip(); dmain = dim.split('(')[0].strip()
    dsub = dim[dim.find('(')+1:dim.rfind(')')] if '(' in dim else ''
    con = l4.replace('Конструкция:', '').strip().split('. ')[0].rstrip('.')
    return lvl, title, f'''<div class="ph" id="P{num}"><div class="num">{num:02d}</div><div><div class="kick">ПРОЕКТ · {LEVELS[lvl].upper()}</div><div class="tit">{html.escape(title)}</div></div></div>
<div class="info"><div class="cell">{bars(lvl)}<div><div class="lab">Трудност</div><div class="val">{LEVELS[lvl]}</div></div></div>
<div class="cell">{I_TIME}<div><div class="lab">Време</div><div class="val">{html.escape(time)}</div></div></div>
<div class="cell">{I_DIM}<div><div class="lab">Габарит</div><div class="val">{html.escape(dmain)}<br><span class="sm">{html.escape(dsub)}</span></div></div></div>
<div class="cell">{I_CON}<div><div class="lab">Конструкция</div><div class="val">{html.escape(con)}</div></div></div></div>
''' + '\n'.join(keep_with_next(lines[4:]))

chaps = [s for s in segs if s[0] == 'chap']; projs = [s for s in segs if s[0] == 'proj' and s[1] not in TO_PDF]
part1 = [c for c in chaps if not re.match(r'ГЛАВА [6-9]', c[1])]; part3 = [c for c in chaps if re.match(r'ГЛАВА [6-9]', c[1])]
from relabel import relabel
os.makedirs('out/img2', exist_ok=True)
pre = sorted([(render_proj(n, l), n, l) for _, n, l in projs], key=lambda x: (x[0][0], x[1]))
NEWNUM = {n: k + 1 for k, (_, n, _) in enumerate(pre)}
RELOG = {}
def renum(n, l):
    new = NEWNUM[n]; out = []
    for x in l:
        m = re.search(r'src="img/([^"]+)"', x)
        if m:
            dst = f'out/img2/{m.group(1)}'
            if not os.path.exists(dst + '.done'):
                RELOG[m.group(1)] = relabel(f'out/img/{m.group(1)}', dst, n, new); open(dst + '.done', 'w').write(str(new))
            x = x.replace(f'src="img/{m.group(1)}"', f'src="img2/{m.group(1)}"')
        out.append(x)
    return out
pr = [((lambda r: (r[0], r[1], r[2].replace(f'<div class="num">{n:02d}</div>', f'<div class="num">{NEWNUM[n]:02d}</div>', 1)))(render_proj(n, renum(n, l))), n) for _, n, l in pre]
json.dump(RELOG, open('out/relabel_log.json', 'w', encoding='utf-8'), ensure_ascii=False)

def part(roman, name):
    a = nid(); toc.append((a, 'part', f'Част {roman} · {name}'))
    return f'<section class="part"><div class="pn" id="{a}">Част {roman}</div><div class="pt">{name}</div></section>'

notes = json.load(open('out/notes_lines.json')) if os.path.exists('out/notes_lines.json') else {}
def notes_html(n):
    k = int(notes.get(str(n), 0))
    if k < 3: return f'<div class="nend" data-p="{n}"></div>'
    return f'<div class="notes"><div class="t">МОИТЕ РАЗМЕРИ И БЕЛЕЖКИ</div>' + '<div class="ln"></div>' * (k - 1) + f'</div><div class="nend" data-p="{n}"></div>'

out = [part('I', 'Основите')] + [render_chap(c[1], c[2]).replace('<section class="chap">', '<section class="chap cont">', 1) for c in part1] + [part('II', 'Проекти')]
cur = None
for (lvl, title, h), n in pr:
    if lvl != cur:
        cur = lvl; toc.append((None, 'g', f'{bars(lvl)} {GROUPS[lvl]}'))
    toc.append((f'P{n}', 'p', f'{NEWNUM[n]:02d}. {title}'))
    out.append(f'<section class="proj">{h}{notes_html(n)}</section>')
out += [part('III', 'След проектите')] + [render_chap(c[1], c[2]).replace('<section class="chap">', '<section class="chap cont">', 1) for c in part3]
from hicons import HI, pick
def hicon(m):
    return f'<div class="h3"><svg viewBox="0 0 24 24" class="hi">{HI[pick(strip(m.group(1)))]}</svg>{m.group(1)}</div>'
out = [re.sub(r'<div class="h3">(.*?)</div>', hicon, x) for x in out]
body = '\n'.join(out)
json.dump(diffs, open('out/diffs.json', 'w', encoding='utf-8'), ensure_ascii=False)

def li(a, k, l):
    if k == 'g': return f'<li class="tg">{l}</li>'
    return f'<li class="t{k}"><a href="#{a}">{html.escape(l)}</a></li>'
toc_html = ''.join(li(*x) for x in toc)
pdf_names = {int(n): re.sub(r'\s+', ' ', t).strip() for n, t in re.findall(r'(\d{2})\.\s+([^\n]+)', open('src/ms_plain.txt', encoding='utf-8').read().split('Глава 6')[0])}
import qrcode
BONUS_URL = 'https://drive.google.com/drive/folders/1ujyGB_OuwJck3UBo_aE7FFSb8s6vO8l9'
TOTAL = 101; MORE = TOTAL - len(pr)
_q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0); _q.add_data(BONUS_URL); _q.make(fit=True); _n = _q.modules_count
_qs = max(30, _n * 0.9)
QRSVG = (f'<svg viewBox="0 0 {_n} {_n}" style="width:{_qs:.1f}mm;height:{_qs:.1f}mm;display:block;margin:0 auto" shape-rendering="crispEdges"><g fill="#000">'
         + ''.join(f'<rect x="{c}" y="{r}" width="1.02" height="1.02"/>' for r, row in enumerate(_q.modules) for c, v in enumerate(row) if v) + '</g></svg>')
bonus = (f'<section class="bonus"><div class="cnum">Бонус</div><div class="cname">Още {MORE} проекта в PDF</div>'
         f'<div class="p">Освен {len(pr)}-те проекта в тази книга, получаваш още {MORE} проекта като допълнителни PDF материали - '
         'в същия вид: схема, разкрой, крепежи и стъпки, подредени от лесни към майсторски.</div>'
         f'<div class="qrb"><div class="qrbox">{QRSVG}</div><div class="qrt">Сканирай кода с камерата на телефона,<br>за да отвориш PDF бонусите.</div>'
         '</div></section>')

css = f"""
@page {{ size: 148mm 210mm; bleed: 5mm; margin: 15mm 14mm 16mm 14mm; @bottom-center {{ content: counter(page); font: 8.5pt Inter; }} }}
@page :left {{ margin-left: 14mm; margin-right: 19mm; }} @page :right {{ margin-left: 19mm; margin-right: 14mm; }}
@page nonum {{ @bottom-center {{ content: none; }} }} @page full {{ margin: 0; @bottom-center {{ content: none; }} }}
html {{ font-family: Lora; font-size: {FONT}pt; line-height: {LEAD}; color: #000; hyphens: auto; }} body {{ margin: 0; }}
.p {{ margin: 0 0 .4em; text-align: justify; orphans: 2; widows: 2; }}
.small {{ font-size: .9em; margin: 0 0 .35em; }} .tiny {{ font-size: .82em; margin: 0 0 .25em; }}
.bullet {{ margin: 0 0 .2em; padding-left: 1.1em; text-indent: -.8em; }} .bullet::before {{ content: '•'; display: inline-block; width: .8em; text-indent: 0; }}
.kw {{ break-inside: avoid; }}
.h1, .h2, .h3, .h4, .sec {{ font-family: Inter; break-after: avoid; line-height: 1.2; hyphens: manual; }}
.sec {{ font-size: 1.3em; font-weight: 800; margin: 1.1em 0 .45em; }} .h1 {{ font-size: 1.3em; font-weight: 800; margin: 1em 0 .45em; }}
.h2 {{ font-size: 1.12em; font-weight: 700; margin: .9em 0 .35em; }} .h3 {{ font-size: 1em; font-weight: 700; margin: .7em 0 .25em; }} .h4 {{ font-size: .93em; font-weight: 700; margin: .6em 0 .2em; }}
.chap, .bonus {{ break-before: page; }} .chap.cont {{ break-before: auto; margin-top: 7mm; }} .part + .chap.cont {{ margin-top: 0; }}
.cnum {{ font: 700 8.5pt Inter; letter-spacing: .18em; text-transform: uppercase; margin: 6mm 0 1.5mm; }}
.cname {{ font: 800 26pt/1.05 Inter; hyphens: none; padding-bottom: 3mm; border-bottom: 1.2pt solid #000; margin-bottom: 5mm; break-after: avoid; }}
.chap > .kw:first-of-type .sec, .chap > .sec:first-of-type {{ margin-top: 0; }}
.part {{ page: nonum; break-before: page; break-after: page; padding-top: 62mm; text-align: center; }}
.part .pn {{ font: 700 11pt Inter; letter-spacing: .25em; text-transform: uppercase; }} .part .pt {{ font: 800 32pt/1.1 Inter; margin-top: 4mm; }}
.imgp {{ margin: .4em 0; break-inside: avoid; }} .imgp img {{ display: block; margin: 0 auto; }} .tiny:has(img.plate), img.plate {{ display: block; margin: 0 auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: .8em; line-height: 1.25; margin: .3em 0 .6em; }}
table.keep {{ break-inside: avoid; }} td, th {{ border: .35pt solid #000; padding: 1.2pt 3pt; vertical-align: top; text-align: left; }}
th {{ background: #e6e6e6; }} thead {{ display: table-header-group; }} tr {{ break-inside: avoid; }}
.proj {{ break-before: page; }}
.ph {{ display: flex; align-items: flex-end; gap: 4mm; border-bottom: 1.2pt solid #000; padding-bottom: 2.5mm; margin-bottom: 3mm; }}
.ph .num {{ font: 800 40pt/0.8 Inter; letter-spacing: -.02em; }}
.ph .kick {{ font: 700 7.5pt Inter; letter-spacing: .16em; margin-bottom: 1.2mm; }} .ph .tit {{ font: 800 16pt/1.1 Inter; hyphens: none; }}
.info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2.5mm 4mm; background: #efefef; border-radius: 2mm; padding: 3mm 3.5mm; margin-bottom: 3mm; }}
.cell {{ display: flex; gap: 2.5mm; align-items: flex-start; }} .cell .ic {{ width: 8mm; height: 8mm; flex: none; }}
.lab {{ font: 700 6.8pt Inter; letter-spacing: .12em; text-transform: uppercase; color: #333; }}
.val {{ font: 600 8.4pt/1.25 Inter; hyphens: manual; }} .sm {{ font: 400 6.6pt Inter; color: #333; }}
.notes {{ margin-top: 4mm; break-inside: avoid; }} .notes .t {{ font: 700 7.2pt Inter; letter-spacing: .12em; height: {LINE_MM}mm; border-bottom: .5pt solid #777; box-sizing: border-box; }}
.notes .ln {{ border-bottom: .5pt solid #777; height: {LINE_MM}mm; box-sizing: border-box; }}
.nend {{ height: 0; }} table.trk {{ font-size: .78em; }} table.trk td {{ height: 4.1mm; padding: .6pt 3pt; }} table.trk td:nth-child(3), table.trk td:nth-child(4) {{ width: 18mm; }}
.qrb {{ margin-top: 10mm; text-align: center; break-inside: avoid; }} .qrbox {{ display: inline-block; padding: 4mm; border: .6pt solid #000; border-radius: 2mm; }}
.qrt {{ font: 600 9pt/1.35 Inter; margin-top: 4mm; }} .qru {{ font: 400 6.5pt Inter; margin-top: 2mm; color: #333; word-break: break-all; }}
.h3 .hi {{ width: 4.4mm; height: 4.4mm; vertical-align: -1mm; margin-right: 1.6mm; }}
.front {{ page: nonum; break-after: page; }}
.title {{ text-align: center; padding-top: 42mm; height: 150mm; position: relative; }}
.title .t {{ font: 800 21pt/1.15 Inter; text-transform: uppercase; hyphens: none; }} .title .s {{ font: 400 10.5pt/1.35 Lora; margin-top: 6mm; }}
.title .pub {{ position: absolute; bottom: 0; width: 100%; font: 400 10pt Inter; }}
.imprint {{ font-size: 8pt; line-height: 1.4; padding-top: 70mm; }} .imprint .p {{ text-align: left; }}
.toc {{ page: nonum; }} .toc .cname {{ font-size: 20pt; margin-bottom: 3mm; }}
.toc ul {{ list-style: none; padding: 0; font-size: .78em; line-height: 1.22; }}
.toc li.tpart {{ font: 800 .95em Inter; letter-spacing: .08em; text-transform: uppercase; margin-top: .9em; }}
.toc li.tc {{ margin-left: 0; }} .toc li.tg {{ font: 700 .9em Inter; margin: .5em 0 .1em; }} .toc li.tg .ic {{ width: 4.2mm; height: 3.6mm; vertical-align: -.6mm; }}
.toc li.tp {{ margin-left: 3mm; }} .toc a {{ color: #000; text-decoration: none; }}
.toc a::after {{ content: leader('.') target-counter(attr(href), page); }}
.ad {{ page: full; break-before: page; height: 210mm; border: 2pt dashed #000; box-sizing: border-box; display: flex; align-items: center; justify-content: center; text-align: center; font: 600 12pt Inter; padding: 15mm; }}
.last {{ page: nonum; break-before: page; text-align: center; padding-top: 55mm; font: 400 9pt/1.5 Inter; }} .last .t {{ font-weight: 800; font-size: 11.5pt; text-transform: uppercase; }}
.legend {{ break-inside: avoid; font: 400 .85em Inter; margin: .3em 0 .8em; }} .legend .ic {{ width: 6mm; height: 5mm; vertical-align: -1.2mm; }}
"""
legend = (f'<div class="legend"><b>Нива на трудност:</b><br>{bars(1)} Начинаещ - до 6 ч, винтове и лепило<br>'
          f'{bars(2)} Средно напреднал - до 12 ч или по-сложни сглобки<br>{bars(3)} Напреднал - над 12 ч, чекмеджета, врати и механизми</div>')
body = body.replace('<div class="kw"><div class="h3">Обозначения</div>', legend + '<div class="kw"><div class="h3">Обозначения</div>', 1)
TM = ('Търговските марки, уебсайтовете, наименованията на продукти и услуги, както и всяка друга интелектуална собственост, която е включена в изображение, '
      'използвано в тази книга, принадлежи на съответните компании и е защитена от международното авторско право. Изображенията са използвани с цел даване '
      'на конкретни примери от практиката и не следва да се тълкуват като препоръка или одобрение към книгата от страна на съответната компания.')
front = f"""<section class="front title"><div class="t">{TITLE}</div><div class="s">{SUB}</div><div class="pub">Издателство Златен Ключ<br>София, 2026</div></section>
<section class="front imprint"><div class="p">{TM}</div><div class="p"><b>{TITLE.upper()}</b><br>{SUB}</div><div class="p">Първо издание</div>
<div class="p">{ISBN}<br>София, 2026</div><div class="p">Всички права запазени © Издателство Златен Ключ, 2026<br>Моля, не възпроизвеждай, не копирай и не разпространявай
съдържанието на тази книга по какъвто и да е начин без изричното съгласие на издателството!</div></section>
<section class="toc"><div class="cname">Съдържание</div><ul>{toc_html}</ul></section>"""
tracker = ('<section class="bonus"><div class="cnum">Моят дневник</div><div class="cname">Моите проекти</div>'
           '<table class="trk"><thead><tr><th>№</th><th>Проект</th><th>Започнат</th><th>Готов ✓</th></tr></thead><tbody>'
           + ''.join(f'<tr><td>{NEWNUM[n]:02d}</td><td>{html.escape(t)}</td><td></td><td></td></tr>' for (lv, t, h), n in pr) + '</tbody></table></section>')
back = tracker + bonus + f"""<section class="ad">СТРАНИЦА 161 - РЕКЛАМА НА КУРСА<br>(от стария печатен файл)</section>
<section class="last"><div class="t">{TITLE}</div><div>{SUB}</div><br><div>Първо издание</div><div>{ISBN}</div><div>София, 2026</div><br><div>Всички права запазени © Издателство Златен Ключ, 2026</div></section>"""
open('out/v3.html', 'w', encoding='utf-8').write(f'<!doctype html><html lang="bg"><head><meta charset="utf-8"><style>{css}</style></head><body>{front}<main>{body}</main>{back}</body></html>')
doc = HTML('out/v3.html', base_url='out/').render(); doc.metadata.title = TITLE

# --- измерване: колко линии за бележки се побират до края на страницата след всеки проект
PX_MM = 25.4 / 96; res = {}
for pg in doc.pages:
    pb = pg._page_box; bottom = pb.content_box_y() + pb.height
    for bx in pb.descendants():
        el = getattr(bx, 'element', None)
        if el is not None and el.get('class') == 'nend':
            # мястото, заето от вече вкараните бележки, се връща към свободното
            free = (bottom - bx.position_y) * PX_MM + int(notes.get(el.get('data-p'), 0)) * LINE_MM + (4 if int(notes.get(el.get('data-p'), 0)) >= 3 else 0)
            full = (pb.height) * PX_MM
            res[el.get('data-p')] = 0 if free > full - 8 else max(0, math.floor((free - 4 - 0.5) / LINE_MM))
json.dump(res, open('out/notes_lines.json', 'w'))
doc.write_pdf('out/v3.pdf'); print('pages', len(doc.pages), 'projects', len(pr))
