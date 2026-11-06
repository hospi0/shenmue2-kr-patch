# -*- coding: utf-8 -*-
"""지도 확대 미리보기 — work/tex/미리보기_지도확대/<묶음>_<번호>_<이름>.png
한 장에 한 지도, 원본|새것을 긴 변 약 1024 화소로 키움. 돌아간 판은 읽는 방향으로 돌림. 64 판은 큰 판 축소라 뺌."""
import os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'tex'); OUT = os.path.join(T, '미리보기_지도확대'); os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
names = {}
for f in os.listdir(os.path.join(T, '번역')):
    if f.endswith('.tsv'):
        for l in open(os.path.join(T, '번역', f), encoding='utf-8'):
            c = l.rstrip('\n').split('\t')
            if len(c) > 2 and c[2] not in ('', '-', '?'): names[c[0]] = c[2]
L = {}
for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) > 3: L[c[1]] = c
EXTRA = {'1279', '1679', '1815', '970'}                              # 지도에 붙는 글자판
B5MAP = {'102300', '101922', '102616', '102618', '102619', '102621', '102653', '102654', '102801', '103196', '103232', '103395'}
ROT = {'102653': -90, '102654': -90, '2935': -90, '101922': 90}      # 읽는 방향으로
F = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 24)
cnt = 0
for n, c in L.items():
    if not (c[0].startswith('C1') or n in EXTRA or n in B5MAP): continue
    a, b = (os.path.join(T, d, c[2] + '.png') for d in ('png', 'new'))
    if not os.path.exists(b): continue
    A, B = Image.open(a).convert('RGBA'), Image.open(b).convert('RGBA')
    if A.width < 128 and A.height < 128: continue
    if A.size != B.size or not (np.array(A) != np.array(B)).any(): continue
    if n in ROT: A, B = A.rotate(ROT[n], expand=True), B.rotate(ROT[n], expand=True)
    bb = A.getbbox(); A, B = A.crop(bb), B.crop(bb)
    k = max(1, round(1024 / max(A.size))); w, h = A.width * k, A.height * k
    pg = Image.new('RGB', (w * 2 + 30, h + 44), (86, 96, 120)); d = ImageDraw.Draw(pg)
    nm = names.get(n, '').replace('／', ' ')
    d.text((8, 6), '%s  %s  x%d  (왼쪽 원본 | 오른쪽 새것)' % (n, nm, k), font=F, fill=(255, 235, 120))
    for i, im in enumerate((A, B)):
        r = im.resize((w, h), Image.LANCZOS); pg.paste(r, (i * (w + 30), 44), r)
    safe = re.sub(r'[\\/:*?"<>|\n ]+', '_', nm)[:24]
    pg.save(os.path.join(OUT, '%s_%s_%s.png' % (c[0][:2], n, safe))); cnt += 1
print('ok', cnt)
