# -*- coding: utf-8 -*-
"""낱장 확대 판독 — python tools/tex_zoom.py <출력.png> <칸폭> <열수> 번호…"""
import sys, os
from PIL import Image, ImageDraw, ImageFont
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'tex')
out, CW, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); ns = sys.argv[4:]
L = {l.split('\t')[1]: l.split('\t') for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:] if l}
f = ImageFont.truetype('C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf', 14)
ims = []
for n in ns:
    r = L[n]; im = Image.open(os.path.join(T, 'png', r[2] + '.png')).convert('RGBA'); bb = im.getbbox() or (0, 0, im.width, im.height); c = im.crop(bb)
    s = (CW - 6) / c.width; c = c.resize((CW - 6, max(1, int(c.height * s))), Image.BICUBIC); ims.append((n, r, c))
rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]; H = sum(max(c.height for _, _, c in r) + 20 for r in rows)
pg = Image.new('RGB', (cols * CW, H), (70, 80, 100)); d = ImageDraw.Draw(pg); y = 0
for r in rows:
    for i, (n, q, c) in enumerate(r):
        pg.paste(c, (i * CW + 3, y + 18), c); d.text((i * CW + 3, y + 1), n + ' ' + q[3] + 'x' + q[4], font=f, fill=(255, 230, 90))
    y += max(c.height for _, _, c in r) + 20
pg.save(out); print(pg.size)
