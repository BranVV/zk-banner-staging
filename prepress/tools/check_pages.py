"""Проверка за страници с 1-3 реда (сираци) в PDF."""
import sys, subprocess, re, pypdf
f = sys.argv[1]; r = pypdf.PdfReader(f); bad = []
for i in range(len(r.pages)):
    t = subprocess.run(['pdftotext', '-f', str(i+1), '-l', str(i+1), '-layout', f, '-'], capture_output=True, text=True).stdout
    lines = [l for l in t.split('\n') if l.strip() and not re.fullmatch(r'\s*\d{1,3}\s*', l)]
    imgs = len(subprocess.run(['pdfimages', '-f', str(i+1), '-l', str(i+1), '-list', f], capture_output=True, text=True).stdout.strip().split('\n')) - 2
    if len(lines) <= 3 and not imgs: bad.append((i+1, [l.strip()[:50] for l in lines]))
import json
ok = ('ЧАСТ I', 'ЧАСТ II', 'ЧАСТ III', 'СТРАНИЦА 161')
bad = [b for b in bad if not (b[1] and b[1][0].startswith(ok))]
# заглавие като последен ред на страница
html_ = open('out/v3.html', encoding='utf-8').read() if len(sys.argv) < 3 else open(sys.argv[2], encoding='utf-8').read()
heads = set(re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<div class="(?:h1|h2|h3|sec|cnum|cname)"[^>]*>(.*?)</div>', html_))
N = lambda x: re.sub(r'\s+', '', x).upper()
heads = {N(h) for h in heads if h}
for i in range(len(r.pages)):
    t = subprocess.run(['pdftotext', '-f', str(i+1), '-l', str(i+1), f, '-'], capture_output=True, text=True).stdout
    lines = [l.strip() for l in t.split('\n') if l.strip() and not re.fullmatch(r'\s*\d{1,3}\s*', l)]
    if lines and N(lines[-1]) in heads: bad.append((i+1, ['ЗАГЛАВИЕ НАЙ-ДОЛУ: ' + lines[-1]]))
for b in bad: print(b)
