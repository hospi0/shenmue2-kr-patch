# -*- coding: utf-8 -*-
"""쉔무 II SRF 파싱(읽기 전용, 2026-11-04). 1편과 달리 꼬리표 덩어리:
  CHID(u32 len=12, 화자 4자 'RYO_') · [STDL(u32 len, 자막 EUC-JP + NUL 패딩) 없으면 자막 없음] · CLIP(u32 len, 립싱크 …FFFFFFFF) · ENDC(u32 0)
  len 은 «태그·길이 8바이트 포함». 레코드 순서 = AFS 안 음성(.ahx) 순서로 추정(확인 필요).
  python tools/srf2.py --disc N   → 장 전체 STREAM AFS 의 SRF 통계 / work/srf_discN.tsv"""
import sys, os, struct, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def parse(b):
    """[(화자, 자막 bytes 또는 None, 덩어리 목록)]"""
    out = []; i = 0; cur = None
    while i + 8 <= len(b):
        tag = b[i:i+4]; ln = struct.unpack_from('<I', b, i + 4)[0]
        if tag == b'CHID':
            cur = [b[i+8:i+ln].decode('ascii', 'replace'), None, []]
        elif tag == b'STDL' and cur is not None:
            cur[1] = b[i+8:i+ln].rstrip(b'\0')
        elif tag == b'ENDC':
            if cur is not None: out.append(tuple(cur)); cur = None
            i += 8; continue
        elif not tag.strip(b'\0'):
            i += 4; continue
        if cur is not None: cur[2].append(tag.decode('ascii', 'replace'))
        if ln < 8: break
        i += ln
    return out

def afs_entries(read, lba, size):
    h = read(lba, 2048)
    assert h[:3] == b'AFS', h[:4]
    n = struct.unpack_from('<I', h, 4)[0]
    need = 8 + 8 * n + 8
    h = read(lba, need)
    ents = [struct.unpack_from('<II', h, 8 + 8 * k) for k in range(n)]
    return ents

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--disc', type=int, default=1); a = ap.parse_args()
    import iso_extract
    from gdi import Disc
    iso_extract.D = D = Disc(a.disc)
    files = [e for e in iso_extract.walk() if not (e[3] & 2) and e[0].upper().endswith('.AFS') and '/STREAM/' in e[0].upper()]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = []; spk = collections.Counter(); nrec = ntxt = 0; chars = 0
    for full, lba, size, fl in files:
        ents = afs_entries(D.read, lba, size)
        off, sz = ents[-1]
        b = D.read(lba + off // 2048, (off % 2048) + sz)[off % 2048:]
        if b[:4] != b'CHID': continue
        for k, (who, t, tags) in enumerate(parse(b)):
            nrec += 1
            if t is None: continue
            s = t.decode('euc_jis_2004', 'replace'); ntxt += 1; chars += len(s); spk[who] += 1
            rows.append('%s\t%d\t%s\t%s' % (full, k, who, s.replace('\n', '\\n')))
    os.makedirs(os.path.join(root, 'work'), exist_ok=True)
    open(os.path.join(root, 'work', 'srf_disc%d.tsv' % a.disc), 'w', encoding='utf-8', newline='\n').write('afs\trec\tspeaker\ttext\n' + '\n'.join(rows) + '\n')
    print('disc %d: STREAM AFS %d · SRF 레코드 %d · 자막 %d줄 · %d자 · 화자 %d' % (a.disc, len(files), nrec, ntxt, chars, len(spk)))
    print(spk.most_common(12))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main()
