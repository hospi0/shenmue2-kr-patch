# -*- coding: utf-8 -*-
"""두 디스크 트랙 폴더의 «파일 단위» 차이 — 설치 전에 이전 판과 비교해 의도하지 않은 변경을 찾는다.
  되읽기 검산은 재료와 디스크가 같은지만 본다. 재료가 낡거나 앞 단계가 지워진 사고는 이 비교로만 드러난다.
  python tools/disc_diff.py <장> <이전 폴더> <새 폴더>
"""
import hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iso_extract as ie, gdi
from gdi import Disc

def load(n, base):
    D0 = Disc(n); G = Disc.__new__(Disc); G.n = n; G.tracks = []
    for t in D0.tracks: G.tracks.append(gdi.Track(os.path.join(base, os.path.basename(t.path)), t.num))
    ie.D = G
    return G, {f: (l, s) for f, l, s, fl in ie.walk() if not fl & 2}

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    n = int(sys.argv[1]); A, ea = load(n, sys.argv[2]); B, eb = load(n, sys.argv[3])
    ch = [f for f in sorted(set(ea) & set(eb)) if ea[f][1] != eb[f][1] or hashlib.md5(A.read(*ea[f])).digest() != hashlib.md5(B.read(*eb[f])).digest()]
    print('장 %d 파일 %d · 바뀜 %d · 없어짐 %d · 새로 %d' % (n, len(eb), len(ch), len(set(ea) - set(eb)), len(set(eb) - set(ea))))
    for f in ch[:60]: print(' ', f, ea[f][1], '→', eb[f][1])

if __name__ == '__main__':
    main()
