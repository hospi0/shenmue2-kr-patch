# -*- coding: utf-8 -*-
"""아직 눈으로 안 본 텍스처(후보 시트 밖) 시트 — 글자판 점수 높은 순. python tools/tex_rest.py [장당 칸수 열수] → work/tex/전수/REST_NN.png + rest_ids.tsv(번호→id)"""
import os, sys, collections
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = os.path.join(ROOT, 'work', 'tex'); O = os.path.join(T, '전수'); os.makedirs(O, exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8')
rev = set(l.split('\t')[1] for l in open(os.path.join(T, 'review', 'ids.tsv'), encoding='utf-8') if '\t' in l)
sc = {}
for l in open(os.path.join(T, 'textlike.tsv'), encoding='utf-8'):
    c = l.rstrip('\n').split('\t')
    if len(c) > 1:
        try: sc[c[1]] = float(c[0])
        except ValueError: pass
idx = [l.split('\t') for l in open(os.path.join(T, 'index.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
rest = [r for r in idx if r[0] not in rev and r[6] not in ('HANGON',)]
rest.sort(key=lambda r: -sc.get(r[0], 0))
h = collections.Counter(min(int(sc.get(r[0], 0) * 20), 10) for r in rest); print(len(rest), sorted(h.items()))
per, cols, cell = 216, 18, 80
f = ImageFont.truetype('C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf', 10)
w = open(os.path.join(T, '전수', 'rest_ids.tsv'), 'w', encoding='utf-8', newline='\n'); n = 0
for p in range(0, len(rest), per):
    ch = rest[p:p + per]; pg = Image.new('RGB', (cols * cell, ((len(ch) + cols - 1) // cols) * cell), (60, 66, 80)); d = ImageDraw.Draw(pg)
    for i, r in enumerate(ch):
        n += 1; w.write('%d\t%s\n' % (n, r[0]))
        im = Image.open(os.path.join(T, 'png', r[0] + '.png')).convert('RGBA'); im.thumbnail((cell - 3, cell - 12), Image.LANCZOS)
        x, y = (i % cols) * cell, (i // cols) * cell; pg.paste(im, (x + 1, y + 11), im); d.text((x + 1, y), str(n), font=f, fill=(255, 230, 90))
    pg.save(os.path.join(O, 'REST_%02d.png' % (p // per)))
print('시트', (len(rest) + per - 1) // per)
