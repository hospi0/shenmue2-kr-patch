# -*- coding: utf-8 -*-
"""★조사 전용: 실행 파일의 «이름 + 가나 읽기» 쌍 표를 나열한다. ⛔map_read.tsv 를 덮어쓰지 말 것 — 비우는 줄은 지도 표 0x244 26줄뿐.
  1편은 아이템·낱말 표(ハイ→예 등)에 한글을 넣은 채 실기 통과 — 전부 비우면 선택지가 사라질 수 있다. 결과는 work/check/exe_readings.tsv.
  게임은 읽기 줄을 2바이트 글자의 뒤 바이트만 DC_KANA 칸으로 찍는다 — 한글을 넣으면 쓰레기 글자가 된다(기술 화면·지도에서 확인).
  조건: 가타카나만인 문자열이고 «모든» 포인터 참조가 이름 문자열 바로 뒤 자리. 본문으로도 쓰이는 문자열은 뺀다(비우면 글자가 사라짐).
  python tools/exe_readings.py
"""
import os, sys, re, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import iso_extract as ie
from gdi import Disc
B = 0x8C010000
KANA = re.compile('[ァ-ヶー”・Ａ-Ｚ]*[ァ-ヶー”・][ァ-ヶー”・Ａ-Ｚ]*')

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); ie.D = D
    e = next(x for x in ie.walk() if x[0] == '/1ST_READ.BIN'); o = D.read(e[1], e[2])
    def jp(a):
        z = o.find(b'\0', a); t = o[a:z]
        if not t or len(t) > 60: return ''
        try: return t.decode('euc_jp')
        except Exception: return ''
    ptr = lambda p: struct.unpack_from('<I', o, p)[0] - B
    refs = collections.defaultdict(list)
    for p in range(0, len(o) - 3, 4):
        v = ptr(p)
        if 0x200000 <= v < 0x2D0000: refs[v].append(p)
    out = []; mixed = []; table = collections.Counter()
    for a, ps in sorted(refs.items()):
        j = jp(a).strip('　')
        if not j or not KANA.fullmatch(j): continue
        if 0x225F00 <= a < 0x226700: continue                 # 기술 읽기 줄은 merge_tr 이 처리
        ok = []
        for p in ps:
            q = ptr(p - 4) if p >= 4 else -1
            n = jp(q).strip('　') if 0x200000 <= q < 0x2D0000 else ''
            ok.append(bool(n) and not KANA.fullmatch(n))
        if all(ok):
            out.append((a, jp(a))); table['%X' % (ps[0] & ~0xFFF)] += 1
        elif any(ok): mixed.append((a, j, len(ps), sum(ok)))
    open(os.path.join(ROOT, 'work', 'check', 'exe_readings.tsv'), 'w', encoding='utf-8', newline='\n').write(''.join('exe:%X\t%s\t대\n' % x for x in out))
    print('읽기 줄 %d · 표별 %s' % (len(out), sorted(table.items())))
    print('본문으로도 쓰여 뺀 줄 %d %s' % (len(mixed), [(('%X' % a), j[:10]) for a, j, n, k in mixed[:20]]))

if __name__ == '__main__':
    main()
