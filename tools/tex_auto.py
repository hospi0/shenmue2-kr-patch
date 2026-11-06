# -*- coding: utf-8 -*-
"""쉔무 II 그림 한글화 초안 — 판 종류별 처리(재포장 없음, 미리보기만). 1편 tools/tex_kr.py 의 지우기·색 재기 재사용.
 입력 work/tex/번역/채움/*.tsv (Z_판독보충 이 앞 표를 덮음) · 칸 지정 work/tex/칸지정.py
 출력 work/tex/new/<id>.png · work/tex/미리보기/<묶음>_NN.png(왼쪽 원본 | 오른쪽 한글) · work/tex/그림결과.tsv(판마다 처리·문제)
 python tools/tex_auto.py [묶음 앞글자…]   예) A1 A5
 ★원칙: 영문·번호 줄은 유지, 한글은 원문 잉크 범위 안(게임이 잘라 씀), 1편 같은 그림은 1편 new 복사."""
import os, sys, glob, re, shutil, unicodedata, importlib.util
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tex_kr as K
T = os.path.join(ROOT, 'work', 'tex'); ONE = os.path.join(ROOT, '..', 'shenmue-kr-patch', 'work', 'scene_tex', 'new')
sys.stdout.reconfigure(encoding='utf-8')
FP = {k: K._font_path(k) for k in K.FONTS}
FP['callig'] = 'C:/claude/utils/font/eastseadokdo/EastSeaDokdo-Regular.ttf'  # K.FONTS.get('callig')

def nf(t): return unicodedata.normalize('NFKC', t).replace('Ⅰ', 'I').replace('Ⅱ', 'II').replace('・', '·')
def runs(v, gap=2, mn=2):
    r = np.where(v)[0]
    if not len(r): return []
    o = [[r[0], r[0]]]
    for y in r[1:]:
        if y - o[-1][1] > gap: o.append([y, y])
        else: o[-1][1] = y
    return [(int(a), int(b)) for a, b in o if b - a + 1 >= mn]
def fit_size(lines, font, maxw, maxh):
    size = max(6, int(maxh * 1.4))
    while size > 6:
        f = ImageFont.truetype(FP[font], size * 4)
        bbs = [f.getbbox(l) for l in lines if l.strip()]
        if all(b[2] - b[0] <= maxw * 4 and b[3] - b[1] <= maxh * 4 for b in bbs): return size
        size -= 1
    return size
def text_mask(shape, items, font, size):
    """items = [(글, 중심x 또는 ('l',x)/('r',x), 중심y)] → 0~1 마스크"""
    H, W = shape; S = 4
    big = Image.new('L', (W * S, H * S), 0); d = ImageDraw.Draw(big); f = ImageFont.truetype(FP[font], size * S)
    for t, x, y in items:
        if not t.strip(): continue
        b = f.getbbox(t); w, h = b[2] - b[0], b[3] - b[1]
        px = {'l': x[1] * S, 'r': x[1] * S - w}[x[0]] if isinstance(x, tuple) else x * S - w / 2
        d.text((px - b[0], y * S - h / 2 - b[1]), t, font=f, fill=255)
    return np.array(big.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
def vtext_mask(shape, cols, font, box, cell=None):
    """세로쓰기: cols = 오른쪽부터 열 목록, box 안"""
    x0, y0, x1, y1 = box
    m = K.render_mask('\n'.join(cols), x1 - x0, y1 - y0, font, v=True, cell_px=cell)
    o = np.zeros(shape, np.float32); o[y0:y1, x0:x1] = m
    return o
def paint(A, m, col, opaque=False):
    a = m[..., None]; c = np.array(col, np.float32)
    has = (A[..., 3:4] > 0).astype(np.float32)
    rgb = A[..., :3].astype(np.float32)
    A[..., :3] = np.where(has > 0, rgb * (1 - a) + c * a, np.where(a > 0, c, rgb)).astype(np.uint8)
    A[..., 3] = np.maximum(A[..., 3], (m * 255).astype(np.uint8))
def outline(m, r=1):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(m, k)
def inpaint(A, mask, r=3, grow=1):
    k = np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)
    mm = cv2.dilate(mask.astype(np.uint8) * 255, k)
    A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), mm, r, cv2.INPAINT_TELEA)
def ink(A, box):
    m = np.zeros(A.shape[:2], bool); x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = K.ink_mask(A, box, 'auto'); return m

LOGO1 = os.path.join(ROOT, '..', 'shenmue-kr-patch', 'work', 'gfx', 'new', 'TITLE3__02_tit_main.png')
LOGO = {'527': dict(cut=200, fill=(187, 51, 68), edge=(255, 255, 153), glow=(255, 255, 221), er=1, gr=7),
        '3577': dict(cut=400, fill=(204, 51, 85), edge=(255, 255, 153), glow=(255, 255, 221), er=2, gr=14),
        '3538': dict(cut=400, fill=(255, 255, 255), edge=(255, 255, 255), glow=(255, 255, 255), er=2, gr=14),
        '611': dict(cut=None, fill=(0, 68, 119), edge=(40, 150, 160), glow=None, er=1, gr=0, shadow=3)}
