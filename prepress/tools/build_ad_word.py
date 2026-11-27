"""Рекламна страница 161: одобрената илюстрация + векторен QR от колони E+F."""
import sys, qrcode, qrcode.image.svg, io
from weasyprint import HTML

URL = sys.argv[1]
ART = sys.argv[2] if len(sys.argv)>2 else 'art-000.jpg'
OUT = sys.argv[3] if len(sys.argv)>3 else 'ad161.pdf'
HEADCSS = sys.argv[4] if len(sys.argv)>4 else 'left: 42mm; width: 75mm; top: 12mm'
CXY = sys.argv[5] if len(sys.argv)>5 else '126.2,188.2'                      # точният URL от таблицата (E+F)
SHOW = URL.replace('https://', '')
HEAD = 'Научи се как да създаваш сам подредени Word документи и ясни PowerPoint презентации, без часове лутане!'

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
qr.add_data(URL); qr.make(fit=True)
mods = qr.modules_count
QR_MM = max(30.0, mods * 1.0)          # тяло на кода >= 30 mm, модул >= 1 mm
mod = QR_MM / mods
rects = ''.join(f'<rect x="{c}" y="{r}" width="1.02" height="1.02"/>'
                for r, row in enumerate(qr.modules) for c, v in enumerate(row) if v)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {mods} {mods}" '
       f'style="width:{QR_MM}mm;height:{QR_MM}mm;display:block" shape-rendering="crispEdges">'
       f'<g fill="#000">{rects}</g></svg>')
QZ = 4 * mod                            # тиха зона 4 модула
BOX = QR_MM + 2 * QZ
CX, CY = map(float, CXY.split(','))                    # център на белия слот в илюстрацията (mm, с наддаване)

css = f"""
@page {{ size: 158mm 220mm; margin: 0; }}
body {{ margin: 0; }}
.pg {{ position: relative; width: 158mm; height: 220mm; overflow: hidden; }}
.art {{ position: absolute; left: 0; top: -3.7mm; width: 158mm; height: 227.4mm; }}
.head {{ position: absolute; {HEADCSS}; text-align: center; background: rgba(255,255,255,.88);
  border-radius: 3mm; padding: 2.5mm 3mm; font: 800 10.5pt/1.22 Inter; text-transform: uppercase; color: #000; }}
.qrbox {{ position: absolute; left: {CX - BOX/2:.2f}mm; top: {CY - BOX/2:.2f}mm; width: {BOX:.2f}mm; height: {BOX:.2f}mm;
  background: #fff; border-radius: 2mm; }}
.qrbox svg {{ position: absolute; left: {QZ:.2f}mm; top: {QZ:.2f}mm; }}
.scan {{ position: absolute; left: {CX - 25:.2f}mm; width: 50mm; top: {CY - BOX/2 - 7:.2f}mm; text-align: center;
  font: 700 9pt Inter; letter-spacing: .12em; color: #000; }}
.scan span {{ background: #fff; border-radius: 1.5mm; padding: .6mm 2.2mm; }}
.cta {{ position: absolute; left: 20mm; top: 186mm; background: #000; color: #fff; border-radius: 3mm;
  font: 800 11pt Inter; padding: 3mm 5mm; text-transform: uppercase; }}
.url {{ position: absolute; left: 20mm; top: 198mm; background: #fff; border-radius: 2mm; padding: 1.2mm 3mm;
  font: 600 8pt Inter; color: #000; }}
"""
html = f"""<!doctype html><html lang="bg"><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="pg"><img class="art" src="{ART}">
<div class="head">{HEAD}</div>
<div class="scan"><span>СКАНИРАЙ МЕ</span></div>
<div class="qrbox">{svg}</div>
<div class="cta">Виж онлайн курса</div>
<div class="url">{SHOW}</div></div></body></html>"""
open('ad.html', 'w', encoding='utf-8').write(html)
HTML('ad.html', base_url='.').write_pdf(OUT)
print(f'modules={mods} module={mod:.2f}mm qr_body={QR_MM:.1f}mm box={BOX:.1f}mm')
