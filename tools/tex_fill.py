# -*- coding: utf-8 -*-
"""그림 번역표 채우기 — work/tex/번역/*.tsv 의 빈 «한글»을 실행 파일 지명 줄(일본어 + 영문 짝, 병합본)에서 끌어온다 → 표기가 대사와 자동으로 같음.
 번호 → id 는 work/tex/선별/선별목록.tsv 에서(손으로 옮기지 않음). 결과 work/tex/번역/채움/*.tsv (번호·id·크기·원문·한글·메모)
 python tools/tex_fill.py"""
import os, sys, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
T = os.path.join(ROOT, 'work', 'tex')
ids = {}
for l in open(os.path.join(T, '선별', '선별목록.tsv'), encoding='utf-8').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) > 4: ids[c[1]] = c
m = {}
for f in glob.glob(os.path.join(ROOT, 'work', 'text', 'ko', 'sm2_*.tsv')):
    for l in open(f, encoding='utf-8').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) > 4 and c[0].startswith('exe:') and '   ' in c[3]:
            m[c[3].split('   ')[0]] = c[4].split('   ')[0]
os.makedirs(os.path.join(T, '번역', '채움'), exist_ok=True)
for f in sorted(glob.glob(os.path.join(T, '번역', '*.tsv'))):
    L = open(f, encoding='utf-8').read().split('\n'); out = ['번호\tid\t폭\t높이\t원문\t한글\t메모']; miss = []
    for l in L[1:]:
        if not l: continue
        c = (l.split('\t') + ['', '', ''])[:4]
        if c[0] not in ids: miss.append('번호없음 ' + c[0]); continue
        ko = c[2] or m.get(c[1], '')
        if not ko: miss.append(c[0] + ' ' + c[1])
        r = ids[c[0]]; out.append('\t'.join([c[0], r[2], r[3], r[4], c[1], ko, c[3]]))
    open(os.path.join(T, '번역', '채움', os.path.basename(f)), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    print(os.path.basename(f), len(out) - 1, '못 채움', miss)