def h_logo(A, n):
    """제목 로고: 1편에서 만든 «쉔무» 붓글씨 모양을 그대로 쓰고, 색·테두리·번짐은 2편 판 실측값. Ⅱ 는 원본 유지"""
    c = LOGO[n]; H, W = A.shape[:2]; cut = c['cut'] or W
    al = A[..., 3] > 40; xs = np.where(al[:, :cut].any(axis=0))[0]; ys = np.where(al[:, :cut].any(axis=1))[0]; pad = c['gr'] // 2 if c['gr'] else 0
    x0, x1, y0, y1 = int(xs[0]) + pad, int(xs[-1]), int(ys[0]) + pad, int(ys[-1]) - pad
    if c['cut']: x1 -= c['gr']                                   # 무 끝이 Ⅱ 빛무리에 붙지 않게
    one = Image.open(LOGO1).convert('RGBA').split()[3].crop((82, 17, 400, 106))
    m = np.array(one.resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32) / 255
    M = np.zeros((H, W), np.float32); M[y0:y1, x0:x1] = m
    if c['cut']:
        # Ⅱ 는 빨간 글자 덩어리 + 빛무리만 원본으로 남긴다(일자로 자르면 Ⅱ 빛무리가 잘리고 ー 끝이 남는다). 흰 판 3538 은 배치가 같은 3577 에서 잰다
        R = np.array(Image.open(os.path.join(T, 'png', '36d9431bd4cf.png')).convert('RGBA')) if n == '3538' else A
        red = ((R[..., 0].astype(int) > R[..., 1].astype(int) + 60) & (R[..., 3] > 128)).astype(np.uint8)
        nl, lb = cv2.connectedComponents(red); r_ = lb[:, cut:]; ii = np.bincount(r_[r_ > 0]).argmax()
        g_ = c['gr'] + 2; w = cv2.dilate((lb == ii).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g_ + 1, 2 * g_ + 1))).astype(np.float32)
        w = cv2.GaussianBlur(w, (0, 0), c['gr'] / 3)
        # Ⅱ 왼쪽 중간(ー 끝 + 그 빛무리): Ⅱ 로부터의 거리별 빛무리 값을 깨끗한 오른쪽에서 재서 거리대로 다시 칠한다
        im_ = lb == ii; xi = np.where(im_.any(axis=0))[0]; wd = xi[-1] - xi[0]; K = c['gr'] + 8
        dt = cv2.distanceTransform((~im_).astype(np.uint8), cv2.DIST_L2, 5); db = np.rint(dt).astype(int)
        cols = np.arange(A.shape[1])[None, :]; rws = [y for y in np.where(im_.any(axis=1))[0] if np.where(im_[y])[0][0] > xi[0] + wd * .15]
        clean = (cols > xi[0] + wd * .75) & (np.arange(A.shape[0])[:, None] >= rws[0]) & (np.arange(A.shape[0])[:, None] <= rws[-1]) & ~im_
        prof = {k: np.median(A[clean & (db == k)], axis=0) for k in range(1, K + 1) if (clean & (db == k)).any()}
        st = int(np.median([np.where(im_[y])[0][0] for y in rws]))
        for k, v in prof.items():
            A[(cols < st) & (np.arange(A.shape[0])[:, None] >= rws[0]) & (np.arange(A.shape[0])[:, None] <= rws[-1]) & (db == k)] = v.astype(np.uint8)
        A[(cols < st) & (np.arange(A.shape[0])[:, None] >= rws[0]) & (np.arange(A.shape[0])[:, None] <= rws[-1]) & (db > K)] = 0
        A[..., 3] = (A[..., 3] * w).astype(np.uint8); A[A[..., 3] == 0] = 0
    else: A[:, :cut] = 0
    if c.get('glow'):
        g = cv2.GaussianBlur(outline(M, max(1, c['gr'] // 3)), (0, 0), c['gr'] / 2.5); paint(A, np.clip(g * 1.2, 0, 1) * .9, c['glow'])
    if c.get('shadow'):
        sh = np.roll(np.roll(M, c['shadow'], 0), c['shadow'], 1); paint(A, sh * .7, (0, 0, 0))
    paint(A, outline(M, c['er']), c['edge']); paint(A, M, c['fill'])
    A[:, cut:, :3] = A[:, cut:, :3]
def h_sub(A, t):
    """부제: 1편 부제와 같은 연성체, 색·그림자는 원본 실측"""
    H, W = A.shape[:2]; al = A[..., 3] > 40; xs = np.where(al.any(axis=0))[0]; ys = np.where(al.any(axis=1))[0]
    x0, x1, y0, y1 = int(xs[0]), int(xs[-1]), int(ys[0]), int(ys[-1]); A[...] = 0
    FP['yeonsung'] = 'C:/claude/utils/font/yeonsung/YeonSung-Regular.ttf'
    s_ = fit_size([t], 'yeonsung', x1 - x0, y1 - y0 - 3); M = text_mask((H, W), [(t, (x0 + x1) / 2, (y0 + y1) / 2)], 'yeonsung', s_)
    paint(A, np.roll(np.roll(M, 2, 0), 2, 1) * .7, (0, 0, 0)); paint(A, outline(M, 1), (40, 150, 160)); paint(A, M, (0, 68, 102))
def h_btn(A, t, x0):
    """버튼 판: 아이콘 오른쪽(x0~)을 통째로 비우고 글자·테두리를 새로 — 칸 밖 붉은 그림자가 남지 않게"""
    al = A[..., 3] > 10; ys = np.where(al.any(axis=1))[0]; xs = np.where(al.any(axis=0))[0]; y0, y1, x1 = int(ys[0]), int(ys[-1]), int(xs[-1])
    A[:, x0:, :] = 0
    s_ = fit_size([t], 'button', x1 - x0 - 3, y1 - y0 - 2); m = text_mask(A.shape[:2], [(t, (x0 + x1) / 2 + 1, (y0 + y1) / 2)], 'button', s_)
    g = cv2.GaussianBlur(outline(m, 2), (0, 0), .7)
    paint(A, np.clip(g * 1.4, 0, 1), (120, 18, 14)); paint(A, m, (250, 232, 180))
# ── 판 종류 ─────────────────────────────────────────────
def h_rows(A, L, font='gothic_b', center=False):
    """투명 판, 줄 낱낱(줄마다 잘려 쓰임): 줄 위치·중심 유지"""
    a = A[..., 3] > 24; bs = runs(a.any(axis=1), 1)
    if len(bs) != len(L): return '줄 수 %d ≠ 번역 %d' % (len(bs), len(L))
    h = max(b - t + 1 for t, b in bs); W = A.shape[1]; size = fit_size(L, font, W - 4, h)
    its = []
    for (t, b), l in zip(bs, L):
        c = np.where(a[t:b + 1].any(axis=0))[0]; w = ImageFont.truetype(FP[font], size * 4).getlength(l) / 4 + 4
        its.append((l, (W - 1) / 2 if center else min(max((c[0] + c[-1]) / 2, w / 2), W - w / 2), (t + b) / 2))
    A[...] = 0; m = text_mask(A.shape[:2], its, font, size)
    paint(A, outline(m, 1), (0, 0, 0)); paint(A, m, (255, 255, 255))
PLATE = {}
def load_plates():
    for f in glob.glob(os.path.join(T, '판', 'plate_0?.png')):
        a = np.array(Image.open(f).convert('RGBA')); PLATE[(a[..., 3] > 0).tobytes()] = a
PANEL = {}
def panel_bg(sel):
    """같은 모양 창끼리 겹쳐 중앙값 = 글자 없는 바탕"""
    g = {}
    for n, c in sel.items():
        if c[0][:2] == 'A1' and n.isdigit() and 712 <= int(n) <= 754 and n != '713':
            a = np.array(Image.open(os.path.join(T, 'png', c[2] + '.png')).convert('RGBA')); g.setdefault((a[..., 3] > 0).tobytes(), []).append(a)
    W3 = np.array([.3, .59, .11], np.float32)
    for k, v in g.items():
        st = np.stack(v).astype(np.float32); m1 = np.median(st, axis=0)
        ms = []
        for a in v:
            d = np.abs(a[..., :3].astype(np.float32) @ W3 - m1[..., :3] @ W3) > 20
            ms.append(cv2.dilate(d.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        ms = np.stack(ms); rgb = st[..., :3].copy(); rgb[ms] = np.nan
        with np.errstate(all='ignore'):
            import warnings; warnings.simplefilter('ignore')
            m2 = np.nanmedian(rgb, axis=0)
        cnt = (~ms).sum(axis=0); bad = (cnt < max(4, len(v) * .3)) | np.isnan(m2).any(axis=2)
        m2 = np.where(np.isnan(m2), m1[..., :3], m2).astype(np.uint8)
        m2 = cv2.inpaint(np.ascontiguousarray(m2), cv2.dilate(bad.astype(np.uint8) * 255, np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA)
        PANEL[k] = (m2, len(v))
    print('창 모양', sorted(x[1] for x in PANEL.values()))
# 숫자 빈자리 판 실측: 줄별 중심 y, 빈자리 줄 범위
SLOTY = {'726': ([212, 256, 286], {2: (274, 299)}), '740': ([212, 241, 292], {1: (228, 255)}), '741': ([234, 264], {1: (251, 278)}),
         '743': ([207, 256, 287], {0: (194, 220), 2: (274, 300)}), '745': ([235, 264], {0: (222, 248)})}
def h_panel(A, L, n_=None):
    """안내창: 바탕은 겹친 중앙값, 글은 원문 줄 간격·크기로 가운데"""
    H, W = A.shape[:2]; al = A[..., 3] > 0; ys = np.where(al.any(axis=1))[0]; xs = np.where(al.any(axis=0))[0]
    top, bot, lf, rt = int(ys[0]), int(ys[-1]), int(xs[0]), int(xs[-1]); ph = bot - top; pw = rt - lf
    w3 = np.array([.3, .59, .11]); lum = A[..., :3] @ w3
    bg = PLATE[al.tobytes()]
    d = (lum < 70) & (np.abs(lum - bg[..., :3] @ w3) > 40) & al
    inner = np.zeros((H, W), bool); inner[top + int(ph * .1):bot - int(ph * .1), lf + int(pw * .1):rt - int(pw * .1)] = True; d &= inner   # 모서리 장식 제외
    bs = runs(d.sum(axis=1) >= 2, 3, 6)
    if not bs: return '글 못 찾음'
    A[..., :3] = bg[..., :3]                              # 측정: 글자 없는 판(tools/tex_plate.py)을 통째로 깔고 그 위에 씀
    cs = np.where(d.any(axis=0))[0]; x0, x1 = int(cs[0]), int(cs[-1]); cx = (lf + rt) / 2
    hs = sorted(b - t + 1 for t, b in bs); bh = min(max(hs[len(hs) // 2], 18), 26)
    left = abs((x0 + x1) / 2 - cx) > pw * .07
    size = min(24, fit_size([l.replace('  ', '가가') for l in L], 'mincho', int(pw * .88), 30))
    n = len(L); room = ph * .74; pitch = min(max(size * 1.5, 18), room / max(1, n)); size = min(size, int(pitch / 1.15))
    f_ = ImageFont.truetype(FP['mincho'], size * 4); wd = lambda t: f_.getlength(t) / 4
    its = []
    if n_ in SLOTY:
        yy, sl = SLOTY[n_]
        for i, (l, y) in enumerate(zip(L, yy)):
            if i in sl:
                t0, t1 = sl[i]; rr = [r for r in runs(d[t0:t1 + 1].any(axis=0), 2, 1) if 50 < r[0] < 460]
                g = max(zip(rr, rr[1:]), key=lambda p: p[1][0] - p[0][1]); a_, b_ = l.split('  ', 1)
                its += [(a_, ('r', g[0][1] + 1), y), (b_, ('l', g[1][0]), y)]
            else: its.append((l, cx, y))
    else:
        c = (top + bot) / 2; yy = [c + (i - (n - 1) / 2) * pitch for i in range(n)]
        maxw = max(wd(l) for l in L); xl = max(lf + pw * .05, min(x0, rt - pw * .05 - maxw))
        its = [(l, ('l', xl) if left else cx, y) for l, y in zip(L, yy)]
    m = text_mask((H, W), its, 'mincho', size)
    paint(A, outline(m, 1) * .75, (232, 232, 200), True); paint(A, m, (12, 12, 12), True)
def h_last_band(A, L, k=-1, font='gothic'):
    """투명 판, 영문 줄은 두고 일본어 줄(k 번째)만"""
    a = A[..., 3] > 24; bs = runs(a.any(axis=1), 2); t, b = bs[k]
    c = np.where(a[t:b + 1].any(axis=0))[0]; cx = (c[0] + c[-1]) / 2
    col = tuple(int(v) for v in np.median(A[t:b + 1][a[t:b + 1]][:, :3], axis=0))
    A[t:b + 1, :, 3] = 0
    wc = np.where(a.any(axis=0))[0]; size = fit_size(L, font, wc[-1] - wc[0], b - t + 1)
    paint(A, text_mask(A.shape[:2], [(L[0], cx, (t + b) / 2)], font, size), col)
def h_glow(A, L):
    """지역 판 128×32: 흰 글자 + 검은 번짐"""
    H, W = A.shape[:2]; a = A[..., 3] > 200; ys = np.where(a.any(axis=1))[0]; xs = np.where(a.any(axis=0))[0]
    cx, cy = (xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2; bright = (A[..., :3].sum(axis=2) > 400) & a
    y2 = np.where(bright.any(axis=1))[0]; x2 = np.where(bright.any(axis=0))[0]
    size = fit_size(L, 'gothic_b', W - 8, int(y2[-1] - y2[0] + 1)); A[...] = 0
    m = text_mask((H, W), [(L[0], W / 2, cy)], 'gothic_b', size)
    g = cv2.GaussianBlur(outline(m, 1), (0, 0), 1.6); g = np.clip(g * 1.6, 0, 1)
    A[..., 3] = (g * 255).astype(np.uint8); paint(A, m, (235, 235, 235))
def h_glyph(A, L, font='brush', vertical=False):
    """낱자·큰 붓글씨: 투명 판 통째로"""
    if not L[0].strip(): A[...] = 0; return
    a = A[..., 3] > 100; ys = np.where(a.any(axis=1))[0]; xs = np.where(a.any(axis=0))[0]; x0, y0, x1, y1 = xs[0], ys[0], xs[-1] + 1, ys[-1] + 1
    px = A[a][:, :3]; lum = px @ np.array([.3, .59, .11]); dark = lum.mean() < 110
    col = tuple(int(v) for v in np.median(px[(lum <= np.percentile(lum, 60)) if dark else (lum >= np.percentile(lum, 40))], axis=0))
    edge = (lum < 80).mean() > .02 and lum.max() > 180
    A[...] = 0
    if vertical:
        m = vtext_mask(A.shape[:2], [L[0]], font, (int(x0), int(y0), int(x1), int(y1)))
    else:
        s = fit_size(L, font, x1 - x0, y1 - y0); m = text_mask(A.shape[:2], [(L[0], (x0 + x1) / 2, (y0 + y1) / 2)], font, s)
    if edge: paint(A, outline(m, 1), (20, 20, 20))
    paint(A, m, col)
def h_yellow(A, L):
    """미니맵: 노란 글자만 지우고 그 자리에(지도선 유지)"""
    r, g, b = [A[..., i].astype(int) for i in range(3)]; y = (r > 150) & (g > 140) & (b < 130) & (A[..., 3] > 30)
    k = cv2.dilate(y.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    ys = np.where(y.any(axis=1))[0]; xs = np.where(y.any(axis=0))[0]
    if not len(ys): return '노란 글 없음'
    x0, y0, x1, y1 = int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1
    A[..., 3][k] = 0
    W = A.shape[1]; cx = (x0 + x1) / 2; half = min(cx, W - cx) * 2
    s = fit_size(L, 'gothic', max(x1 - x0, min(half, x1 - x0 + 16)), y1 - y0); m = text_mask(A.shape[:2], [(L[0], cx, (y0 + y1) / 2)], 'gothic', s)
    paint(A, outline(m, 1), (20, 20, 20)); paint(A, m, (255, 240, 60))
def main_band(m, vertical=False):
    p = m.sum(axis=0 if vertical else 1); bs = runs(p >= 2, 2, 3)
    return max(bs, key=lambda b: (b[1] - b[0])) if bs else None
def plate(A, t, box, font='gothic', vertical=False, keep_rest=True):
    """불투명 판: box 안에서 가장 큰 글자 줄만 지우고 그 자리에"""
    x0, y0, x1, y1 = box
    A0 = A.copy(); m = ink(A, box)
    if not m.any(): return '잉크 없음'
    b = main_band(m, vertical)
    if not b: return '줄 못 찾음'
    sel = np.zeros_like(m)
    if vertical: sel[:, b[0]:b[1] + 1] = m[:, b[0]:b[1] + 1]
    else: sel[b[0]:b[1] + 1] = m[b[0]:b[1] + 1]
    ys = np.where(sel.any(axis=1))[0]; xs = np.where(sel.any(axis=0))[0]; bx = (int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1)
    col = K.measure_color(A, bx, sel[bx[1]:bx[3], bx[0]:bx[2]])
    inpaint(A, sel, 3, 1)
    if vertical: mk = vtext_mask(A.shape[:2], [nf(t)], font, bx)
    else:
        s = fit_size([nf(t)], font, bx[2] - bx[0], bx[3] - bx[1]); mk = text_mask(A.shape[:2], [(nf(t), (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)], font, s)
    paint(A, mk, col, True)
def h_plate(A, L, memo):
    H, W = A.shape[:2]; v = '세로' in memo; e = []
    if len(L) == 1: e.append(plate(A, L[0], (0, 0, W, H), 'gothic', v))
    else:
        n = len(L)
        for i, t in enumerate(L):
            bx = (W * (n - 1 - i) // n, 0, W * (n - i) // n, H) if v else (0, H * i // n, W, H * (i + 1) // n)
            e.append(plate(A, t, bx, 'gothic', v))
    e = [x for x in e if x]
    return ' / '.join(e) if e else None
def h_table(A, L, whole=False):
    """투명 표: 줄마다 왼쪽 한자 덩어리만, 오른쪽 영문 유지"""
    a = A[..., 3] > 24; bs = runs(a.any(axis=1), 1, 4)
    if len(bs) != len(L): return '줄 수 %d ≠ %d' % (len(bs), len(L))
    ends = sorted(runs(a[t:b + 1].any(axis=0), 8, 2)[0][1] for t, b in bs); xe = ends[len(ends) // 2] + 2   # 한자 칸 끝 = 줄별 끝의 중앙값
    W = A.shape[1]
    if whole: xe = W
    elif xe > W * .6: xe = int(W * .42)
    for (t, b), l in zip(bs, L):
        reg = a[t:b + 1, :xe]; c0 = (int(np.where(reg.any(axis=0))[0][0]), xe)
        px = A[t:b + 1, :xe][reg][:, :3]; col = tuple(int(v) for v in np.median(px, axis=0))
        A[max(0, t - 1):b + 2, :xe, 3] = 0
        s = fit_size([l], 'gothic', xe - 2, b - t + 1); paint(A, text_mask(A.shape[:2], [(l, xe / 2, (t + b) / 2)], 'gothic', s), col)

SPECIAL = {}; SHEET = {}
sp = os.path.join(T, '칸지정.py')
if os.path.exists(sp):
    s_ = importlib.util.spec_from_file_location('kan', sp); k_ = importlib.util.module_from_spec(s_); s_.loader.exec_module(k_); SPECIAL = k_.SPECIAL; SHEET = getattr(k_, 'SHEET', {})
PCT = {}
sp2 = os.path.join(T, '칸지정2.py')
if os.path.exists(sp2):
    s2 = importlib.util.spec_from_file_location('kan2', sp2); k2 = importlib.util.module_from_spec(s2); s2.loader.exec_module(k2); PCT = k2.PCT
sp3 = os.path.join(T, '칸지정3.py')
if os.path.exists(sp3):
    s3 = importlib.util.spec_from_file_location('kan3', sp3); k3 = importlib.util.module_from_spec(s3); s3.loader.exec_module(k3); PCT.update(k3.PCT)
def pct_boxes(A, spec):
    al = A[..., 3] > 0; ys = np.where(al.any(axis=1))[0]; xs = np.where(al.any(axis=0))[0]
    X0, Y0, W, H = int(xs[0]), int(ys[0]), int(xs[-1] - xs[0] + 1), int(ys[-1] - ys[0] + 1)
    cv_ = lambda b: (X0 + int(b[0] * W / 100), Y0 + int(b[1] * H / 100), X0 + int(b[2] * W / 100), Y0 + int(b[3] * H / 100))
    out = []
    for i in spec:
        o = dict(i[5]) if len(i) > 5 else {}
        if 'draw' in o: o['draw'] = cv_(o['draw'])
        if 'keep' in o: o['keep'] = [cv_(b) for b in o['keep']]
        out.append(cv_(i) + (i[4], o))
    return out
LERP = [False]; PAPER = [False]
NOTE_COLS = (('홍콩 완차이', 411, 58, 238), ('홍남가', 345, 138, 258), ('은전루 205', 285, 208, 440), ('타오리샤오 노사', 160, 128, 458))   # 512 판 기준 원본 세로줄(x 중심, 위, 아래)
def h_note(A, n):
    """봉투 쪽지 33(128)·1637(512): 먹 글씨 화소만 지우고 같은 종이 결(옮겨 온 화소 + 둘레 밝기 맞춤)로 메운 뒤 원본 세로줄 자리에 쓴다. 인장은 그대로"""
    H = A.shape[0]; k = H / 512
    g = cv2.cvtColor(A[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32)
    bg = cv2.medianBlur(A[..., :3], max(3, int(41 * k) | 1)); bg = cv2.cvtColor(bg, cv2.COLOR_RGB2GRAY).astype(np.float32)
    box = np.zeros(g.shape, bool)
    for x0, y0, x1, y1 in ((380, 40, 440, 250), (320, 120, 372, 275), (255, 190, 312, 450), (130, 110, 190, 470)):
        box[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)] = 1
    ink = (bg - g > 26) & box
    ink = cv2.dilate(ink.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5) if H > 128 else (3, 3))) > 0
    red = cv2.dilate(((A[..., 0].astype(int) > A[..., 1].astype(int) + 30)).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0   # 인장은 옮겨 오지 않는다
    F = A[..., :3].astype(np.float32).copy(); todo = ink.copy()
    for dx, dy in ((70, 9), (-70, 9), (64, -40), (-64, -40), (120, 30), (-120, 30), (30, 100), (-30, 100), (30, -100), (-30, -100)):
        dx = int(dx * k); dy = int(dy * k)
        S = np.roll(A[..., :3].astype(np.float32), (dy, dx), (0, 1)); ok = ~np.roll(ink | red, (dy, dx), (0, 1))
        m = todo & ok; F[m] = S[m]; todo &= ~ok
    clean = (~ink).astype(np.float32); sg = 10 * max(k, .4)
    d = (A[..., :3].astype(np.float32) - F) * clean[..., None]
    F += cv2.GaussianBlur(d, (0, 0), sg) / (cv2.GaussianBlur(clean, (0, 0), sg) + 1e-3)[..., None]
    A[..., :3][ink] = np.clip(F[ink], 0, 255).astype(np.uint8)
    m = np.zeros((512, 512), np.float32); size = 38; cell = 41
    for t, cx, top, bot in NOTE_COLS:
        y = top + size / 2; its = []
        for c in t:
            its.append((c, cx, y)); y += cell // 2 if c == ' ' else cell
        m = np.maximum(m, text_mask((512, 512), its, 'mincho', size))
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    if H != 512: m = np.clip(cv2.resize(m, (H, H), interpolation=cv2.INTER_AREA) * 1.3, 0, 1)
    paint(A, m, (28, 28, 26), True)
def yesno_ink():
    """예/아니요 글자 화소 — 파란 판(글자색이 무늬와 안 겹침)에서 재서 빨간 판에도 그대로 쓴다(글자 층이 같음)"""
    B = np.array(Image.open(os.path.join(T, 'png', 'e98c936a3cfe.png')).convert('RGBA'))
    r, g, b = [B[..., i].astype(int) for i in range(3)]
    box = np.zeros(r.shape, bool); box[30:90, 70:175] = 1; box[155:215, 75:185] = 1
    cream = (r > 150) & (g > 140) & (b < r - 25) & (B[..., 3] > 200) & box
    near = cv2.dilate(cream.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))) > 0
    return cv2.dilate((cream | (near & ((r + g + b) / 3 < 90))).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
def h_yesno(A, top_t, bot_t):
    """예/아니요 판: 글자 화소만 같은 줄의 깨끗한 버튼 무늬(거울 반복)로 메운다 — 용·테두리는 원본 그대로. 밝기는 둘레 차이를 흐려서 맞춘다"""
    ink = yesno_ink(); F = A[..., :3].astype(np.float32).copy()
    for (ya, yb), (sa, sb) in (((30, 90), (73, 83)), ((155, 215), (174, 183))):
        n = sb - sa; xs = np.arange(256); q = (xs - sa) % (2 * n); q = sa + np.where(q < n, q, 2 * n - 1 - q)
        F[ya:yb] = A[ya:yb][:, q, :3]
    clean = (~ink).astype(np.float32)
    d = (A[..., :3].astype(np.float32) - F) * clean[..., None]
    w = cv2.GaussianBlur(clean, (0, 0), 7) + 1e-3
    F += cv2.GaussianBlur(d, (0, 0), 7) / w[..., None]
    A[..., :3][ink] = np.clip(F[ink], 0, 255).astype(np.uint8)
    for t, (x0, y0, x1, y1) in ((top_t, (80, 37, 170, 83)), (bot_t, (84, 161, 178, 212))):
        sz = fit_size([t], 'gothic', x1 - x0 - 14, y1 - y0 - 16); m = text_mask(A.shape[:2], [(t, (x0 + x1) / 2, (y0 + y1) / 2)], 'gothic', sz)
        paint(A, outline(m, 2), (0, 0, 0), True); paint(A, m, (205, 200, 135), True)
COVER = {'1133': '쌍장타', '1419': '사보벽참', '1658': '순보추', '1695': '연수포', '1818': '선공각', '3038': '열황섬'}
COVER.update({'100930': '그림자사냥', '100931': '갑옷꿰기', '101008': '선풍', '101009': '몽롱무쌍', '101010': '마제각', '101011': '대전백', '101012': '복신각', '101013': '백원락', '101014': '사신첩', '101015': '항룡각', '101016': '연환벽', '101017': '연환퇴', '101018': '사호추'})
def h_cover(A, t):
    """기술서 표지: 오른쪽 흰 띠를 재서 띠 안쪽만 칠하고 세로로"""
    H, W = A.shape[:2]; lum = A[..., :3] @ np.array([.3, .59, .11]); sal = lum > 165
    col = sal.mean(axis=0); cs = np.where(col[W // 2:] > .35)[0] + W // 2; x0, x1 = int(cs[0]), int(cs[-1]) + 1
    rw = sal[:, x0:x1].mean(axis=1); rs = np.where(rw > .3)[0]; y0, y1 = int(rs[0]), int(rs[-1]) + 1
    reg = A[y0:y1, x0:x1, :3].astype(np.float32); px = reg[lum[y0:y1, x0:x1] > 165]; base = np.median(px, axis=0)
    rs_ = np.random.RandomState(x0 + y0); f = base[None, None] + cv2.GaussianBlur(rs_.normal(0, 7, reg.shape[:2]).astype(np.float32), (0, 0), 1)[..., None]
    A[y0 + 1:y1 - 1, x0 + 1:x1 - 1, :3] = np.clip(f[1:-1, 1:-1], 0, 255).astype(np.uint8)
    m = vtext_mask((H, W), [t], 'brush', (x0 + 2, y0 + 5, x1 - 2, y1 - 5)); paint(A, m, (35, 32, 28), True)
    return None
def h_oval(A):
    """천룡지우 타원 넷: 실측 위치(128 기준 x10·38·64·92, y44~85). 먹을 지우고 타원과 글자를 새로"""
    W = A.shape[1]; k = W / 128; l8 = (A[..., :3] @ np.array([.3, .59, .11])).astype(np.uint8); bgm = cv2.medianBlur(np.ascontiguousarray(l8), int(31 * k) | 1).astype(np.int16)
    mm = np.zeros(A.shape[:2], np.uint8); y0, y1 = int(38 * k), int(92 * k); mm[y0:y1] = ((bgm - l8)[y0:y1] > 14).astype(np.uint8) * 255; mm[y0:y1, int(118 * k):] = 0
    A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), cv2.dilate(mm, np.ones((5, 5), np.uint8)), 4, cv2.INPAINT_TELEA)
    rgb = np.ascontiguousarray(A[..., :3]); ov = np.zeros(A.shape[:2], np.uint8)
    for x, w_, t in ((10, 25, '천'), (38, 23, '룡'), (64, 25, '지'), (92, 24, '우')):
        cv2.ellipse(ov, (int((x + w_ / 2) * k), int(64 * k)), (int(w_ / 2 * k), int(20 * k)), 0, 0, 360, 255, max(1, int(2 * k)), cv2.LINE_AA)
    A[..., :3] = rgb; paint(A, ov.astype(np.float32) / 255, (24, 22, 18), True)
    s_ = int(19 * k); paint(A, text_mask(A.shape[:2], [(t, (x + w_ / 2) * k, 64 * k) for x, w_, t in ((10, 25, '천'), (38, 23, '룡'), (64, 25, '지'), (92, 24, '우'))], 'brush', s_), (24, 22, 18), True)
def h_hissatsu(A, t):
    """필살 표시: 불꽃·원은 두고 가운데 글자만(실측 x10~28, y14~27, 밝기 204)"""
    sat = A[..., :3].max(axis=2).astype(int) - A[..., :3].min(axis=2); g = (sat < 40) & (A[..., 3] > 100); box = np.zeros(g.shape, bool); box[13:29, 9:30] = True
    A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), cv2.dilate((g & box).astype(np.uint8) * 255, np.ones((2, 2), np.uint8)), 2, cv2.INPAINT_TELEA)
    paint(A, text_mask(A.shape[:2], [(t, 19, 20.5)], 'gothic', 14), (225, 225, 225), True)
def boxes(A, spec):
    same = None
    if any(len(i) > 5 and i[5].get('same') for i in spec):
        same = min(fit_size(nf(i[4]).split(chr(10)), i[5].get('font', 'gothic') if len(i) > 5 else 'gothic', i[2] - i[0], i[3] - i[1]) for i in spec)
    for it in spec:
        x0, y0, x1, y1, t = it[:5]; o = it[5] if len(it) > 5 else {}
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(A.shape[1], x1), min(A.shape[0], y1); bx = (x0, y0, x1, y1); font = o.get('font', 'gothic')
        halo = None; op = (A[y0:y1, x0:x1, 3] > 0).mean() > .9 and not o.get('clear')
        if o.get('key') == 'flat':                         # 판이 민무늬: 글자 아닌 쪽 색 중앙값으로 칸을 칠함
            px_ = A[y0:y1, x0:x1, :3].reshape(-1, 3); lm_ = px_ @ np.array([.3, .59, .11]); sd = lm_ >= np.percentile(lm_, 50) if o.get('side', 'light') == 'light' else lm_ <= np.percentile(lm_, 50)
            A[y0:y1, x0:x1, :3] = np.median(px_[sd], axis=0).astype(np.uint8); col = o['col']; op = True
        elif o.get('key'):                                 # 글자색 직접 지정: dark(lum<thr)·light(lum>thr)·red(R−G>35)·sat(채도>thr)만 지움
            r_ = A[y0:y1, x0:x1, :3].astype(np.int16); lm_ = r_ @ np.array([.3, .59, .11]); ky = o['key']
            kk = (r_[..., 0] - r_[..., 1] > o.get('thr', 35)) if ky == 'red' else ((r_.max(axis=2) - r_.min(axis=2)) > o.get('thr', 70)) if ky == 'sat' else (lm_ > o.get('thr', 165)) if ky == 'light' else (r_[..., 2] - r_[..., 0] > o.get('thr', 25)) if ky == 'blue' else (lm_ < o.get('thr', 95))
            if o.get('light2'): kk = kk | (lm_ > o['light2'])          # 글자 흰 테두리도 같이
            if o.get('green'): kk = kk | (r_[..., 1] - r_[..., 0] > 15)   # 글자에 가렸던 테두리 초록
            mm = np.zeros(A.shape[:2], np.uint8); mm[y0:y1, x0:x1] = kk.astype(np.uint8) * 255; mm = cv2.dilate(mm, np.ones((5, 5), np.uint8))
            for k0, k1, k2, k3 in o.get('keep', ()): mm[k1:k3, k0:k2] = 0     # 영문 등 남길 칸
            if o.get('outer'): A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), mm, 3, cv2.INPAINT_TELEA); col = o['col']; op = True   # 돌처럼 칸 경계가 보이는 판: 주변 화소도 씀
            else:
                sub = np.ascontiguousarray(A[y0:y1, x0:x1, :3]); A[y0:y1, x0:x1, :3] = cv2.inpaint(sub, mm[y0:y1, x0:x1], 3, cv2.INPAINT_TELEA); col = o['col']; op = True   # 칸 안 화소로만 메움(테두리 색 안 끌어옴)
        elif o.get('clone'):                                 # 무늬 판: 옆의 깨끗한 무늬를 복사해 덮음(가장자리 부드럽게)
            dx, dy = o['clone']; W_, H_ = A.shape[1], A.shape[0]; dx = int(dx * W_ / 100); dy = int(dy * H_ / 100)
            S_ = np.array(Image.open(os.path.join(T, 'png', o['src'] + '.png')).convert('RGBA')) if o.get('src') else A.copy()
            p_ = S_[y0 + dy:y1 + dy, x0 + dx:x1 + dx, :3].astype(np.float32); m_ = np.zeros((y1 - y0, x1 - x0), np.float32); m_[3:-3, 3:-3] = 1; m_ = np.clip(cv2.GaussianBlur(m_, (0, 0), 2) * 1.3, 0, 1)[..., None]
            A[y0:y1, x0:x1, :3] = (A[y0:y1, x0:x1, :3] * (1 - m_) + p_ * m_).astype(np.uint8); col = o['col']; op = True
        elif o.get('ink'):                                 # 깃발 등: 바탕과 색이 다른 화소만 빼고 메움
            b_ = cv2.medianBlur(np.ascontiguousarray(A[..., :3]), 31).astype(np.int16); mm = np.zeros(A.shape[:2], np.uint8)
            mm[y0:y1, x0:x1] = (np.abs(A[..., :3].astype(np.int16) - b_).sum(axis=2)[y0:y1, x0:x1] > o['ink']).astype(np.uint8) * 255
            A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), cv2.dilate(mm, np.ones((5, 5), np.uint8)), 4, cv2.INPAINT_TELEA); col = o['col']; op = True
        elif o.get('wipe'):                                  # 칸 전체를 주변 바탕으로 메움(글자 화소 안 고름)
            mk_ = np.zeros(A.shape[:2], np.uint8); mk_[y0:y1, x0:x1] = 255; A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), mk_, 3, cv2.INPAINT_TELEA); col = o['col']; op = True
        elif o.get('cell'):                                  # 지도 이름표: 흰 칸을 재서 통째로 칠하고 그 안에(1편 규칙)
            l_ = A[y0:y1, x0:x1, :3] @ np.array([.3, .59, .11]); br = cv2.morphologyEx((l_ > o.get('thr', 185)).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((max(3, (y1 - y0) // 3), max(3, (x1 - x0) // 8)), np.uint8))
            c_, lb, st, _ = cv2.connectedComponentsWithStats(br); i_ = 1 + int(np.argmax(st[1:, 4])); bx_, by_, bw, bh_ = [int(v) for v in st[i_][:4]]
            x0, y0, x1, y1 = x0 + bx_ + 1, y0 + by_ + 1, x0 + bx_ + bw - 1, y0 + by_ + bh_ - 1; bx = (x0, y0, x1, y1)
            A[y0:y1, x0:x1, :3] = np.median(A[y0:y1, x0:x1, :3].reshape(-1, 3), axis=0).astype(np.uint8) if False else np.percentile(A[y0:y1, x0:x1, :3].reshape(-1, 3), 80, axis=0).astype(np.uint8)
            col = (15, 15, 15); op = True
        elif o.get('dark'):                                  # 판 위 검은 글자 + 밝은 테두리: 그 화소만 메우고 같은 꼴로
            lum = A[..., :3] @ np.array([.3, .59, .11]); mm = np.zeros(A.shape[:2], bool); mm[y0:y1, x0:x1] = (lum[y0:y1, x0:x1] < 75) | (lum[y0:y1, x0:x1] > 165)
            sel = np.zeros_like(mm); sel[y0:y1, x0:x1] = cv2.dilate(mm[y0:y1, x0:x1].astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), sel.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
            col = (15, 15, 15); halo = (214, 214, 150); op = True
        elif o.get('fill'):
            reg = A[y0:y1, x0:x1, :3]; dk = np.median(reg[reg.sum(axis=2) < 120], axis=0) if (reg.sum(axis=2) < 120).any() else np.array([10, 8, 6])
            A[y0:y1, x0:x1, :3] = dk.astype(np.uint8); col = o.get('col')
        elif op:
            m = ink(A, bx); col = o.get('col') or K.measure_color(A, bx, m[y0:y1, x0:x1])
            if PAPER[0]:                                  # 종이: 얼룩 측정(바탕−밝기>12)으로 먹 화소만
                l8 = (A[..., :3] @ np.array([.3, .59, .11])).astype(np.uint8); bgm = cv2.medianBlur(np.ascontiguousarray(l8), 31).astype(np.int16)
                mm = np.zeros(A.shape[:2], np.uint8); mm[y0:y1, x0:x1] = ((bgm - l8)[y0:y1, x0:x1] > 12).astype(np.uint8) * 255
                A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), cv2.dilate(mm, np.ones((5, 5), np.uint8)), 4, cv2.INPAINT_TELEA)
            elif LERP[0]:                                 # 판 글자: 바탕색·글자색을 재서 글자 쪽에 가까운 화소만 지움
                r_ = A[y0:y1, x0:x1, :3].astype(np.float32); t_ = max(0, y0 - 2); l_ = max(0, x0 - 2)
                ring = np.concatenate([A[t_:y0, x0:x1, :3].reshape(-1, 3), A[y1:y1 + 2, x0:x1, :3].reshape(-1, 3), A[y0:y1, l_:x0, :3].reshape(-1, 3), A[y0:y1, x1:x1 + 2, :3].reshape(-1, 3)]).astype(np.float32)
                bgc = np.median(ring, axis=0); dd = np.sqrt(((r_ - bgc) ** 2).sum(axis=2)); th = np.percentile(dd, 92)
                core = r_[dd >= th]; col = o.get('col') or tuple(int(v) for v in np.median(core, axis=0))
                mm = np.zeros(A.shape[:2], np.uint8); mm[y0:y1, x0:x1] = (dd > max(22, th * .3)).astype(np.uint8) * 255
                A[..., :3] = cv2.inpaint(np.ascontiguousarray(A[..., :3]), cv2.dilate(mm, np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA)
            else: inpaint(A, m, 3, 1)
        else:
            reg = A[y0:y1, x0:x1]; a = reg[..., 3] > 60
            if a.any():
                px = reg[a][:, :3].astype(np.float32); lum = px @ np.array([.3, .59, .11]); sat = px.max(axis=1) - px.min(axis=1)
                if np.percentile(lum, 90) - np.percentile(lum, 10) > 110:      # 글자 + 흰/검은 테두리
                    if (sat > 70).mean() > .2: core = px[sat > 70]; hl = px[(sat < 40)]
                    else:
                        dark = (lum < np.percentile(lum, 35)).mean(); core = px[lum <= np.percentile(lum, 40)]; hl = px[lum >= np.percentile(lum, 70)]
                    col = o.get('col') or tuple(int(v) for v in np.median(core, axis=0)); halo = tuple(int(v) for v in np.median(hl, axis=0)) if len(hl) else None
                else: col = o.get('col') or tuple(int(v) for v in np.median(px, axis=0))
            else: col = o.get('col') or (0, 0, 0)
            cl = o.get('clr', 1); A[max(0, y0 - cl):y1 + cl, max(0, x0 - cl):x1 + cl, 3] = 0
        if o.get('halo'): halo = o['halo']
        if not t: continue
        if o.get('fill'): x0, y0, x1, y1 = x0 + (x1 - x0) // 12, y0 + (y1 - y0) // 6, x1 - (x1 - x0) // 12, y1 - (y1 - y0) // 6; bx = (x0, y0, x1, y1)
        if o.get('draw'): x0, y0, x1, y1 = o['draw']; bx = (x0, y0, x1, y1)
        if o.get('roth'):                                  # 돌아간 판의 가로글: 똑바로 가로로 그려 눕힘(1 = 반시계, -1 = 시계)
            hh, ww = x1 - x0, y1 - y0; s_ = fit_size([nf(t)], font, ww, hh); U = text_mask((hh, ww), [(nf(t), ww / 2, hh / 2)], font, s_); mk = np.zeros(A.shape[:2], U.dtype); mk[y0:y1, x0:x1] = np.rot90(U, o['roth'])
        elif o.get('rot'):                                 # 판이 돌아간 세로 간판: 똑바로 세로로 그려 반시계로 눕힘(게임에서 시계 방향으로 돌아 세로가 됨)
            hh, ww = x1 - x0, y1 - y0; U = vtext_mask((hh, ww), nf(t).split(chr(10)), font, (0, 0, ww, hh)); mk = np.zeros(A.shape[:2], U.dtype); mk[y0:y1, x0:x1] = np.rot90(U, o.get('rotk', 1))
        elif o.get('v'): mk = vtext_mask(A.shape[:2], nf(t).split('\n'), font, bx)
        else:
            L = nf(t).split('\n'); h = (y1 - y0) / len(L); s = fit_size(L, font, x1 - x0, int(h)); mk = text_mask(A.shape[:2], [(l, (x0 + x1) / 2, y0 + h * (i + .5)) for i, l in enumerate(L)], font, s)
        if halo: paint(A, outline(mk, o.get('ow', 1)), halo, op)
        paint(A, mk, col, op)

def h_sheet(A, spec):
    # 글자 모음 판: 게임이 칸 경계로 잘라 쓰므로 원본 글자 경계 안에만. 바탕은 줄무늬라 행마다 그 행 중앙값으로, 넘치는 글은 가로만 눌러 넣음
    rowbg = np.median(A[..., :3], axis=1)
    for x0, y0, x1, y1, t in spec:
        A[y0 - 1:y1 + 2, x0 - 2:x1 + 3, :3] = rowbg[y0 - 1:y1 + 2, None, :].astype(np.uint8)
        H = y1 - y0; f = ImageFont.truetype(FP['gothic_b'], int(H * .92)); bb = f.getbbox(t); w, h = bb[2] - bb[0], bb[3] - bb[1]
        g = Image.new('L', (w, h), 0); ImageDraw.Draw(g).text((-bb[0], -bb[1]), t, font=f, fill=255)
        W = min(w, x1 - x0); hh = min(h, H); g = g.resize((W, hh), Image.LANCZOS); xx = (x0 + x1 - W) // 2; yy = (y0 + y1 - hh) // 2
        m = np.array(g, np.float32)[..., None] / 255; r = A[yy:yy + hh, xx:xx + W, :3].astype(np.float32); A[yy:yy + hh, xx:xx + W, :3] = (r * (1 - m) + 12 * m).astype(np.uint8)
    return None

BTN = {'488': 24, '489': 23, '490': 22, '497': 48}
def h_title(A):
    # TITLE.GZ 타이틀 통그림: 시작 로고 자리만. 지운 자리는 바로 위 돌 무늬를 옮겨 메우고 1편 «쉔무» 모양을 얹음. Ⅱ·영문 줄·저작권은 원본
    x0, y0, x1, y1 = 246, 164, 704, 286; dy = 112
    # Ⅱ 는 칸 안으로 들어오므로 글자 + 빛무리 화소만 원본 유지(칸 끝을 Ⅱ 앞에서 끊으면 빛무리가 잘리고 ー 끝이 남는다)
    red = ((A[..., 0].astype(int) > A[..., 1].astype(int) + 60) & (A[..., 0] > 100)).astype(np.uint8)
    nl, lb = cv2.connectedComponents(red); ii = lb[160:300, 690:760]; ii = np.bincount(ii[ii > 0]).argmax()
    keep = cv2.dilate((lb == ii).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))).astype(np.float32)
    keep = cv2.GaussianBlur(keep, (0, 0), 2)[y0:y1, x0:x1, None]
    # 밝기 흐름은 칸 둘레에서 이어 받고(바탕), 돌결만 위쪽에서 옮김 → 칸 경계가 안 보임
    mk = np.zeros(A.shape[:2], np.uint8); mk[y0:y1, x0:x1] = 255; small = cv2.resize(np.ascontiguousarray(A[..., :3]), None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA); ms = cv2.resize(mk, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    base = cv2.resize(cv2.inpaint(small, ms, 5, cv2.INPAINT_TELEA), (A.shape[1], A.shape[0]), interpolation=cv2.INTER_CUBIC)[y0:y1, x0:x1].astype(np.float32); base = cv2.GaussianBlur(base, (0, 0), 8)
    src = A[y0 - dy:y1 - dy, x0:x1, :3].astype(np.float32); det = src - cv2.GaussianBlur(src, (0, 0), 14); B = A[y0:y1, x0:x1, :3].astype(np.float32)
    m = np.zeros((y1 - y0, x1 - x0), np.float32); m[6:-6, 6:-3] = 1; m = cv2.GaussianBlur(m, (0, 0), 4)[..., None]
    m = m * (1 - keep)
    A[y0:y1, x0:x1, :3] = np.clip(B * (1 - m) + (base + det) * m, 0, 255).astype(np.uint8)
    one = Image.open(LOGO1).convert('RGBA').split()[3].crop((82, 17, 400, 106))
    lx0, ly0, lx1, ly1 = 272, 176, 660, 274; M = np.zeros(A.shape[:2], np.float32); M[ly0:ly1, lx0:lx1] = np.array(one.resize((lx1 - lx0, ly1 - ly0), Image.LANCZOS), np.float32) / 255
    sh = cv2.GaussianBlur(np.roll(np.roll(outline(M, 3), 8, 0), 8, 1), (0, 0), 6); paint(A, np.clip(sh, 0, 1) * .75, (20, 10, 5))
    paint(A, np.clip(cv2.GaussianBlur(outline(M, 3), (0, 0), 3) * 1.25, 0, 1) * .95, (205, 205, 123)); paint(A, M, (148, 41, 57))

def h_sign_rows(A, L):
    """844 표지판 시트: 게임이 줄마다 원본 글자 범위만 잘라 붙인다 → 줄별 원본 x 범위 안에 맞춰 그린다(가운데로 놓으면 끝이 잘림 — 완차이가 «완»만 나옴)"""
    a = A[..., 3] > 40; bs = runs(a.any(axis=1), 2)
    if len(bs) != len(L): return '줄 수 %d ≠ %d' % (len(bs), len(L))
    box = [(int(np.where(a[t:b + 1].any(axis=0))[0][0]), int(np.where(a[t:b + 1].any(axis=0))[0][-1]), t, b) for t, b in bs]
    col = tuple(int(v) for v in np.median(A[a][:, :3], axis=0))
    A[...] = 0
    for (x0, x1, t, b), l in zip(box, L):
        size = fit_size([l], 'gothic_b', x1 - x0, b - t + 1)
        paint(A, text_mask(A.shape[:2], [(l, (x0 + x1) / 2, (t + b) / 2)], 'gothic_b', size), col, True)
def dispatch(n, g, A, L, memo, jp):
    if n in ('33', '1637'): return h_note(A, n)
    if L and L[0] == '축소': return 'SHRINK'
    if n == '562': A[:] = np.array(Image.open(LOGO1.replace('TITLE3__02_tit_main', 'RESUME02__00_re_fix2')).convert('RGBA')); return None   # 원본 화소 동일 → 1편 글자판(표 = work/tex/재사용/RESUME.DAT)
    if n == '655': return h_title(A)
    if n == '844': return h_sign_rows(A, L)
    if n in ('94', '96', '2297', '2322'): return h_oval(A)
    if n in BTN: return h_btn(A, L[0], BTN[n])
    if n in ('653', '654'): return h_yesno(A, L[0], L[1])
    if n == '664': A[...] = 0
    if n in COVER: return h_cover(A, COVER[n])
    if int(n) in SHEET: return h_sheet(A, SHEET[int(n)])
    if int(n) in SPECIAL:
        LERP[0] = False; PAPER[0] = g == 'B3'; e = boxes(A, SPECIAL[int(n)])
        return e
    if int(n) in PCT:
        PAPER[0] = g in ('B1', 'B4') or int(n) in (1998, 2422, 2879, 1811)
        LERP[0] = (g in ('D2', 'D3') or int(n) in (1141, 1378, 3000)) and int(n) not in (1404, 1450, 1998, 2422, 2879)
        return boxes(A, pct_boxes(A, PCT[int(n)]))
    LERP[0] = False
    if n in BTN: return h_btn(A, L[0], BTN[n])
    if 'rows' in memo: return h_rows(A, L, center=n == '669')   # 669 시작 메뉴 안내: 원본은 끝 넉 줄이 왼쪽 정렬 → 전부 가운데(하스피 실기 지적)
    if g == 'A1':
        if int(n) >= 712 and n != '713': return h_panel(A, L, n)
        return 'SKIP'
    if n in LOGO: return h_logo(A, n)
    if n == '612': return h_sub(A, '제2장 홍콩')
    if g == 'A2': return 'SKIP'
    if g == 'A3': return 'CARD'
    if g == 'A4' and int(n) in (278, 279, 362, 363, 368, 369): return h_last_band(A, L, 1)
    if g == 'A5': return h_glow(A, L)
    if g == 'A6': return h_glyph(A, L, 'brush', '세로' in memo)
    if n in ('768', '769', '770'): return h_hissatsu(A, L[0])
    if g == 'A7': return h_glyph(A, L, 'brush')
    if g == 'A8': return h_yellow(A, L)
    if '4줄' in memo: return h_table(A, L, True)
    if '7줄' in memo: return h_table(A, L)
    return 'SKIP'

def main():
    pre = sys.argv[1:]
    sel = {}
    for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) > 6: sel[c[1]] = c
    rows = {}
    for f in sorted(glob.glob(os.path.join(T, '번역', '채움', '*.tsv'))):
        for l in open(f, encoding='utf-8').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) >= 7: rows[c[0]] = c
    os.makedirs(os.path.join(T, 'new'), exist_ok=True); load_plates()
    res = {}; rp = os.path.join(T, '그림결과.tsv')
    if os.path.exists(rp):
        for l in open(rp, encoding='utf-8').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 2: res[c[0]] = l
    done = {}
    for n, r in rows.items():
        g = sel[n][0][:2]
        if g == 'F' or (pre and g not in pre): continue
        id_, ko, memo, jp = r[1], r[5], r[6], r[4]
        if ko == '-' or ko == '?':
            st_ = os.path.join(T, 'new', id_ + '.png')
            if os.path.exists(st_): os.remove(st_); print('옛 그림 지움', n)   # «그대로» 판의 옛 초안이 남으면 재포장에 들어간다
            res[n] = '%s\t%s\t그대로\t%s' % (n, g, memo); continue
        if (ko == '1편' or sel[n][6].strip()) and n != '897':
            p = os.path.join(ONE, id_ + '.png')
            if os.path.exists(p): shutil.copy(p, os.path.join(T, 'new', id_ + '.png')); res[n] = '%s\t%s\t1편 재사용\t' % (n, g); done.setdefault(g, []).append((n, r)); continue
        im = np.array(Image.open(os.path.join(T, 'png', id_ + '.png')).convert('RGBA')); A = im.copy()
        L = [nf(x) for x in ko.split('／')]
        try: e = dispatch(n, g, A, L, memo, jp)
        except Exception as x: e = '오류 %r' % x
        if e == 'SHRINK': continue
        if e == 'CARD': done.setdefault(g, []); continue
        if e == 'SKIP': res[n] = '%s\t%s\t수동 남음\t%s' % (n, g, ko[:30]); continue
        if e: res[n] = '%s\t%s\t문제\t%s' % (n, g, e); print(n, g, e); continue
        Image.fromarray(A).save(os.path.join(T, 'new', id_ + '.png')); res[n] = '%s\t%s\t그림\t' % (n, g); done.setdefault(g, []).append((n, r))
    SHR = {104767: 2935, 104797: 102653, 105765: 102654, 101923: 102621, 101769: 102616, 101809: 102618, 102487: 1098}   # 64 판 = 같은 그림 큰 판의 축소(실측)
    if not pre or 'B5' in pre:
        for dn, sn in SHR.items():
            a, b = str(sn), str(dn); pa = os.path.join(T, 'new', rows[a][1] + '.png') if a in rows else ''
            if b in rows and pa and os.path.exists(pa):
                o = Image.open(os.path.join(T, 'png', rows[b][1] + '.png')); Image.open(pa).resize(o.size, Image.LANCZOS).save(os.path.join(T, 'new', rows[b][1] + '.png')); res[b] = '%s\tB5\t그림\t축소' % b
    for sn, dn in ((1366, 984), (1778, 2743)):                     # 큰 판 축소본
        a, b = str(sn), str(dn)
        if a in rows and b in rows and os.path.exists(os.path.join(T, 'new', rows[a][1] + '.png')) and (not pre or 'C1' in pre):
            o = Image.open(os.path.join(T, 'png', rows[b][1] + '.png')); im = Image.open(os.path.join(T, 'new', rows[a][1] + '.png')).resize(o.size, Image.LANCZOS); im.save(os.path.join(T, 'new', rows[b][1] + '.png')); res[b] = '%s\tC1\t그림\t축소' % b; done.setdefault('C1', []).append((b, rows[b]))
    open(rp, 'w', encoding='utf-8', newline='\n').write('번호\t묶음\t처리\t메모\n' + '\n'.join(res[k] for k in res) + '\n')
    lab = ImageFont.truetype(FP['gothic_b'], 13); TW = 340; TH = 180; cols = 2
    for g, it in done.items():
        if not it: continue
        for f in glob.glob(os.path.join(T, '미리보기', g + '_*.png')): os.remove(f)
        per = 14
        for p in range(0, len(it), per):
            ch = it[p:p + per]; pg = Image.new('RGB', (cols * (2 * TW + 10), ((len(ch) + 1) // 2) * (TH + 22)), (28, 28, 34)); d = ImageDraw.Draw(pg)
            for i, (n, r) in enumerate(ch):
                x = (i % cols) * (2 * TW + 10); y = (i // cols) * (TH + 22); d.text((x + 4, y + 3), ('%s %s' % (n, r[5]))[:70], font=lab, fill=(255, 220, 90))
                ims = [Image.open(os.path.join(T, q, r[1] + '.png')).convert('RGBA') for q in ('png', 'new')]
                bb = ims[0].getbbox() or (0, 0, 1, 1); b2 = ims[1].getbbox() or bb; box = (min(bb[0], b2[0]), min(bb[1], b2[1]), max(bb[2], b2[2]), max(bb[3], b2[3]))
                for k, im in enumerate(ims):
                    u = Image.new('RGBA', im.size, (86, 96, 120, 255)); u.alpha_composite(im); c = u.crop(box); s = min((TW - 8) / c.width, TH / c.height, 4)
                    c = c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS); pg.paste(c.convert('RGB'), (x + 4 + k * TW, y + 20))
            pg.save(os.path.join(T, '미리보기', '%s_%02d.png' % (g, p // per)))
    import collections
    print(collections.Counter(v.split('\t')[2] for v in res.values()))

if __name__ == '__main__':
    main()
