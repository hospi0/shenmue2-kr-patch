# -*- coding: utf-8 -*-
"""맵·모델 텍스처 한글화(2026-11-05, 하스피 «골라낸거 일단 전부 만들어줘 일어나서 확인할께») — PNG 초안·미리보기만(재포장·빌드 X).
  원본 work/scene_tex/png/<id>.png → 새것 work/scene_tex/new/<id>.png
  미리보기 work/scene_tex/미리보기/<분류>_NN.png  (왼쪽 원본 | 오른쪽 한글, 확대)
  스펙 work/scene_tex/spec_ko.py : SPEC = {id: [항목,…]}
    항목 = dict(box=(x0,y0,x1,y1), t='한글'(줄은 \\n), v=세로쓰기, font=, color=, stroke=(색,두께),
               align='c'|'l'|'r', fit='ink'|'box', erase='auto'|'alpha'|'none'|'fill', pad=)
  ★경계: 한글은 원문 글자 잉크 범위(fit='ink') 안에만 — 게임이 텍스처 일부만 잘라 붙이므로(전차로 교훈).
  ★지우기: 상자 안 «글자 화소»만(배경과 색 차이로 판정) → 주변 바탕으로 메움(cv2.inpaint). 알파 텍스처는 글자 알파만 0.
  python tools/tex_kr.py [id …]
"""
import os, sys, importlib.util
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, 'work', 'tex')
F = 'C:/claude/utils/font/'
FONTS = {
    'gothic': F + 'nanum-gothic/NanumGothicExtraBold.ttf',
    'gothic_b': F + 'nanum-gothic/NanumGothicBold.ttf' if os.path.exists(F + 'nanum-gothic/NanumGothicBold.ttf') else F + 'nanum-gothic/NanumGothicExtraBold.ttf',
    'heavy': F + 'blackhansans/BlackHanSans-Regular.ttf',
    'button': F + 'dohyeon/DoHyeon-Regular.ttf',
    'jua': F + 'jua/Jua-Regular.ttf',
    'mincho': F + 'gowunbatang/GowunBatang-Bold.ttf',
    'mincho_r': F + 'gowunbatang/GowunBatang-Regular.ttf',
    'brush': F + 'songmyung/SongMyung-Regular.ttf',
    'callig': F + 'eastseadokdo/EastSeaDokdo-Regular.ttf',
    'brush2': F + 'nanumbrushscript/NanumBrushScript-Regular.ttf' if os.path.exists(F + 'nanumbrushscript/NanumBrushScript-Regular.ttf') else F + 'eastseadokdo/EastSeaDokdo-Regular.ttf',
    'pen': F + 'nanum-pen/NanumPenScript-Regular.ttf' if os.path.exists(F + 'nanum-pen/NanumPenScript-Regular.ttf') else F + 'gaegu/Gaegu-Bold.ttf',
    'gaegu': F + 'gaegu/Gaegu-Bold.ttf',
    'pixel': F + 'Galmuri-v2.40.3/Galmuri11-Bold.ttf',
}

def _font_path(k):
    p = FONTS.get(k, k)
    if not os.path.exists(p):
        import glob
        c = glob.glob(os.path.join(os.path.dirname(p), '*.ttf')) + glob.glob(os.path.join(os.path.dirname(p), '*.otf'))
        if c: return c[0]
        return FONTS['gothic']
    return p

