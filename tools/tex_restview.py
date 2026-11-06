# -*- coding: utf-8 -*-
"""남은 판 미리보기 — work/tex/미리보기_남은것/<이름>.png (원본|새것)."""
import os
from PIL import Image, ImageDraw, ImageFont
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'tex')
OUT = os.path.join(T, '미리보기_남은것'); os.makedirs(OUT, exist_ok=True)
L = {}
for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) > 2: L[c[1]] = c
F = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 14)
G = [('01_돌글자', ['102846', '102847', '102878', '102879', '102880']), ('02_지도_큰판', ['102300', '101922']),
     ('03_지도_128판', ['102616', '102653', '102654', '2935', '102618', '102619', '102621', '102801', '103196', '103232', '103395']),
     ('04_지도_64축소', ['104767', '104797', '105765', '101923', '101769', '101809', '102487']),
     ('05_기술서표지', ['100930', '100931', '101008', '101009', '101010', '101011', '101012', '101013', '101014', '101015', '101016', '101017', '101018'])]
for name, ns in G:
    S = 620 if name.startswith('02') else 300; cols = 1 if S > 300 else 2; rows = -(-len(ns) // cols); cw = 2 * S + 30; ch = S + 28
    pg = Image.new('RGB', (cw * cols, ch * rows), (86, 96, 120)); d = ImageDraw.Draw(pg)
    for i, n in enumerate(ns):
        x, y = (i % cols) * cw + 5, (i // cols) * ch
        d.text((x, y + 3), '%s  (왼쪽 원본 | 오른쪽 새것)' % n, font=F, fill=(255, 235, 120))
        for k, dn in enumerate(('png', 'new')):
            p = os.path.join(T, dn, L[n][2] + '.png')
            if not os.path.exists(p):
                d.text((x + k * (S + 12), y + 40), '없음', font=F, fill=(255, 80, 80)); continue
            im = Image.open(p).convert('RGBA'); c = im.crop(im.getbbox()); s = S / max(c.size)
            c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS); pg.paste(c, (x + k * (S + 12), y + 24), c)
    tmp = os.path.join(OUT, '_tmp.png'); pg.save(tmp); os.replace(tmp, os.path.join(OUT, name + '.png'))
print('ok', len(G))
