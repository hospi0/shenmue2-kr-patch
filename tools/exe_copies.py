# -*- coding: utf-8 -*-
"""실행 파일에서 같은 원문의 다른 주소 사본 → 이미 있는 번역을 채운 표 work/text/copy_ko.tsv (merge_extra 가 ko_extra/sm2_190 에 넣음).
  빼는 것: 기술 낱자 비교 표(0x252000~0x254000 참조 — 원문으로 strcmp), 코드가 문자열처럼 잡힌 값, 번역이 원문과 같은 값.
  앞뒤 전각 공백은 원문 칸 그대로 둔다.
  python tools/exe_copies.py   (build_exe 이후 — 번역표·원본 실행 파일 기준)
"""
import os, sys, re, glob, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import iso_extract as ie
from gdi import Disc
B = 0x8C010000; LOCK = (0x252000, 0x254000)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); ie.D = D
    e = next(x for x in ie.walk() if x[0] == '/1ST_READ.BIN'); o = D.read(e[1], e[2])
    rows = {}
    skip = os.path.basename('sm2_190.tsv')
    for f in glob.glob(os.path.join(ROOT, 'work', 'text', 'ko', 'sm2_*.tsv')) + glob.glob(os.path.join(ROOT, 'work', 'text', 'ko_extra', 'sm2_*.tsv')):
        if os.path.basename(f) == skip: continue
        for l in open(f, encoding='utf-8').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) >= 5 and c[0].startswith('exe:') and c[4]: rows[int(c[0][4:], 16)] = c
    byjp = {}
    for a, c in sorted(rows.items()):
        k_, v_ = c[3].strip('　'), c[4].strip('　')
        if v_ or k_ not in byjp: byjp[k_] = byjp.get(k_) or v_      # 빈칸 번역(읽기 줄)보다 실제 번역 우선
    refs = collections.defaultdict(list)
    for p in range(0, len(o) - 3, 4):
        v = struct.unpack_from('<I', o, p)[0]
        if B + 0x200000 <= v < B + 0x2D0000: refs[v - B].append(p)
    out = []; lock = 0; junk = 0
    for a, ps in sorted(refs.items()):
        if a in rows: continue
        t = o[a:o.find(b'\0', a)]
        if not 2 <= len(t) <= 80 or not re.fullmatch(rb'(?:[\xa1-\xfe][\xa1-\xfe])+', t): continue
        try: j = t.decode('euc_jp')
        except Exception: continue
        k = j.strip('　')
        if k not in byjp or not re.search(r'[ぁ-んァ-ヶ一-龥]', k): continue
        ko = byjp[k]
        if any(LOCK[0] <= p < LOCK[1] for p in ps): lock += 1; continue
        if ko == k or (ko and not re.search('[가-힣]', ko)): junk += 1; continue
        lead = len(j) - len(j.lstrip('　')); tail = len(j) - len(j.rstrip('　'))
        out.append('exe:%X\t%s\t%s\n' % (a, j, '　' * lead + ko + '　' * tail if ko else '　'))
    p = os.path.join(ROOT, 'work', 'text', 'copy_ko.tsv')
    open(p, 'w', encoding='utf-8', newline='\n').write(''.join(out))
    print('채운 사본 %d · 낱자 표라 뺌 %d · 값이라 뺌 %d' % (len(out), lock, junk))

if __name__ == '__main__':
    main()