def DERIVE_MAP():
    p = os.path.join(D, 'spec_ko.py')
    s = importlib.util.spec_from_file_location('spec_ko2', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return getattr(m, 'DERIVE', {})

def load_spec():
    p = os.path.join(D, 'spec_ko.py')
    s = importlib.util.spec_from_file_location('spec_ko', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.SPEC, getattr(m, 'GROUP', {})

def ink_mask(rgba, box, mode):
    x0, y0, x1, y1 = box
    reg = rgba[y0:y1, x0:x1]
    if mode == 'alpha':
        return reg[..., 3] > 24
    rgb = reg[..., :3].astype(np.int16)
    h, w = rgb.shape[:2]
    k = max(5, (min(h, w) // 2) | 1); k = min(k, 61)
    bg = cv2.medianBlur(np.ascontiguousarray(reg[..., :3]), k).astype(np.int16)
    dist = np.abs(rgb - bg).sum(axis=2).astype(np.uint8 if False else np.int32)
    d8 = np.clip(dist, 0, 255).astype(np.uint8)
    if d8.max() < 30: return np.zeros((h, w), bool)
    t, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return d8 > max(t, 28)

def measure_color(rgba, box, m):
    x0, y0, x1, y1 = box
    reg = rgba[y0:y1, x0:x1]
    px = reg[m][:, :3]
    if len(px) == 0: return (0, 0, 0)
    lum = px @ np.array([0.3, 0.59, 0.11])
    bgl = np.median((reg[~m][:, :3] @ np.array([0.3, 0.59, 0.11]))) if (~m).any() else 128
    # 배경에서 먼 쪽(진한 쪽) 3분의 1 의 중앙값 = 글자 본색
    order = np.argsort(np.abs(lum - bgl))[::-1]
    core = px[order[:max(1, len(order) // 3)]]
    return tuple(int(v) for v in np.median(core, axis=0))

def render_mask(text, W, H, font, v=False, align='c', S=6, spacing=0.08, cell_px=None):
    """W×H 상자에 맞춘 글자 알파(0~255) — S 배 크게 그려 줄임. 줄 = \\n (세로면 열, 오른쪽부터)"""
    fp = _font_path(font)
    lines = text.split('\n')
    big = Image.new('L', (W * S, H * S), 0); d = ImageDraw.Draw(big)
    if not v:
        n = len(lines); lh = H * S / n
        # 줄 높이·폭에 맞는 최대 크기
        size = int(lh * 1.15)
        while size > 4:
            f = ImageFont.truetype(fp, size)
            ok = True; boxes = []
            for ln in lines:
                bb = d.textbbox((0, 0), ln, font=f)
                boxes.append(bb)
                if bb[2] - bb[0] > W * S or bb[3] - bb[1] > lh * (1 - spacing): ok = False
            if ok: break
            size -= max(1, size // 40)
        for i, (ln, bb) in enumerate(zip(lines, boxes)):
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            x = {'l': 0, 'r': W * S - tw}.get(align, (W * S - tw) / 2) - bb[0]
            y = i * lh + (lh - th) / 2 - bb[1]
            d.text((x, y), ln, font=f, fill=255)
    else:
        n = len(lines); cw = W * S / n
        eff = lambda c: sum(0.4 if ch == ' ' else 1 for ch in c)
        mx = max(eff(c) for c in lines)
        cell = min(cw, H * S / mx)
        if cell_px: cell = min(cell, cell_px * S)
        size = int(cell * 1.1)
        while size > 4:
            f = ImageFont.truetype(fp, size)
            bb = d.textbbox((0, 0), '가', font=f)
            if max(bb[2] - bb[0], bb[3] - bb[1]) <= cell * (1 - spacing): break
            size -= max(1, size // 40)
        for i, col in enumerate(lines):
            cx = W * S - (i + 0.5) * cw
            tot = cell * eff(col)
            ystart = {'l': 0, 'r': H * S - tot}.get(align, (H * S - tot) / 2)   # 세로: l=위 r=아래 c=가운데
            yy = ystart
            for j, ch in enumerate(col):
                if ch == ' ': yy += cell * 0.4; continue
                cy_ = yy; yy += cell
                bb = d.textbbox((0, 0), ch, font=f)
                gw, gh = bb[2] - bb[0], bb[3] - bb[1]
                if ch in 'ー―-~〜': ch_img = Image.new('L', (int(cell), int(cell)), 0); dd = ImageDraw.Draw(ch_img); dd.line([(cell / 2, cell * 0.15), (cell / 2, cell * 0.85)], fill=255, width=max(1, int(cell / 9))); big.paste(255, (int(cx - cell / 2), int(cy_)), ch_img); continue
                if ch in '.,、。，．':                     # 세로쓰기 부호는 칸 오른쪽 위
                    d.text((cx + cell * 0.1 - bb[0], cy_ - bb[1]), ch, font=f, fill=255); continue
                d.text((cx - gw / 2 - bb[0], cy_ + (cell - gh) / 2 - bb[1]), ch, font=f, fill=255)
    return np.array(big.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255.0

def cell_label(im, out, it):
    """지도 단색 칸 이름표: 칸 안 한 점 → 검은 테두리 안쪽 전체(글자 획은 메움)를 칸 색 한 가지로 칠하고 그 안에만 한글.
    it: cell=(x,y), t, [v, font, color, thr(테두리 어둡기), pad]"""
    H_, W_ = im.shape[:2]; sx, sy = it['cell']
    if it.get('from'):                                 # 사본 판: 원본 판의 칸 둘레 조각을 사본에서 찾아 짚는 점을 옮김
        base = np.array(Image.open(os.path.join(D, 'png', it['from'] + '.png')).convert('L')).astype(np.float32)
        g = cv2.cvtColor(im[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32)
        h = 20; bx0, by0 = max(0, sx - h), max(0, sy - h); tpl = base[by0:sy + h, bx0:sx + h]
        R2 = 40; wx0, wy0 = max(0, bx0 - R2), max(0, by0 - R2)
        win = g[wy0:min(H_, by0 + tpl.shape[0] + R2), wx0:min(W_, bx0 + tpl.shape[1] + R2)]
        res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(res)
        sx, sy = sx + (wx0 + ml[0] - bx0), sy + (wy0 + ml[1] - by0)
    rgb = im[..., :3].astype(np.int32); lum = rgb @ np.array([0.3, 0.59, 0.11])
    bright = (lum > it.get('thr', 110)).astype(np.uint8)              # 테두리·글자 = 어두움
    if it.get('net'):                                  # 테두리 = 지도 전체로 이어진 큰 어두운 그물, 글자 획 = 떨어진 작은 덩어리
        dark = (lum < it.get('thr', 110)).astype(np.uint8)
        nd, ld, st, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
        big = [k for k in range(1, nd) if st[k, 4] > it.get('netmin', 400)]
        border = np.isin(ld, big).astype(np.uint8)
        bright = (cv2.dilate(border, np.ones((2, 2), np.uint8)) == 0).astype(np.uint8)
    if it.get('seal'): bright = cv2.erode(bright, np.ones((3, 3), np.uint8), iterations=it['seal'])   # 가는 대각선 테두리 틈 막기
    n, lab = cv2.connectedComponents(bright, connectivity=4)
    R_ = it.get('r', 3); ids = set()
    for dy in range(-R_, R_ + 1):
        for dx in range(-R_, R_ + 1):
            x, y = sx + dx, sy + dy
            if 0 <= x < W_ and 0 <= y < H_ and lab[y, x] > 0: ids.add(lab[y, x])
    ids = [k for k in ids if 4 <= (lab == k).sum() < it.get('maxa', 6000)]      # 칸 밖 큰 바탕은 제외
    if not ids: print('! 칸 못 찾음', it['t'], it['cell']); return
    reg = np.isin(lab, ids).astype(np.uint8)
    main = max(ids, key=lambda k: (lab == k).sum())
    hull = cv2.convexHull(cv2.findNonZero(reg))
    for _ in range(2):                                   # 글자 획에 쪼개진 칸 조각(껍질 안에 거의 다 든 작은 덩어리)도 모음
        hm = np.zeros((H_, W_), np.uint8); cv2.fillPoly(hm, [hull], 1)
        cand = np.unique(lab[(hm > 0) & (lab > 0)])
        for k in cand:
            if k in ids: continue
            pk = lab == k; a_ = pk.sum()
            if a_ < it.get('maxa', 6000) and (hm[pk] > 0).mean() > 0.9: ids.append(k)
        reg = np.isin(lab, ids).astype(np.uint8)
        hull = cv2.convexHull(cv2.findNonZero(reg))
    fill = np.zeros((H_, W_), np.uint8); cv2.fillPoly(fill, [hull], 1)
    if it.get('seal'): fill = cv2.dilate(fill, np.ones((3, 3), np.uint8), iterations=it['seal'])
    fill &= (cv2.dilate(reg, np.ones((3, 3), np.uint8), iterations=3) | (lum > it.get('line', 60)).astype(np.uint8))   # 테두리 선(아주 어두움)은 안 덮음
    fill = cv2.morphologyEx(fill, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    bgc = np.median(rgb[(lab == main) & (lum > it.get('thr', 110))], axis=0)
    out[fill > 0, :3] = bgc.astype(np.uint8)
    if not it.get('t'): return
    (cx, cy), (rw, rh), ang = cv2.minAreaRect(hull)
    if rw < rh: rw, rh, ang = rh, rw, ang + 90
    while ang > 90: ang -= 180
    while ang < -90: ang += 180
    if it.get("dbg"): print("ang", it["t"], round(ang,1), round(rw,1), round(rh,1))
    pad = it.get('pad', 2)
    if it.get('upright') or abs(ang) < 6 or abs(abs(ang) - 90) < 6:                         # 반듯한 칸: 칸 안 직사각형 그대로(세로 칸이면 세로쓰기)
        ys, xs = np.nonzero(fill)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        while x1 - x0 > 4 and y1 - y0 > 4 and fill[y0:y1, x0:x1].mean() < 0.985:   # 칸 안에 꽉 차는 직사각형으로 줄임
            sides = [fill[y0, x0:x1].mean(), fill[y1 - 1, x0:x1].mean(), fill[y0:y1, x0].mean(), fill[y0:y1, x1 - 1].mean()]
            k = int(np.argmin(sides))
            if k == 0: y0 += 1
            elif k == 1: y1 -= 1
            elif k == 2: x0 += 1
            else: x1 -= 1
        x0, y0, x1, y1 = x0 + pad, y0 + pad, x1 - pad, y1 - pad
        if x1 - x0 < 4 or y1 - y0 < 4: print('! 칸 너무 작음', it['t'], it['cell']); return
        v = it.get('v', (y1 - y0) > (x1 - x0) * 1.3 and 'csize' not in it)
        if 'csize' in it:                                   # 지도 한 장 안 글자 크기 상한 통일 — 칸 가운데에
            cs = it['csize']; lines = it['t'].split(chr(10)); L = max(len(l) for l in lines); n_ = len(lines)
            bw, bh = (cs * n_, cs * L) if v else (cs * L, cs * n_)
            bw, bh = min(bw, x1 - x0), min(bh, y1 - y0)
            x0 += (x1 - x0 - bw) // 2; y0 += (y1 - y0 - bh) // 2; x1, y1 = x0 + bw, y0 + bh
        a = render_mask(it['t'], x1 - x0, y1 - y0, it.get('font', 'gothic'), v, 'c', spacing=it.get('spacing', 0.06))
        x, y = x0, y0
    else:
        tw, th = max(4, int(rw - 2 * pad - 2)), max(4, int(rh - 2 * pad - 1))
        if abs(ang) > 45:                                              # 세로에 가까운 칸 = 세로쓰기(글자는 덜 기울게)
            angv = ang - 90 if ang > 0 else ang + 90
            a0 = render_mask(it['t'], th, tw, it.get('font', 'gothic'), True, 'c', spacing=it.get('spacing', 0.06))
            r = Image.fromarray((a0 * 255).astype(np.uint8)).rotate(-angv, resample=Image.BICUBIC, expand=True)
        else:
            a0 = render_mask(it['t'], tw, th, it.get('font', 'gothic'), False, 'c', spacing=it.get('spacing', 0.06))
            r = Image.fromarray((a0 * 255).astype(np.uint8)).rotate(-ang, resample=Image.BICUBIC, expand=True)
        a = np.array(r).astype(np.float32) / 255.0
        x, y = int(round(cx - r.width / 2)), int(round(cy - r.height / 2))
    xa, ya = max(0, -x), max(0, -y); a = a[ya:, xa:]; x += xa; y += ya
    a = a[:H_ - y, :W_ - x]
    a = a * (fill[y:y + a.shape[0], x:x + a.shape[1]] > 0)            # 칸 밖으로 안 나감
    if it.get('gain'): a = np.clip(a * it['gain'], 0, 1)
    blend(out, x, y, a, it.get('color', (25, 25, 25)))

def rlabel(im, out, it):
    """기울어진 색칸 이름표(지도) — seed 점의 바탕색과 비슷한 이어진 영역 = 칸, 그 볼록 껍질 안(테두리 1px 남김)을 바탕색으로 메우고
    칸의 긴 변 방향으로 한글을 돌려 그 안에만. it: seed=(x,y), t, [tol, font, color, vert(긴 변 대신 짧은 변 방향), pad]"""
    sx, sy = it['seed']; H_, W_ = im.shape[:2]
    rgb = im[..., :3].astype(np.int32)
    if 'poly' in it:                                   # 네 모서리를 직접 잰 칸(가장 확실)
        comp = np.zeros((H_, W_), np.uint8); cv2.fillPoly(comp, [np.array(it['poly'], np.int32)], 1)
    elif 'rgb' in it:                                    # 칸 색을 지정: 그 색 화소(글자에 끊긴 곳은 닫기로 이음) 중 seed 가까운 덩어리
        near = (np.abs(rgb - np.array(it['rgb'])).sum(axis=2) < it.get('tol', 45)).astype(np.uint8)
        near = cv2.morphologyEx(near, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=it.get('close', 2))
        n, lab, st, cen = cv2.connectedComponentsWithStats(near, connectivity=8)
        cand = [(np.hypot(cen[k][0] - sx, cen[k][1] - sy), k) for k in range(1, n) if 60 < st[k, 4] < it.get('maxa', 4000)]
        if not cand: print('! 이름표 못 찾음', it['t']); return
        comp = (lab == min(cand)[1]).astype(np.uint8)
    else:
        base = np.median(rgb[max(0, sy - 1):sy + 2, max(0, sx - 1):sx + 2].reshape(-1, 3), axis=0)
        near = (np.abs(rgb - base).sum(axis=2) < it.get('tol', 60)).astype(np.uint8)
        n, lab = cv2.connectedComponents(near, connectivity=4)
        comp = (lab == lab[sy, sx]).astype(np.uint8)
    if 'poly' not in it and (comp.sum() > it.get('maxa', 4000) or comp.sum() < 20):
        print('! 이름표 영역 이상 %s %s 화소 %d — 건너뜀' % (it['t'], it['seed'], comp.sum())); return
    pts = cv2.findNonZero(comp)
    hull = cv2.convexHull(pts)
    fill = np.zeros((H_, W_), np.uint8); cv2.fillPoly(fill, [hull], 255)
    fill = cv2.erode(fill, np.ones((3, 3), np.uint8), iterations=it.get('shrink', 2 if 'poly' in it else 1))   # 칸 테두리 선은 남김
    if 'bg' in it: bgc = np.array(it['bg'])
    else:
        lum = rgb @ np.array([0.3, 0.59, 0.11]); inside = (fill > 0) & (lum > np.percentile(lum[fill > 0], 55))
        bgc = np.median(rgb[inside], axis=0)                     # 칸 안 밝은 쪽 = 칸 바탕색(글자는 어두움)
    out[fill > 0, :3] = bgc.astype(np.uint8)
    (cx, cy), (rw, rh), ang = cv2.minAreaRect(hull)
    if rw < rh: rw, rh, ang = rh, rw, ang + 90           # rw = 긴 변, ang = 긴 변 방향(도, 영상 좌표 시계 방향)
    while ang > 90: ang -= 180
    while ang < -90: ang += 180
    if 'ang' in it: ang = it['ang']; rw, rh = it.get('tsize', (rw, rh))   # 각도·크기 직접 지정(칸이 정사각에 가까울 때)
    pad = it.get('pad', 2)
    tw, th = max(4, int(rw - 2 * pad - 2)), max(4, int(rh - 2 * pad - 1))
    a0 = render_mask(it['t'], tw, th, it.get('font', 'gothic'), False, 'c', spacing=it.get('spacing', 0.06))
    if it.get('gain'): a0 = np.clip(a0 * it['gain'], 0, 1)
    r = Image.fromarray((a0 * 255).astype(np.uint8)).rotate(-ang, resample=Image.BICUBIC, expand=True)
    a = np.array(r).astype(np.float32) / 255.0
    a *= (fill[:, :] > 0)[int(round(cy - r.height / 2)):, int(round(cx - r.width / 2)):][:a.shape[0], :a.shape[1]] if False else 1
    x, y = int(round(cx - r.width / 2)), int(round(cy - r.height / 2))
    xa, ya = max(0, -x), max(0, -y); a = a[ya:, xa:]; x += xa; y += ya
    a = a[:H_ - y, :W_ - x]
    a = a * (fill[y:y + a.shape[0], x:x + a.shape[1]] > 0)            # ★칸 밖으로 한 화소도 안 나가게
    col = it.get('color') or (25, 25, 25)
    blend(out, x, y, a, col)

CLEAN = {}

def apply(id_, items):
    im = np.array(Image.open(os.path.join(D, 'png', id_ + '.png')).convert('RGBA'))
    out = im.copy()
    notes = []
    for it in items:
        if isinstance(it.get('cell'), tuple):  # 지도 단색 칸: 테두리 안 전체를 칸 색으로 → 한글
            cell_label(im, out, it); continue
        if 'seed' in it:                       # 기울어진 색칸 이름표: 칸 안 한 점 → 같은 색 영역 → 칸 모양·각도
            rlabel(im, out, it); continue
        box = tuple(int(v) for v in it['box']); x0, y0, x1, y1 = box
        mode = it.get('erase', 'alpha' if (im[y0:y1, x0:x1, 3] < 250).mean() > 0.2 else 'auto')
        if mode == 'flat':                    # 상자를 바탕색(밝은 쪽 화소 중앙값)으로 평평하게 — 지도 칸처럼 바탕이 고른 곳
            reg = out[y0:y1, x0:x1]; rgbf = reg[..., :3].reshape(-1, 3).astype(np.float32)
            lum = rgbf @ np.array([0.3, 0.59, 0.11], np.float32)
            bgc = np.array(it['bg'], np.float32) if 'bg' in it else np.median(rgbf[lum >= np.percentile(lum, 50)], axis=0)   # bg = 바탕색 직접 지정
            sd = rgbf[lum >= np.percentile(lum, 50)].std(axis=0) * it.get('noise', 0.5)                                      # noise = 결 세기(0 = 단색)
            rng = np.random.default_rng(x0 * 7919 + y0)
            fillv = np.clip(bgc + rng.normal(0, 1, reg[..., :3].shape) * sd, 0, 255)
            reg[..., :3] = fillv.astype(np.uint8)
            m = np.zeros((y1 - y0, x1 - x0), bool); mode = 'none'
        if mode == 'rowprof':                 # 가로로 고른 판: 글자 없는 열 cols 의 줄별 색(중앙값)으로 상자를 다시 칠함
            out[y0:y1, x0:x1, :3] = np.median(im[y0:y1][:, it['cols'], :3], axis=1)[:, None, :].astype(np.uint8)
            mode = 'none'
        if mode == 'colprof':                 # 세로로 고른 판(나무결·줄무늬): 글자 없는 줄 rows 의 열별 색으로 다시 칠함. ink=δ 면 어두운 글자 화소 둘레만
            prof = np.median(im[it['rows']][:, x0:x1, :3], axis=0)[None, :, :]
            if 'delta' in it:
                lum = im[y0:y1, x0:x1, :3].astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
                mk = cv2.dilate((lum < float(np.median(prof @ np.array([0.3, 0.59, 0.11]))) - it['delta']).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=it.get('grow', 2)) > 0
                mk &= im[y0:y1, x0:x1, 3] > 128
                out[y0:y1, x0:x1, :3][mk] = np.broadcast_to(prof, (y1 - y0, x1 - x0, 3))[mk].astype(np.uint8)
            else:
                out[y0:y1, x0:x1, :3] = np.broadcast_to(prof, (y1 - y0, x1 - x0, 3)).astype(np.uint8)
            mode = 'none'
        if mode == 'dark':                    # 밝은 바탕 위 진한 글자: 바탕 밝기보다 많이 어두운 화소 = 글자(큰 글자도 통째로)
            lum = im[y0:y1, x0:x1, :3].astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
            m = lum < np.percentile(lum, 75) - it.get('delta', 45); mode = 'auto'
        elif mode == 'ink':                   # 지정한 글자 색에 가까운 화소만(분홍 글자 등)
            rgbr = im[y0:y1, x0:x1, :3].astype(np.int32)
            m = np.abs(rgbr - np.array(it['ink'])).sum(axis=2) < it.get('tol', 70); mode = 'auto'
        elif mode == 'light':                 # 어두운 바탕 위 밝은 글자
            lum = im[y0:y1, x0:x1, :3].astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
            m = lum > np.percentile(lum, 25) + it.get('delta', 45); mode = 'auto'
        elif mode == 'box':
            m = np.ones((y1 - y0, x1 - x0), bool); mode = 'auto'
        elif mode == 'none' and 'm' in dir() and it.get('erase') == 'flat':
            pass
        else:
            m = ink_mask(im, box, 'alpha' if mode == 'alpha' else 'auto') if mode != 'none' else np.zeros((y1 - y0, x1 - x0), bool)
        col = it.get('color') or measure_color(im, box, m)
        amul = 1.0
        if it.get('amul') and mode == 'alpha' and m.any(): amul = float(np.median(im[y0:y1, x0:x1, 3][m])) / 255.0
        # 잉크 범위 = 한글을 넣을 경계
        if it.get('fit', 'ink') == 'ink' and m.any():
            ys, xs = np.nonzero(m)
            tx0, ty0, tx1, ty1 = x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1
        else:
            tx0, ty0, tx1, ty1 = box
        p = it.get('pad', 0); tx0 += p; ty0 += p; tx1 -= p; ty1 -= p
        # 지우기
        if mode == 'alpha':
            a = out[y0:y1, x0:x1, 3]; a[m] = 0
        elif mode == 'fill':
            out[y0:y1, x0:x1][m] = list(it['fillc']) + [255]
        elif mode == 'auto' and m.any():  # noqa
            mm = np.zeros(im.shape[:2], np.uint8); mm[y0:y1, x0:x1][m] = 255
            mm = cv2.dilate(mm, np.ones((3, 3), np.uint8), iterations=it.get('grow', 2))
            mm[:y0, :] = 0; mm[y1:, :] = 0; mm[:, :x0] = 0; mm[:, x1:] = 0
            src = np.ascontiguousarray(out[..., :3]).copy()
            tr = out[..., 3] < 16
            if tr.any():                                   # 투명 화소(RGB 흰색 등)가 메움에 번지지 않게 — 상자 안 불투명 중앙값으로
                op = out[y0:y1, x0:x1][out[y0:y1, x0:x1, 3] >= 16][:, :3]
                if len(op): src[tr] = np.median(op, axis=0).astype(np.uint8)
                mm[tr] = 0
            rgb = cv2.inpaint(src, mm, 3, cv2.INPAINT_TELEA)
            out[..., :3] = np.where(mm[..., None] > 0, rgb, out[..., :3])
        if not it.get('t'): continue
        W, H = tx1 - tx0, ty1 - ty0
        if W < 2 or H < 2: notes.append('%s 상자 너무 작음 %s' % (id_, box)); continue
        rot = it.get('rot', 0)               # 텍스처 안 글자가 누워 있으면(PIL 반시계 각도) 바로 세워 그린 뒤 같은 각도로 눕힘
        if it.get('full'):                   # 그림 경계에 걸친 낱말: full 크기로 한 번에 그려 crop 위치의 W×H 만 이 판에
            fw_, fh_ = it['full']; cx_, cy_ = it.get('crop', (0, 0))
            m0 = render_mask(it['t'], fw_ * 4, fh_, it.get('font', 'gothic'), False, 'c', spacing=it.get('spacing', 0.04))   # 낱말 본래 폭을 재서
            xs_ = np.nonzero(m0.max(axis=0) > 0.1)[0]; m0 = m0[:, xs_.min():xs_.max() + 1]
            tw_ = min(fw_, int(m0.shape[1] * it.get('stretch', 1.6)))                                                       # 원문처럼 옆으로 늘리되 1.6배까지, 전체 폭 가운데에
            m1 = np.zeros((fh_, fw_), np.float32); ox_ = (fw_ - tw_) // 2
            m1[:, ox_:ox_ + tw_] = cv2.resize(m0, (tw_, fh_), interpolation=cv2.INTER_AREA)
            a = m1[cy_:cy_ + H, cx_:cx_ + W]
        elif it.get('vsize'):                # 원문처럼 한쪽으로 늘린 글자: vsize 비율로 그린 뒤 상자 크기로 늘림
            vw_, vh_ = it['vsize']
            a = cv2.resize(render_mask(it['t'], vw_ * 4, vh_ * 4, it.get('font', 'gothic'), it.get('v', False), it.get('align', 'c'), spacing=it.get('spacing', 0.08)), (W, H), interpolation=cv2.INTER_AREA)
        elif rot not in (0, 90, 270):          # 비스듬한 글자: tw×th 로 바로 그린 뒤 rot 도(반시계) 돌려 상자 가운데에
            tw_, th_ = it['tsize']
            a0 = render_mask(it['t'], tw_, th_, it.get('font', 'gothic'), it.get('v', False), it.get('align', 'c'), spacing=it.get('spacing', 0.08))
            r = Image.fromarray((a0 * 255).astype(np.uint8)).rotate(rot, resample=Image.BICUBIC, expand=True)
            cx, cy = (tx0 + tx1) / 2, (ty0 + ty1) / 2
            tx0, ty0 = int(round(cx - r.width / 2)), int(round(cy - r.height / 2)); tx0 = max(0, tx0); ty0 = max(0, ty0)
            a = np.array(r).astype(np.float32) / 255.0
        elif rot in (90, 270):
            a = render_mask(it['t'], H, W, it.get('font', 'gothic'), it.get('v', False), it.get('align', 'c'), spacing=it.get('spacing', 0.08))
            a = np.ascontiguousarray(np.rot90(a, rot // 90))
        else:
            a = render_mask(it['t'], W, H, it.get('font', 'gothic'), it.get('v', False), it.get('align', 'c'), spacing=it.get('spacing', 0.08), cell_px=it.get('cell'))
        if it.get('gain'): a = np.clip(a * it['gain'], 0, 1)      # 가는 글꼴 진하게
        if it.get('bold'): a = cv2.dilate(a, np.ones((2, 2), np.float32), iterations=it['bold'])
        if it.get('flip') == 'v': a = a[::-1].copy()
        if it.get('flip') == 'h': a = a[:, ::-1].copy()
        if it.get('stroke'):
            sc, sw = it['stroke']
            k = np.ones((2 * sw + 1, 2 * sw + 1), np.uint8)
            st = cv2.dilate((a * 255).astype(np.uint8), k).astype(np.float32) / 255.0
            blend(out, tx0, ty0, st, sc, amul)
        blend(out, tx0, ty0, a, col, amul)
    for (cx0, cy0, cx1, cy1) in CLEAN.get(id_, []):        # 원문 글자만 있던 구역: 이번에 그린 한글 말고 남은 원문 화소 지움
        reg = out[cy0:cy1, cx0:cx1]; orig = im[cy0:cy1, cx0:cx1]
        same = (np.abs(reg.astype(int) - orig.astype(int)).sum(axis=2) == 0) & (orig[..., 3] > 0)
        reg[same, 3] = 0
    Image.fromarray(out).save(os.path.join(D, 'new', id_ + '.png'))
    return notes

def blend(out, x, y, a, col, amul=1.0):
    H_, W_ = out.shape[:2]
    a = a[:max(0, H_ - y), :max(0, W_ - x)]
    h, w = a.shape
    reg = out[y:y + h, x:x + w].astype(np.float32)
    c = np.array(col[:3], np.float32)
    reg[..., :3] = reg[..., :3] * (1 - a[..., None]) + c * a[..., None]
    reg[..., 3] = np.maximum(reg[..., 3], a * 255 * amul)
    out[y:y + h, x:x + w] = np.clip(reg, 0, 255).astype(np.uint8)

def previews(ids, group, label):
    f = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 14)
    cells = []
    for k in ids:
        a = Image.open(os.path.join(D, 'png', k + '.png')).convert('RGBA')
        b = Image.open(os.path.join(D, 'new', k + '.png')).convert('RGBA')
        w, h = a.size; s = max(1, min(4, 300 // max(w, h))) if max(w, h) < 300 else 300 / max(w, h)
        nw, nh = int(w * s), int(h * s)
        def prep(im):
            im = im.resize((nw, nh), Image.NEAREST if s >= 1 else Image.LANCZOS)
            bg = Image.new('RGBA', im.size, (110, 110, 120, 255)); bg.alpha_composite(im); return bg.convert('RGB')
        c = Image.new('RGB', (nw * 2 + 30, nh + 24), (32, 32, 38))
        c.paste(prep(a), (4, 2)); c.paste(prep(b), (nw + 26, 2))
        ImageDraw.Draw(c).text((4, nh + 4), '%s  %s' % (k, label.get(k, '')), font=f, fill=(255, 220, 90))
        cells.append(c)
    # 한 장 = 세로로 쌓되 높이 1800 까지
    pages = []; cur = []; hsum = 0
    for c in cells:
        if cur and hsum + c.height > 1800: pages.append(cur); cur = []; hsum = 0
        cur.append(c); hsum += c.height + 6
    if cur: pages.append(cur)
    os.makedirs(os.path.join(D, '미리보기'), exist_ok=True)
    outs = []
    for i, pg in enumerate(pages, 1):
        W = max(c.width for c in pg); H = sum(c.height + 6 for c in pg)
        sh = Image.new('RGB', (W, H), (20, 20, 24)); y = 0
        for c in pg: sh.paste(c, (0, y)); y += c.height + 6
        p = os.path.join(D, '미리보기', '%s_%02d.png' % (group, i))
        try: sh.save(p)
        except OSError: p = p[:-4] + '_new.png'; sh.save(p)          # 보는 프로그램이 잡고 있으면 다른 이름으로
        outs.append(p)
    return outs

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(os.path.join(D, 'new'), exist_ok=True)
    SPEC, GROUP = load_spec()
    want = sys.argv[1:] or list(SPEC)
    notes = []
    for k in want:
        if SPEC[k]: notes += apply(k, SPEC[k])
    # 축소판(먼 거리용 작은 텍스처) = 원본 + (큰 새것 축소 − 큰 원본 축소) — 바뀐 곳만 옮김
    for small, big in getattr(load_spec.__globals__.get('_m', None) or __import__('types'), 'DERIVE', {}).items() if False else DERIVE_MAP().items():
        if want and small not in want and big not in want: continue
        so = np.array(Image.open(os.path.join(D, 'png', small + '.png')).convert('RGBA')).astype(np.float32)
        bo = Image.open(os.path.join(D, 'png', big + '.png')).convert('RGBA'); bn = Image.open(os.path.join(D, 'new', big + '.png')).convert('RGBA')
        sz = (so.shape[1], so.shape[0])
        d_ = np.array(bn.resize(sz, Image.BOX)).astype(np.float32) - np.array(bo.resize(sz, Image.BOX)).astype(np.float32)
        Image.fromarray(np.clip(so + d_, 0, 255).astype(np.uint8)).save(os.path.join(D, 'new', small + '.png'))
        SPEC[small] = []; GROUP[small] = GROUP.get(big, '기타')
    label = {}
    for fn in ('선택_범위1.tsv', '선택_범위1_보충.tsv'):
        for l in open(os.path.join(D, fn), encoding='utf-8').read().splitlines()[1:]:
            c = l.split('\t'); label[c[0]] = c[2]
    groups = {}
    for k in SPEC: groups.setdefault(GROUP.get(k, '기타'), []).append(k)
    if sys.argv[1:]:                                     # id 를 지정하면 그 id 가 든 묶음의 미리보기만 다시
        groups = {g: ks for g, ks in groups.items() if set(ks) & set(want)}
    for g, ks in groups.items():
        for p in previews(ks, g, label): print(p)
    for n in notes: print('!', n)

if __name__ == '__main__':
    main()
