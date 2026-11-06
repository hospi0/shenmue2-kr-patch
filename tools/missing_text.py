# -*- coding: utf-8 -*-
"""번역표에 없는 글 모으기(2026-11-06) — MISC/MEMODATA.BIN(메모장 본문 MSTR) + PKS 밖 SCNF(FREETALK·SYSTALK·COLD.BIN).
  → work/text/missing.tsv  (kind · key · speaker · count · jp · 풀이)
  메모 사전 코드는 tools 쪽 표가 확정되면 풀이 열에 펼친다.
  python tools/missing_text.py
"""
import os, sys, re, struct, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import iso_extract as ie
from gdi import Disc
import pak, scnf_text as sc

def memo_chunks(b):
    i = 0; out = {}
    while i + 8 <= len(b):
        t = b[i:i+4]; L = struct.unpack_from('<I', b, i + 4)[0]
        if t not in (b'MEMO', b'RUBI', b'MSTR') or L < 8: break
        out[t.decode()] = (i, L); i += L
    return out

def memo_strings(b):
    """MSTR 안 문자열 [(위치(MSTR 본문 기준), bytes)] — MEMO·RUBI 표 값 = MSTR+8 기준 위치"""
    c = memo_chunks(b); o, L = c['MSTR']; s = b[o+8:o+L]; out = []; i = 0
    while i < len(s):
        e = s.find(b'\0', i)
        if e < 0: e = len(s)
        if e > i: out.append((i, s[i:e]))
        i = e + 1
    return out

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tr = {}
    for f in glob.glob(os.path.join(ROOT, 'work', 'text', 'ko', 'sm2_*.tsv')):
        for l in open(f, encoding='utf-8'):
            c = l.rstrip('\n').split('\t')
            if len(c) >= 5 and c[0] != 'key': tr[c[3]] = c[4]
    body = lambda t: t.split('「', 1)[1][:-1] if '「' in t and t.endswith('」') else t
    seen = collections.OrderedDict(); memo = {}
    for n in (1, 2, 3, 4):
        D = Disc(n); ie.D = D
        E = {e[0]: e for e in ie.walk() if not e[3] & 2}
        rd = lambda f: D.read(E[f][1], E[f][2])
        b = rd('/MISC/MEMODATA.BIN')
        memo.setdefault(b, n)
        srcs = [(f, rd(f)) for f in E if f.startswith('/MISC/') and re.search(r'/(FREETALK|FREETLK\d|SYSTALK)\.BIN$', f)]
        cold = rd('/MISC/COLD.BIN'); srcs += [('COLD:' + k, cold[o:o+s]) for k, (o, s) in pak.entries(cold).items() if k == 'SYSTALK']
        for f, d in srcs:
            _, _, rows = sc.patch(d, lambda i, t: None)
            for idk, t in rows:
                t1 = t.replace('\n', '＆'); bd = body(t1)
                if bd in tr or t1 in tr: continue
                spk = t1.split('「', 1)[0] if '「' in t1 else ''
                k = (idk, bd)
                if k not in seen: seen[k] = [spk, 0, set()]
                seen[k][1] += 1; seen[k][2].add(f.rsplit('/', 1)[-1])
    print('MEMODATA 종류', len(memo), [v for v in memo.values()])
    rows = ['kind\tkey\tspeaker\tcount\tjp\twhere']
    for (idk, bd), (spk, c, w) in seen.items():
        rows.append('scnf\t%s\t%s\t%d\t%s\t%s' % (idk, spk, c, bd, ','.join(sorted(w))))
    nm = 0
    for b in memo:
        for o, s in memo_strings(b):
            t = s.decode('euc_jp', 'replace')
            rows.append('memo\tmemo:%X\t\t1\t%s\tMEMODATA' % (o, t)); nm += 1
        break
    open(os.path.join(ROOT, 'work', 'text', 'missing.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(rows) + '\n')
    print('SCNF 빠진 줄', len(seen), '· 메모 문자열', nm)

if __name__ == '__main__':
    main()
