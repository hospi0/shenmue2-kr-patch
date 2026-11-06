# -*- coding: utf-8 -*-
"""1ST_READ.BIN 문자열을 «포인터 기준»으로 전수 추출(읽기 전용).
포인터 = 0x0C010000 + 파일 오프셋 (P0, 4정렬 워드). 대상 위치에서 NUL 까지 읽어 EUC-JP 로 풀리고 JIS 2바이트 글자가 하나 이상이면 문자열로 본다.
출력: work/exe_strings.tsv  (문자열오프셋, 참조수, 참조위치들, 바이트길이, 다음문자열까지 여유, 본문)"""
import struct, sys, collections
BASE = 0x8C010000
DATA_LO = 0x210000   # II: 이 뒤는 문자열·표(데이터) — 첫 문자열 0x2137xx
def main(path, out):
    d = open(path, 'rb').read()
    # ★참조 = «PC 상대 리터럴로 실제 읽히는 워드» 또는 «데이터 영역(DATA_LO 이후) 워드»만.
    #   코드 안에서 우연히 0x0C2xxxxx 꼴이 된 바이트(16비트 표 조각 등)를 포인터로 고치면 코드가 깨진다(2곳 실측).
    lits = set()
    for i in range(0, len(d) - 1, 2):
        w = d[i] | d[i+1] << 8
        if (w & 0xF000) == 0xD000: lits.add(((i + 4) & ~3) + (w & 0xFF) * 4)
    refs = collections.defaultdict(list)
    for i in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, i)[0]
        if BASE <= v < BASE + len(d) and (i in lits or i >= DATA_LO): refs[v - BASE].append(i)
    rows = []
    for t in sorted(refs):
        e = d.find(b'\0', t)
        raw = d[t:e]
        if len(raw) < 2: continue
        try: s = raw.decode('euc_jp')
        except UnicodeDecodeError: continue
        if not any(ord(c) > 0x2000 for c in s): continue
        if any(ord(c) < 0x20 and c not in '\n\t' for c in s): continue
        rows.append([t, refs[t], len(raw), s])
    # 여유 = 다음 «참조되는» 위치까지
    tg = sorted(refs)
    import bisect
    for r in rows:
        k = bisect.bisect_right(tg, r[0])
        r.append((tg[k] if k < len(tg) else len(d)) - r[0])
    with open(out, 'w', encoding='utf-8', newline='\n') as o:
        for t, rf, ln, s, room in rows:
            o.write('%06X\t%d\t%s\t%d\t%d\t%s\n' % (t, len(rf), ','.join('%06X' % x for x in rf[:8]), ln, room, s.replace('\n', '\n')))
    return rows
if __name__ == '__main__':
    rows = main(sys.argv[1], sys.argv[2])
    print(len(rows), sum(len(r[3]) for r in rows))
