"""Бонус страница 160: илюстрация в стила на рекламната страница + заглавие + QR към бонусите."""
import sys, qrcode
from weasyprint import HTML
URL = 'https://drive.google.com/drive/folders/1ujyGB_OuwJck3UBo_aE7FFSb8s6vO8l9'
MORE, INBOOK = int(sys.argv[1]), int(sys.argv[2])
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0); qr.add_data(URL); qr.make(fit=True); n = qr.modules_count
rects = ''.join(f'<rect x="{c}" y="{r}" width="1.02" height="1.02"/>' for r, row in enumerate(qr.modules) for c, v in enumerate(row) if v)
Q = 34
qrsvg = f'<svg viewBox="0 0 {n} {n}" style="width:{Q}mm;height:{Q}mm;display:block" shape-rendering="crispEdges"><g fill="#000">{rects}</g></svg>'
W, IW, IH = 158, 1024, 1466; H = W * IH / IW; OFF = -(H - 220)  # режем само от тавана
sx = lambda px: px / 655 * W; sy = lambda py: py / 938 * H + OFF
SQ = (sx(433), sy(672), sx(633), sy(885)); BT = (sx(25), sy(843), sx(368), sy(903))
css = f"""
@page {{ size: 158mm 220mm; margin: 0; }}
body {{ margin: 0; }}
.pg {{ position: relative; width: 158mm; height: 220mm; overflow: hidden; }}
.art {{ position: absolute; left: 0; top: {OFF:.2f}mm; width: {W}mm; height: {H:.2f}mm; }}
.card {{ position: absolute; left: 10mm; top: 10mm; width: 64mm; background: rgba(255,255,255,.94); border: .4mm solid #000;
  border-radius: 3mm; padding: 3.4mm 4.5mm 3.6mm; font-family: Inter; }}
.k {{ font: 700 7.5pt Inter; letter-spacing: .2em; }}
.t {{ font: 800 19pt/1.02 Inter; margin: 1.6mm 0 2mm; }}
.s {{ font: 400 8pt/1.3 Inter; }}
.qr {{ position: absolute; left: {(SQ[0]+SQ[2])/2 - Q/2:.2f}mm; top: {SQ[1] + 4.5:.2f}mm; }}
.sc {{ position: absolute; left: {SQ[0]:.2f}mm; width: {SQ[2]-SQ[0]:.2f}mm; top: {SQ[1] + 4.5 + Q + 1.6:.2f}mm; text-align: center; font: 800 7.6pt Inter; letter-spacing: .12em; }}
.bt {{ position: absolute; left: {BT[0]:.2f}mm; width: {BT[2]-BT[0]:.2f}mm; top: {BT[1]:.2f}mm; height: {BT[3]-BT[1]:.2f}mm;
  display: flex; align-items: center; justify-content: center; color: #fff; font: 800 10.5pt Inter; letter-spacing: .04em; }}
"""
html = f"""<!doctype html><html lang="bg"><head><meta charset="utf-8"><style>{css}</style></head><body><div class="pg">
<img class="art" src="bonus_art.png">
<div class="card"><div class="k">БОНУС</div><div class="t">Още {MORE} проекта<br>в PDF</div>
<div class="s">Освен {INBOOK}-те проекта в книгата - схема, разкрой, крепежи и стъпки, от лесни до майсторски.</div></div>
<div class="qr">{qrsvg}</div><div class="sc">СКАНИРАЙ МЕ</div>
<div class="bt">ОТВОРИ PDF БОНУСИТЕ</div>
</div></body></html>"""
open('bonus.html', 'w', encoding='utf-8').write(html)
HTML('bonus.html', base_url='.').write_pdf('mebeli_bonus160.pdf')
print('ok', SQ, BT)
