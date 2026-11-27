# Предпечат (Claude) - код

Процесът и правилата са в Google Drive: 01_Management/01_Processes/Production/Prepress Processes,
документ „Предпечат с Claude - процес и правила“. Първо се чете той, после този код.

## Работна папка
Всичко се пуска от работна папка на книгата (напр. /home/claude/<book>) с подпапки:
- `src/ms.docx` - ръкописът (от колона G на Copywriting Tasks)
- `out/` - генерирано (body.html, img/, img2/, v3.html, v3.pdf, notes_lines.json)
- `ad/` - страници 160 и 161 като отделни PDF с bleed (158x220 мм)
- `deliver/` - пробните набори за Bran

Скриптовете се копират в работната папка (пускат се с относителни пътища).

## Ред на пускане
```bash
python3 convert.py                       # docx -> out/body.html + out/img (сиви)
export EXTRA_PDF=3,7,11                  # номерата на проектите от ръкописа, които отиват в PDF бонуса
rm -rf out/img2 out/notes_lines.json     # при всяка смяна на подбора на проекти!
python3 build4.py 9.7 1.32               # шрифт pt, междуредие -> out/v3.html, out/v3.pdf
python3 en_pass.py                       # маха останали английски думи от картинките в out/img2
python3 build4.py 9.7 1.32               # 2-ри и 3-ти пас: бележките се мерят от предишния пас
python3 build4.py 9.7 1.32
python3 ad/build_bonus.py 71 30          # стр. 160 (още N проекта, проекти в книгата)
# вмъкване на стр. 160 и 161 (pypdf, TrimBox 5,5,153,215 мм) -> deliver/<BOOK>_162_PROBEN_NABOR_vNN.pdf
python3 check_pages.py deliver/<file>.pdf   # сираци и заглавия най-долу - трябва да е празно
python3 check_layout.py                     # разделени таблици - SPLIT: []
```

## Файлове
- `convert.py` - docx -> HTML по стиловете на Ани (H1/H2/H3/Body/Small/Tiny/Bullet/Eyebrow/ProjectNum/Image)
- `build4.py` - набор в WeasyPrint: почистване, части/глави/проекти, иконки, бележки, страници 159-162
- `hicons.py` - иконките на подзаглавията + правилата коя иконка за кое заглавие (EXACT и RULES)
- `relabel.py` - пренаписва „ПРОЕКТ NN“ и ъгловия номер в картинките, маха английски думи (OCR)
- `en_pass.py` - втори пас за английски думи
- `check_pages.py`, `check_layout.py` - автоматичните проверки
- `build_bonus.py` - страница 160 (илюстрация + каре + QR + бутон)
- `build_ad_word.py` - страница 161 за Word & PowerPoint (пример за рекламна страница от код)
- `books/MEBELI_V2/` - одобрените страници 160/161 и илюстрацията за Мебели V2

`build4.py` още съдържа неща, специфични за Мебели V2 (TO_PDF, TOTAL=101, BONUS_URL, ADV_WORDS,
ръчни поправки на ръкописа). За нова книга те се сменят в началото на файла.
