# -*- coding: utf-8 -*-
"""쉔무 II 원문 추출(읽기 전용, 2026-11-04) — 4장 자막(SRF STDL) + 장마다 NPC(HUMANS PKS) + 실행 파일 문자열.
  → work/text/lines.tsv   (kind · key · speaker · jp · where)  넣을 자리 전부
  → work/text/tsv/sm2_NNN.tsv (key · speaker · count · jp · ko)  같은 원문 = 한 줄, 18 KB 단위(자투리는 앞 묶음에)
  자막·NPC 줄바꿈 = ＆. 실행 파일 문자열은 포인터 기준(적재 0x8C010000), 가나·한자 든 것만.
  python tools/extract2.py
"""
import os, sys, re, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import iso_extract, srf2, pks
from gdi import Disc
from afs import read_afs

BASE = 0x8C010000
CHUNK = 18 * 1024

def afs_files(D):
    iso_extract.D = D
    return [e for e in iso_extract.walk() if not (e[3] & 2)]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []            # (kind, key, speaker, jp, where)
    for n in (1, 2, 3, 4):
        D = Disc(n); ents = afs_files(D)
        for full, lba, size, fl in ents:
            U = full.upper()
            if U.endswith('.AFS') and '/STREAM/' in U:
                es = srf2.afs_entries(D.read, lba, size)
                off, sz = es[-1]
                b = D.read(lba + off // 2048, (off % 2048) + sz)[off % 2048:]
                if b[:4] != b'CHID': continue
                an = full.rsplit('/', 1)[1][:-4]
                for k, (who, t, tags) in enumerate(srf2.parse(b)):
                    if t is None: continue
                    jp = t.decode('euc_jis_2004', 'replace').replace('\n', '＆')
                    rows.append(('srf', '%s#%d' % (an, k), who.rstrip('_'), jp, '%d:%s' % (n, full)))
            elif U.endswith('/NPC/HUMANS.AFS'):
                d = D.read(lba, size)
                import io
                p = os.path.join(ROOT, 'work', '_humans_tmp.afs'); open(p, 'wb').write(d)
                dd, es = read_afs(p); os.remove(p)
                for nm, o, s in es:
                    if not nm.upper().endswith('.PKS'): continue
                    for idk, t in pks.strings(dd[o:o + s]):
                        jt = t.decode('euc_jis_2004', 'replace')
                        spk = jt.split('「', 1)[0] if '「' in jt[:12] else ''
                        rows.append(('pks', idk, spk, jt.replace('\n', '＆'), '%d:%s/%s' % (n, full, nm)))
        print('disc %d: 누계 %d' % (n, len(rows)), flush=True)
    # 실행 파일(1장 것 — 장마다 같은지 확인은 따로)
    D = Disc(1)
    e = [x for x in afs_files(D) if x[0] == '/1ST_READ.BIN'][0]
    d = D.read(e[1], e[2]); refs = collections.Counter()
    for i in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, i)[0]
        if BASE <= v < BASE + len(d): refs[v - BASE] += 1
    nexe = 0
    # 잡음(포인터가 우연히 가리킨 부동소수·코드 조각) — 짧은 한자 이름은 남김(2026-11-04 하스피 «한자 한두 글자는 쓸리지 않게»)
    NOISE = {0x2137B2, 0x21F0A4, 0x21FB6E, 0x22074C, 0x238FA0, 0x239058, 0x23905C, 0x239060, 0x23B280, 0x2409A8,
             0x24B9FC, 0x24BA08, 0x25372C, 0x253750}
    # DC_KANJI 희귀 한자 칸에 기술 이름 글자를 다시 그려 쓴 문자열 85개 — 그림으로 읽은 원문(work/text/remap_font_decoded.tsv)
    REMAP = {}
    rp = os.path.join(ROOT, 'work', 'text', 'remap_font_decoded.tsv')
    if os.path.exists(rp):
        for l in open(rp, encoding='utf-8').read().splitlines()[1:]:
            c = l.split('\t'); REMAP[int(c[0][4:], 16)] = c[1] + ('〔판독?〕' if len(c) > 2 and c[2] else '')
    for o in sorted(refs):
        if o in NOISE: continue
        if o in REMAP:
            rows.append(('exe', 'exe:%06X' % o, '글꼴재배치', REMAP[o], 'refs=%d' % refs[o])); nexe += 1; continue
        s = d[o:d.find(b'\0', o)]
        if 2 <= len(s) < 600 and re.fullmatch(rb'(?:[\xa1-\xfe][\xa1-\xfe]|[\x09\x0a\x20-\x7e])+', s) and re.search(rb'[\xa4\xa5][\xa1-\xf6]|[\xb0-\xf4][\xa1-\xfe]', s):
            rows.append(('exe', 'exe:%06X' % o, '', s.decode('euc_jis_2004', 'replace').replace('\n', '＆').replace('\t', '＼ｔ'), 'refs=%d' % refs[o])); nexe += 1
    os.makedirs(os.path.join(ROOT, 'work', 'text', 'tsv'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'text', 'lines.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('kind\tkey\tspeaker\tjp\twhere\n')
        for r in rows: w.write('\t'.join(r) + '\n')
    # 번역 묶음: (무리, 원문) 하나 = 한 줄 — 실행 파일은 따로 무리
    seen = collections.OrderedDict()
    for kind, key, spk, jp, where in rows:
        g = 'exe' if kind == 'exe' else 'talk'
        if kind == 'pks' and '「' in jp:              # 화자「본문」 → 본문만(같은 말을 화자만 달리 하는 NPC 가 많음 — 빌더가 화자 붙임)
            jp = jp.split('「', 1)[1]
            if jp.endswith('」'): jp = jp[:-1]
        k = (g, jp)
        if k in seen: seen[k][2] += 1
        else: seen[k] = [key, spk, 1]
    out = []; cur = ['key\tspeaker\tcount\tjp\tko\n']; size = 0
    for (g, jp), (key, spk, c) in seen.items():
        ln = '%s\t%s\t%d\t%s\t\n' % (key, spk, c, jp)
        if size + len(ln.encode('utf-8')) > CHUNK and len(cur) > 1:
            out.append(cur); cur = ['key\tspeaker\tcount\tjp\tko\n']; size = 0
        cur.append(ln); size += len(ln.encode('utf-8'))
    if len(cur) > 1:
        if out and size < CHUNK // 3: out[-1] += cur[1:]
        else: out.append(cur)
    for i, c in enumerate(out, 1):
        open(os.path.join(ROOT, 'work', 'text', 'tsv', 'sm2_%03d.tsv' % i), 'w', encoding='utf-8', newline='\n').write(''.join(c))
    cnt = collections.Counter(r[0] for r in rows)
    print('자리 %s · 고유 원문 %d (대사 %d · 실행 파일 %d) · 묶음 %d개' % (dict(cnt), len(seen), sum(1 for k in seen if k[0] == 'talk'), sum(1 for k in seen if k[0] == 'exe'), len(out)))

if __name__ == '__main__':
    main()
