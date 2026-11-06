# -*- coding: utf-8 -*-
"""쉔무 II 지명 카드·날짜 낱자(A3) 한글화 — 초안·미리보기만(재포장 없음). 1편 로딩 지명과 같은 글꼴(brush, 흰색).
 work/tex/번역/채움/A3_지명카드.tsv → work/tex/new/<id>.png · work/tex/미리보기/A3_NN.png(왼쪽 원본 | 오른쪽 한글)
 카드 = 알파 잉크 줄(band): [번호 줄] 일본어 줄 / 영문 줄 → 영문·번호 줄은 그대로, 일본어 줄 잉크만 지우고 그 자리(폭은 원문·영문 줄 중 넓은 쪽 안)에 씀.
 python tools/tex_card.py"""
import os, sys, unicodedata
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'work', 'tex'); sys.stdout.reconfigure(encoding='utf-8')
FONT = 'C:/claude/utils/font/songmyung/SongMyung-Regular.ttf'
LAB = 'C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf'
def bands(a, thr=24, gap=2):
    r = np.where((a > thr).any(axis=1))[0]
    if not len(r): return []
    out = [[r[0], r[0]]]
    for y in r[1:]:
        if y - out[-1][1] > gap: out.append([y, y])
        else: out[-1][1] = y
    return [tuple(b) for b in out if b[1] - b[0] >= 2]
def ink(a, y0, y1, thr=24):
    c = np.where((a[y0:y1 + 1] > thr).any(axis=0))[0]
    return c[0], c[-1]
def text_img(t, w, h):
    """글자 잉크가 w×h 안에 들어오게(가로로 넘치면 글자 크기를 줄임) — 4배로 그려 줄임"""
    S = 4; size = int(h * S * 1.3)
    while size > 8:
        f = ImageFont.truetype(FONT, size); bb = f.getbbox(t)
        if bb[2] - bb[0] <= w * S and bb[3] - bb[1] <= h * S: break
        size -= 2
    m = Image.new('L', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), 0)
    ImageDraw.Draw(m).text((4 - bb[0], 4 - bb[1]), t, font=f, fill=255)
    m = m.crop(m.getbbox())
    return m.resize((max(1, m.width // S), max(1, m.height // S)), Image.LANCZOS)
DATE = {'分', '午後', '午前', '時', '年', '日', '月'}
GLYPH_H = 0
def card(r):
    no, id_, W, H, jp, ko, memo = r
    ko = unicodedata.normalize('NFKC', ko)                     # 전각 숫자·영문은 이 글꼴에 없다(８번 창고 → 숫자 사라짐)
    im = Image.open(os.path.join(T, 'png', id_ + '.png')).convert('RGBA'); A = np.array(im); a = A[..., 3]
    bs = bands(a)
    if not bs: return im, im, '잉크 없음'
    if '낱자' in memo or len(bs) == 1: jb = bs[0]; lim = (0, im.width - 1)
    else:
        jb = bs[-2]
        x0, x1 = ink(a, *jb); e0, e1 = ink(a, *bs[-1]); lim = (min(x0, e0), max(x1, e1))
    if len(bs) == 1 and '낱자' not in memo: lim = ink(a, *jb)
    x0, x1 = ink(a, *jb); cx = (x0 + x1) / 2
    B = A.copy(); B[jb[0]:jb[1] + 1, :, 3] = 0
    gh = GLYPH_H if ('낱자' in memo or jp in DATE) else jb[1] - jb[0] + 1     # 날짜 낱자는 모두 같은 글자 높이(1편 «같은 ui 글자는 크기 통일»)
    m = text_img(ko, lim[1] - lim[0] + 1, gh)
    px = int(round(cx - m.width / 2)); px = max(lim[0], min(px, lim[1] - m.width + 1)); py = jb[0] + (jb[1] - jb[0] + 1 - m.height) // 2
    out = Image.fromarray(B); layer = Image.new('RGBA', out.size, (255, 255, 255, 0)); layer.putalpha(0)
    full = Image.new('L', out.size, 0); full.paste(m, (px, py))
    layer = Image.merge('RGBA', (Image.new('L', out.size, 255),) * 3 + (full,))
    return im, Image.alpha_composite(out, layer), ''
def main():
    rows = [l.split('\t') for l in open(os.path.join(T, '번역', '채움', 'A3_지명카드.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
    os.makedirs(os.path.join(T, 'new'), exist_ok=True); os.makedirs(os.path.join(T, '미리보기'), exist_ok=True)
    lab = ImageFont.truetype(LAB, 13); cells = []; skip = []
    global GLYPH_H
    hs = []
    for r in rows:
        if r[4] in DATE or '낱자' in r[6]:
            a = np.array(Image.open(os.path.join(T, 'png', r[1] + '.png')).convert('RGBA'))[..., 3]; b = bands(a)[0]; hs.append(b[1] - b[0] + 1)
    GLYPH_H = min(hs); print('날짜 낱자 높이', sorted(hs))
    for r in rows:
        if r[5] in ('-', '?'): skip.append(r[0]); continue
        a, b, n = card(r)
        b.save(os.path.join(T, 'new', r[1] + '.png'))
        cells.append((r, a, b))
    TW = 236; CW = 2 * TW + 12; CH = 150; cols = 3; per = cols * 7
    bg = (86, 96, 120)
    for p in range(0, len(cells), per):
        pg = Image.new('RGB', (cols * CW, ((min(per, len(cells) - p) + cols - 1) // cols) * CH), (28, 28, 34)); d = ImageDraw.Draw(pg)
        for i, (r, a, b) in enumerate(cells[p:p + per]):
            x = (i % cols) * CW; y = (i // cols) * CH
            d.text((x + 4, y + 2), '%s %s → %s' % (r[0], r[4], r[5]), font=lab, fill=(255, 220, 90))
            for k, im in enumerate((a, b)):
                bb = Image.fromarray(np.array(a if 0 else im)).getbbox() or (0, 0, im.width, im.height)
                u = Image.new('RGBA', im.size, bg + (255,)); u.alpha_composite(im)
                box = a.getbbox() or (0, 0, a.width, a.height); bb2 = b.getbbox() or box
                box = (min(box[0], bb2[0]) - 4, min(box[1], bb2[1]) - 4, max(box[2], bb2[2]) + 4, max(box[3], bb2[3]) + 4)
                c = u.crop(box); s = min(TW / c.width, 124 / c.height, 2); c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
                pg.paste(c.convert('RGB'), (x + 4 + k * TW, y + 20))
        pg.save(os.path.join(T, '미리보기', 'A3_%02d.png' % (p // per)))
    print('그림', len(cells), '건너뜀', skip)
if __name__ == '__main__': main()
