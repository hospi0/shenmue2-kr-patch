# -*- coding: utf-8 -*-
"""HUMANS.AFS 의 NPC PKS — SCNF 대사표 읽기/다시 쓰기.

PKS = 'PAKS'(16B) + 'IPAC'(u32 디렉터리 위치(IPAC 기준), u32 개수, u32 크기) + 항목들 + 디렉터리(20B×개수: 이름8·형식4·위치·크기, 위치는 IPAC 기준)
SCNF 항목(형식 'BIN ') = 'SCNF' u32 크기 … +0x10 부터 '하위 청크'(이름4·u32 크기·…). 하위 청크 기준(SCNF+0x10)으로
  · 16B 표: u32 본문 위치, u32 ID 위치, 4B 코드, f32 길이  (표는 문자열 덩어리 앞, 모든 문자열 참조는 이 표에서만 — 140개 전수 확인)
  · 문자열 덩어리: 'F1015B002\\0아케미「…」\\0' … 끝 0 패딩(4정렬)
"""
import struct, re

def _scnf_span(b):
    """(IPAC 위치, 디렉터리 [(이름,형식,위치,크기)], SCNF 항목 번호)"""
    assert b[:4] == b'PAKS' and b[0x10:0x14] == b'IPAC'
    ip = 0x10
    dpos, n, size = struct.unpack_from('<III', b, ip + 4)
    ents = []
    for i in range(n):
        p = ip + dpos + i * 20
        ents.append([b[p:p+8], b[p+8:p+12], struct.unpack_from('<I', b, p+12)[0], struct.unpack_from('<I', b, p+16)[0]])
    k = next((i for i, e in enumerate(ents) if b[ip+e[2]:ip+e[2]+4] == b'SCNF'), None)
    return ip, ents, k

def strings(b):
    """[(ID, 본문 bytes)] — 표 순서."""
    ip, ents, k = _scnf_span(b)
    if k is None: return []
    sc = b[ip+ents[k][2]: ip+ents[k][2]+ents[k][3]]
    return [(sc[i:sc.index(b'\0', i)].decode(), t) for i, t in _table(sc)[1]]

def _table(sc):
    base = 0x10
    m = re.search(rb'[A-Z][0-9A-Z]{8}\x00', sc)
    pool = m.start()
    # 표 = 풀 앞쪽에서 «ID 위치 칸이 풀 안의 ID 를 가리키는» 16B 행들
    rows = []; seen = set()
    words = struct.unpack_from('<%dI' % (pool // 4), sc)
    for w in range(1, len(words), 1):
        idp = words[w] + base
        if pool <= idp < len(sc) and re.match(rb'[A-Z][0-9A-Z]{8}\x00', sc[idp:idp+10]) and w >= 1:
            tp = words[w-1] + base
            if pool <= tp < len(sc) and (w-1) * 4 not in seen:
                rows.append(((w-1) * 4, idp, tp)); seen.add((w-1) * 4)
    return pool, [(idp, sc[tp:sc.index(b'\0', tp)]) for _, idp, tp in rows], rows

def rebuild(b, new_text=None):
    """new_text = {ID: 본문 bytes(EUC, NUL 없음)}. 없으면 원본 그대로 다시 쌓는다(검산용)."""
    new_text = new_text or {}
    ip, ents, k = _scnf_span(b)
    if k is None: return b
    s0, l0 = ip + ents[k][2], ents[k][3]
    sc = bytearray(b[s0:s0+l0]); base = 0x10
    pool, items, rows = _table(bytes(sc))
    # 원래 문자열 순서대로 다시 쌓기(ID·본문 모두 원래 등장 순서)
    order = []; pend = pool
    while pend < len(sc):
        e = sc.find(b'\0', pend)
        if e < 0 or e == pend: break
        order.append(pend); pend = e + 1
    id_at = {idp for _, idp, _ in rows}
    text_of = {tp: sc[idp:sc.index(b'\0', idp)].decode() for _, idp, tp in rows}
    newpool = bytearray(); remap = {}
    for p in order:
        old = sc[p:sc.index(b'\0', p)]
        cur = old
        if p in text_of and text_of[p] in new_text: cur = new_text[text_of[p]]
        remap[p] = pool + len(newpool); newpool += cur + b'\0'
    tail = sc[pend:]  # 원래 끝 패딩
    pad = (-(pool + len(newpool))) % 4
    if not new_text: newsc = sc[:pool] + newpool + tail
    else: newsc = sc[:pool] + newpool + b'\0' * pad
    newsc = bytearray(newsc)
    for roff, idp, tp in rows:
        struct.pack_into('<II', newsc, roff, remap[tp] - base, remap[idp] - base)
    delta = len(newsc) - l0
    struct.pack_into('<I', newsc, 4, len(newsc))
    struct.pack_into('<I', newsc, 0x14, struct.unpack_from('<I', newsc, 0x14)[0] + delta)
    if delta == 0: return b[:s0] + bytes(newsc) + b[s0+l0:]
    # IPAC 안 뒤 항목 밀기 + 디렉터리 갱신
    dpos, n, size = struct.unpack_from('<III', b, ip + 4)
    body = bytearray(b[ip:ip+dpos])
    body[ents[k][2]:ents[k][2]+l0] = newsc
    out = bytearray(b[:ip]) + body
    for i, e in enumerate(ents):
        if i == k: e[3] = len(newsc)
        elif e[2] > ents[k][2]: e[2] += delta
    ndpos = dpos + delta
    for e in ents: out += e[0] + e[1] + struct.pack('<II', e[2], e[3])
    struct.pack_into('<III', out, ip + 4, ndpos, n, size + delta)
    out += b[ip+dpos+n*20:]
    return bytes(out)
