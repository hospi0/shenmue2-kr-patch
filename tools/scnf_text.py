# -*- coding: utf-8 -*-
"""PKS 밖에 박힌 SCNF 대사표 제자리 번역(2026-11-04 «미추출 다시 확인»).

  · MISC/COLD.BIN · MISC/COLDINIT.PKS(gzip) — 혼잣말·가게 닫힘·문 너머 목소리(SY07·F1195 …, 자막 SRF 와 같은 ID)
  · SCENE/0N/JHD0/MAPINFO.BIN — 하즈키 집 잠자리 혼잣말 SYS01·SYS02(음성·SRF 없음 → 이 글이 그대로 화면에)
SCNF = 'SCNF' u32 크기 · u32 하위 개수 · u32 ? · 하위 덩어리들(이름4 · u32 크기 · 16 B 표(본문 위치·ID 위치·코드·f32) · 문자열 풀).
  표의 위치는 «그 하위 덩어리 시작» 기준(PKS 는 하위가 하나라 0x10 기준과 같음). ID 는 8~9자(SY07A001 / F1195A007).
다시 쌓기: 하위마다 풀을 새로 쌓아 크기를 고치고 이어 붙임 — SCNF 전체 크기는 그대로(남는 곳 0), 넘치면 오류.
"""
import struct, re

IDRX = re.compile(rb'[A-Z][0-9A-Z]{6,9}\x00')

def chunks(d):
    i = 0
    while True:
        i = d.find(b'SCNF', i)
        if i < 0: return
        L = struct.unpack_from('<I', d, i + 4)[0]
        if 0x20 < L < 0x100000 and i + L <= len(d): yield i, L
        i += 4

def _sub_rows(sub):
    m = IDRX.search(sub, 8)
    if not m: return None, []
    pool = m.start()
    words = struct.unpack_from('<%dI' % (pool // 4), sub)
    rows = []; seen = set()
    for w in range(1, len(words)):
        idp = words[w]
        if pool <= idp < len(sub) and IDRX.match(sub, idp):
            tp = words[w - 1]
            if pool <= tp < len(sub) and (w - 1) * 4 not in seen:
                rows.append(((w - 1) * 4, idp, tp)); seen.add((w - 1) * 4)
    return pool, rows

def patch(d, translate):
    """translate(ID, 원문 str) → 새 글 bytes(EUC) 또는 None. 돌려줌 (새 데이터, 바꾼 줄 수, [(ID, 원문)])"""
    d = bytearray(d); n = 0; seen = []
    for s, L in list(chunks(bytes(d))):
        sc = bytes(d[s:s + L]); cnt = struct.unpack_from('<I', sc, 8)[0]
        if not (0 < cnt < 64): continue
        subs = []; b = 0x10
        for _ in range(cnt):
            sz = struct.unpack_from('<I', sc, b + 4)[0]
            if sz < 8 or b + sz > L: subs = None; break
            subs.append(sc[b:b + sz]); b += sz
        if not subs: continue
        out = bytearray(sc[:0x10])
        for sub in subs:
            pool, rows = _sub_rows(sub)
            if not rows: out += sub; continue
            order = []; pend = pool
            while pend < len(sub):
                e = sub.find(b'\0', pend)
                if e < 0 or e == pend: break
                order.append(pend); pend = e + 1
            text_of = {tp: sub[idp:sub.index(b'\0', idp)].decode('ascii') for _, idp, tp in rows}
            newpool = bytearray(); remap = {}
            for p in order:
                cur = sub[p:sub.index(b'\0', p)]
                if p in text_of:
                    jt = cur.decode('euc_jp', 'replace'); seen.append((text_of[p], jt))
                    nb = translate(text_of[p], jt)
                    if nb is not None: cur = nb; n += 1
                remap[p] = pool + len(newpool); newpool += cur + b'\0'
            ns = bytearray(sub[:pool]) + newpool
            ns += b'\0' * ((-len(ns)) % 4)
            for roff, idp, tp in rows:
                struct.pack_into('<II', ns, roff, remap[tp], remap[idp])
            struct.pack_into('<I', ns, 4, len(ns))
            out += ns
        if len(out) > L: raise SystemExit('SCNF %X 넘침: %d B > %d B' % (s, len(out), L))
        d[s:s + L] = out + b'\0' * (L - len(out))
    return bytes(d), n, seen

if __name__ == '__main__':
    import sys, os
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pak
    for p in sys.argv[1:]:
        raw, d = pak.load(p)
        nd, k, seen = patch(d, lambda i, t: None)
        print(p, '줄', len(seen), '원본과 같음' if nd == d else '다름!')
