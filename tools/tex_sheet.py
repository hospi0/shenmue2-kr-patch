# -*- coding: utf-8 -*-
"""판독용 확대 시트 — python tools/tex_sheet.py <출력.png> <묶음 앞글자…> [칸폭 칸높이 열수]  (work/tex 기준)"""
import sys, os
from PIL import Image, ImageDraw, ImageFont
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'tex')
out = sys.argv[1]; args = sys.argv[2:]; nums = [a for a in args if a.isdigit()]; pre = [a for a in args if not a.isdigit()]
CW, CH, cols = (int(nums[0]), int(nums[1]), int(nums[2])) if len(nums) >= 3 else (240, 170, 6)
L = [l.split('\t') for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
f = ImageFont.truetype('C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf', 13)
g = [r for r in L if r[0][:2] in pre]
pg = Image.new('RGB', (cols * CW, ((len(g) + cols - 1) // cols) * CH), (70, 80, 100)); d = ImageDraw.Draw(pg)
for i, r in enumerate(g):
    im = Image.open(os.path.join(T, 'png', r[2] + '.png')).convert('RGBA'); bb = im.getbbox() or (0, 0, im.width, im.height); c = im.crop(bb)
    s = min((CW - 6) / c.width, (CH - 22) / c.height, 4); c = c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS)
    x = (i % cols) * CW; y = (i // cols) * CH
    pg.paste(c, (x + 3, y + 18), c); d.text((x + 3, y + 1), '%s %s %sx%s' % (r[0][:2], r[1], r[3], r[4]), font=f, fill=(255, 230, 90))
pg.save(out); print(pg.size, len(g))
