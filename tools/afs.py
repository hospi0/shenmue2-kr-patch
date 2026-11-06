# -*- coding: utf-8 -*-
"""쉔무 AFS 읽기(읽기 전용). 머리 'AFS\0' + 개수 + (off,size)*n, 그 뒤 (목록off,목록size), 목록 = 48B(이름32+날짜6×u16+크기u32)."""
import struct, sys
def read_afs(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'AFS\0', path
    n = struct.unpack_from('<I', d, 4)[0]
    ents = [struct.unpack_from('<II', d, 8 + i*8) for i in range(n)]
    names = [None]*n
    # 목록 포인터: 표 바로 뒤, 아니면 첫 파일 앞 마지막 8B
    cand = [8 + n*8, ents[0][0] - 8] if n else []
    for p in cand:
        lo, ls = struct.unpack_from('<II', d, p)
        if lo and ls == n*48 and lo + ls <= len(d):
            names = [d[lo+i*48:lo+i*48+32].split(b'\0')[0].decode('ascii','replace') for i in range(n)]
            break
    return d, [(names[i] or '%04d' % i, o, s) for i, (o, s) in enumerate(ents)]
if __name__ == '__main__':
    d, es = read_afs(sys.argv[1])
    for nm, o, s in es:
        print('%-32s %08X %8d %s' % (nm, o, s, d[o:o+4]))


def build_afs(orig, files):
    """원본 AFS 바이트의 머리 배치(첫 파일 위치·이름 목록)를 따라 새 파일들로 다시 만든다.
    files = [(이름, 바이트)] 원본 순서 그대로. 날짜는 원본 목록에서 가져오고 크기만 갱신.
    규칙(원본 검산): 파일은 0x800 정렬, 첫 파일 위치는 원본 그대로, (목록위치,목록크기)는 첫 파일 바로 앞 8B, 목록 뒤 0x800 정렬."""
    import struct
    n = struct.unpack_from('<I', orig, 4)[0]
    assert n == len(files)
    first = struct.unpack_from('<I', orig, 8)[0]
    lo, ls = struct.unpack_from('<II', orig, first - 8)
    out = bytearray(orig[:first])
    al = lambda x: (x + 0x7FF) & ~0x7FF
    for i, (nm, data) in enumerate(files):
        off = len(out)
        struct.pack_into('<II', out, 8 + i*8, off, len(data))
        out += data; out += b'\0' * (al(len(out)) - len(out))
    lst = bytearray(orig[lo:lo+ls])
    for i, (nm, data) in enumerate(files):
        struct.pack_into('<I', lst, i*48 + 44, len(data))
    lpos = len(out)
    struct.pack_into('<II', out, first - 8, lpos, ls)
    out += lst; out += b'\0' * (al(len(out)) - len(out))
    return bytes(out)
