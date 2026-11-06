# -*- coding: utf-8 -*-
"""PAKS/IPAC 묶음(MISC/COLD.BIN·COLDINIT.PKS(gzip) 등) 항목 바꾸기 + gzip 원래 머리 유지 재압축.

IPAC 디렉터리 = IPAC+dpos, 20 B × n (이름 8 · 형식 4 · 위치(IPAC 기준) · 크기).
★게임은 글꼴을 MISC/*.FON 이 아니라 이 묶음 안 DC_KANJI·RYOU 항목에서 쓴다(2026-11-03 1차 시험 빌드 — 자막 코드는 한글인데 한자 그림).
"""
import struct, zlib, gzip
GZ = bytes((0x1F, 0x8B))

def entries(d):
    ip = 0x10; assert d[:4] == b'PAKS' and d[ip:ip+4] == b'IPAC'
    dpos, n, size = struct.unpack_from('<III', d, ip + 4)
    out = {}
    for i in range(n):
        p = ip + dpos + i * 20
        out[d[p:p+8].rstrip(b'\0').decode('latin1')] = (ip + struct.unpack_from('<I', d, p + 12)[0], struct.unpack_from('<I', d, p + 16)[0])
    return out

def replace_same_size(d, repl):
    b = bytearray(d); ents = entries(d)
    for name, data in repl.items():
        off, size = ents[name]
        if len(data) != size: raise ValueError('%s 크기 %d ≠ %d' % (name, len(data), size))
        b[off:off+size] = data
    return bytes(b)

def gz_header_len(g):
    flg = g[3]; p = 10
    if flg & 4: p += 2 + struct.unpack_from('<H', g, p)[0]
    if flg & 8: p = g.index(b'\0', p) + 1
    if flg & 16: p = g.index(b'\0', p) + 1
    if flg & 2: p += 2
    return p

def regzip(orig_gz, data):
    """원래 gzip 머리(파일 이름·시각) 그대로 + deflate 9 + CRC·길이."""
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = c.compress(data) + c.flush()
    return orig_gz[:gz_header_len(orig_gz)] + body + struct.pack('<II', zlib.crc32(data) & 0xFFFFFFFF, len(data) & 0xFFFFFFFF)

def load(path):
    raw = open(path, 'rb').read()
    return raw, (gzip.decompress(raw) if raw[:2] == GZ else raw)
