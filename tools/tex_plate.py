# -*- coding: utf-8 -*-
"""안내창 깨끗한 판 만들기 — 같은 모양 창을 겹쳐, 화소마다 «그 판에서 글자(검정·밝은 테두리)와 멀리 떨어진» 표본만 모아 중앙값. python tools/tex_plate.py
 → work/tex/판/plate_NN.png(글자 없는 바탕) · 판별 표본 수 그림 plate_NN_cnt.png"""
import os, sys
import numpy as np, cv2
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = os.path.join(ROOT, 'work', 'tex'); O = os.path.join(T, '판'); os.makedirs(O, exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8')
L = {l.split('\t')[1]: l.split('\t') for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:] if l}
g = {}
for n in range(712, 755):
    if n == 713: continue
    a = np.array(Image.open(os.path.join(T, 'png', L[str(n)][2] + '.png')).convert('RGBA')); g.setdefault((a[..., 3] > 0).tobytes(), []).append((n, a))
w3 = np.array([.3, .59, .11], np.float32)
for i, (k, v) in enumerate(sorted(g.items(), key=lambda x: -len(x[1]))):
    st = np.stack([a for _, a in v]).astype(np.float32); al = v[0][1][..., 3] > 0
    m1 = np.median(st, axis=0)
    ms = []
    for _, a in v:                                           # 실측: 글자 밝기<60, 밝은 테두리 2화소 → 획 둘레 3화소만 뺀다
        l = a[..., :3].astype(np.float32) @ w3
        ms.append(cv2.dilate((l < 70).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
    ms = np.stack(ms); rgb = st[..., :3].copy(); rgb[ms] = np.nan
    import warnings; warnings.simplefilter('ignore')
    m2 = np.nanmedian(rgb, axis=0); cnt = (~ms).sum(axis=0)
    edge = (np.stack(ms).mean(axis=0) > .95) & al             # 전 판에서 어두운 곳 = 그림 자체(모서리 장식·틀)
    bad = np.isnan(m2).any(axis=2) & al & ~edge
    m2 = np.where(np.isnan(m2), m1[..., :3], m2).astype(np.uint8)
    if bad.any(): m2 = cv2.inpaint(np.ascontiguousarray(m2), bad.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    out = np.dstack([m2, v[0][1][..., 3]]); Image.fromarray(out).save(os.path.join(O, 'plate_%02d.png' % i))
    print(i, '판', len(v), '장 · 표본 없는 화소', int(bad.sum()), '· 최소 표본', int(cnt[al].min()))
