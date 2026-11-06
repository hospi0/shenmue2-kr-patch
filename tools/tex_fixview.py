# -*- coding: utf-8 -*-
"""지적받아 고친 그림만 모은 미리보기 — work/tex/미리보기_지적수정/<지적>.png (원본|새것, 번호·묶음 라벨).
회전 판은 게임에서 보이는 방향(시계 90도)으로도 돌려서 보여 준다. 표 G 에 지적을 더하면 된다."""
import os
from PIL import Image, ImageDraw, ImageFont
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'tex')
OUT = os.path.join(T, '미리보기_지적수정'); os.makedirs(OUT, exist_ok=True)
L = {}
for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) > 2: L[c[1]] = c
F = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 14)
ROT = {'974', '2879', '1276', '3188', '3450', '3563', '3208', '3218'}
G = [('01_D1_안내판', ['1055', '1499', '1549']), ('02_D2_건물판_글자', ['1322', '1370', '1354', '1375', '1548', '1404', '1450', '1145']),
     ('03_D2_세로간판_게임방향', sorted(ROT, key=int)), ('04_출입금지_계산대', ['1371', '3546']), ('05_새가게거리_옥상이전', ['1329', '1651', '1640', '1705', '1459']),
     ('06_E1_글자판970', ['970']), ('07_전수보충', ['101137', '101464', '102299', '106117', '106137', '106259', '104267', '104759', '104318', '104519', '104788', '105675', '105180']),
     ('08_대결화면_매입불가', ['298', '299', '300', '301', '529']), ('09_타이틀_저장글자판', ['655', '562']), ('10_표지_재수정', ['932', '1436', '1685', '2926']), ('11_손그림지도', ['103', '838', '861', '934', '762', '1090', '2771']),
     ('12_이전지적_안내창_옵션_로고', ['726', '740', '741', '743', '745', '664', '666', '527', '3577', '488', '489', '490', '497']), ('13_이전지적_지도_글자판', ['1279', '1679', '1815', '878', '870', '877', '1098', '1366', '1778'])]
def tile(n, S):
    r = []
    for d in ('png', 'new'):
        p = os.path.join(T, d, L[n][2] + '.png')
        im = Image.open(p).convert('RGBA')
        if n in ROT: im = im.rotate(-90, expand=True)
        c = im.crop(im.getbbox()); s = S / max(c.size); r.append(c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS))
    return r
for name, ns in G:
    S = 1000 if name.startswith('06') else 300; cols = 1 if S == 1000 else 2; rows = -(-len(ns) // cols); cw = 2 * S + 30; ch = S + 28
    pg = Image.new('RGB', (cw * cols, ch * rows), (86, 96, 120)); d = ImageDraw.Draw(pg)
    ns = [n for n in ns if n in L]
    for i, n in enumerate(ns):
        x, y = (i % cols) * cw + 5, (i // cols) * ch; d.text((x, y + 3), '%s  %s  (왼쪽 원본 | 오른쪽 새것)' % (n, L[n][0]), font=F, fill=(255, 235, 120))
        a, b = tile(n, S); pg.paste(a, (x, y + 24), a); pg.paste(b, (x + S + 12, y + 24), b)
    tmp = os.path.join(OUT, '_tmp.png'); pg.save(tmp)
    try: os.replace(tmp, os.path.join(OUT, name + '.png'))
    except OSError as e: print('잠김', name, e)
print(OUT, len(G))
