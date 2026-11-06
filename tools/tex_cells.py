# -*- coding: utf-8 -*-
"""글자 모음 판 칸 찾기 — 투명 판의 글자 덩어리 상자에 번호를 매겨 시트로. python tools/tex_cells.py <출력.png> 번호…  (상자는 work/tex/칸상자.tsv 에 누적)"""
import sys, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'tex')
L = {l.split('\t')[1]: l.split('\t') for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:] if l}
f = ImageFont.truetype('C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf', 12)
out = sys.argv[1]; pages = []; rows = []
for n in sys.argv[2:]:
    a = np.array(Image.open(os.path.join(T, 'png', L[n][2] + '.png')).convert('RGBA'))
    m = (a[..., 3] > 30).astype(np.uint8) if a[..., 3].min() < 255 else (a[..., :3].sum(axis=2) < 300).astype(np.uint8)
    k = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 9), np.uint8)); c, lab, st, _ = cv2.connectedComponentsWithStats(k)
    bx = sorted([tuple(st[i][:4]) for i in range(1, c) if st[i][4] > 12], key=lambda b: (b[1] // 8, b[0]))
    s = max(1, min(3, 700 // a.shape[1])); im = Image.fromarray(a).resize((a.shape[1] * s, a.shape[0] * s), Image.NEAREST); bg = Image.new('RGBA', im.size, (86, 96, 120, 255)); bg.alpha_composite(im); d = ImageDraw.Draw(bg)
    for i, (x, y, w, h) in enumerate(bx):
        d.rectangle((x * s, y * s, (x + w) * s, (y + h) * s), outline=(255, 60, 60)); d.text((x * s + 1, y * s), str(i), font=f, fill=(255, 255, 0)); rows.append('%s\t%d\t%d\t%d\t%d\t%d' % (n, i, x, y, x + w, y + h))
    d.text((2, bg.height - 14), n, font=f, fill=(0, 255, 0)); pages.append(bg)
W = sum(p.width for p in pages[:2]) + 8; H = 0; x = 0; pg = Image.new('RGB', (1440, sum(max(p.height for p in pages[i:i + 2]) + 6 for i in range(0, len(pages), 2))), (20, 20, 20)); y = 0
for i in range(0, len(pages), 2):
    x = 0
    for p in pages[i:i + 2]: pg.paste(p.convert('RGB'), (x, y)); x += p.width + 6
    y += max(p.height for p in pages[i:i + 2]) + 6
pg.save(out)
p = os.path.join(T, '칸상자.tsv'); old = open(p, encoding='utf-8').read().split('\n') if os.path.exists(p) else []
keep = [l for l in old if l and l.split('\t')[0] not in sys.argv[2:]]
open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(keep + rows) + '\n'); print(pg.size, len(rows))
