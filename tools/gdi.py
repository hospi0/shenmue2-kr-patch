# -*- coding: utf-8 -*-
"""쉔무 II(일판 4장) GD-ROM cue/bin 판독 유틸 — 읽기 전용. (2026-11-04 쉔무 1 tools/gdi.py 에서 옮김, 트랙 시작 LBA 는 섹터 헤더 MSF 로 자동 실측)
(2026-11-03 건버드 2 tools/gdi.py 를 쉔무용으로 옮기고 트랙 시작 LBA 를 섹터 헤더 MSF 로 자동 실측하게 바꿈)
1장 실측: t1 LBA0 · t3 LBA45000 · t6 파일0=LBA159971, 데이터 LBA160046(앞 75섹 pregap)."""
import os, glob

SEC, HDR, USER = 2352, 16, 2048
ROMS = r"C:\claude\roms\dc"
def disc_dir(n):
    return os.path.join(ROMS, "Shenmue II (Japan) (Disc %d)" % n)

def _bcd(b): return (b >> 4) * 10 + (b & 15)
SYNC = b'\x00' + b'\xff' * 10 + b'\x00'

class Track:
    def __init__(self, path, num):
        self.num, self.path = num, path
        self.f = open(path, 'rb')
        n = os.path.getsize(path) // SEC
        self.start_lba = None
        for i in range(min(n, 400)):
            self.f.seek(i * SEC); r = self.f.read(16)
            if r[:12] == SYNC and r[15] in (1, 2):
                self.skip = i
                self.start_lba = _bcd(r[12]) * 4500 + _bcd(r[13]) * 75 + _bcd(r[14]) - 150
                break
        if self.start_lba is not None:
            self.sectors = n - self.skip
    def user(self, lba, count=1):
        self.f.seek((lba - self.start_lba + self.skip) * SEC)
        d = self.f.read(count * SEC)
        return b''.join(d[i*SEC+HDR:i*SEC+HDR+USER] for i in range(count))
    def contains(self, lba):
        return self.start_lba <= lba < self.start_lba + self.sectors

class Disc:
    def __init__(self, n=1):
        self.n = n
        paths = sorted(glob.glob(os.path.join(disc_dir(n), "*(Track *).bin")),
                       key=lambda p: int(p.rsplit('Track ', 1)[1].split(')')[0]))
        self.tracks = []
        for p in paths:
            t = Track(p, int(p.rsplit('Track ', 1)[1].split(')')[0]))
            if t.start_lba is not None: self.tracks.append(t)
    def track_of(self, lba):
        for t in self.tracks:
            if t.contains(lba): return t
        raise KeyError("LBA %d 는 어떤 데이터 트랙에도 없다" % lba)
    def read(self, lba, nbytes):
        t = self.track_of(lba)
        n = (nbytes + USER - 1) // USER
        if n > t.start_lba + t.sectors - lba:
            raise ValueError("LBA %d 에서 %d 섹터 요청, 트랙%d 넘침" % (lba, n, t.num))
        return t.user(lba, n)[:nbytes]
