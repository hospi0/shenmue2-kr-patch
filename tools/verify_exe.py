# -*- coding: utf-8 -*-
"""build_exe 결과 검산: ① 모든 문자열 포인터가 넣은 번역 바이트를 가리킴 ② 원본 대비 바뀐 바이트가 «문자열 자리·포인터 워드·덧붙임» 밖에 없음."""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import exe_strings, build_exe
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = os.path.join(ROOT, 'work', 'disc1', '1ST_READ.BIN'); o = open(src, 'rb').read()
    n = open(os.path.join(ROOT, 'work', 'build', '1ST_READ.BIN'), 'rb').read()
    rows = exe_strings.main(src, os.path.join(ROOT, 'work', 'exe_strings.tsv'))
    import glob as _g
    tr = build_exe.load_tr([q for p_ in sys.argv[1:] for q in _g.glob(p_)])
    for k_ in tr:
        for x_, y_ in build_exe.HELP_SHORT: tr[k_] = tr[k_].replace(x_, y_)
    allowed = bytearray(len(o)); bad = 0; checked = 0
    lay = {}
    lp = os.path.join(ROOT, 'work', 'build', 'memo_layout.tsv')
    if os.path.exists(lp):                                   # 메모장 줄 다시 나누기 자리: 표 포인터 → 새 줄 글
        for ln in open(lp, encoding='utf-8').read().splitlines()[1:]:
            sl, txt = ln.split('	', 1); lay[int(sl, 16)] = txt
    for sl, txt in lay.items():
        for i in range(sl, sl + 4): allowed[i] = 1
        p = struct.unpack_from('<I', n, sl)[0]
        if not txt:
            if p: bad += 1; print('메모 자리 %06X 비어야 함' % sl)
        elif n[p - build_exe.BASE:n.index(b'\0', p - build_exe.BASE)] != build_exe.enc_mixed(txt): bad += 1; print('메모 자리 %06X 내용 다름' % sl)
        checked += 1
    for p in range(build_exe.SETTING_LABELS[0], build_exe.SETTING_LABELS[1], 8):   # 설정 메뉴 폭 워드
        for i in range(p + 4, p + 8): allowed[i] = 1
    for t, refs, ln, s, room in rows:
        for i in range(t, t + ln + 1): allowed[i] = 1
        for r in refs:
            for i in range(r, r + 4): allowed[i] = 1
        want = build_exe.enc_mixed(build_exe.prep(s, tr[t])) if t in tr else o[t:t+ln]
        for r in refs:
            if r in lay: continue
            p = struct.unpack_from('<I', n, r)[0] - build_exe.BASE
            got = n[p:n.index(b'\0', p)]
            checked += 1
            if got != want: bad += 1; print('포인터 %06X → %06X 내용 다름' % (r, p)) if bad < 10 else None
    # 순서 표(헬프): 표 칸 자체와, 목록에 없는 1글자 문자열(「0」) 자리도 허용 + 표 포인터가 원래 순서·원래 내용(번역 빼고)인지
    for a, b in build_exe.ORDERED_TABLES:
        for p, ov in build_exe.ordered(o, a, b):
            for i in range(p, p + 4): allowed[i] = 1
            nv = struct.unpack_from('<I', n, p)[0] - build_exe.BASE
            for i in range(ov, o.index(0, ov) + 1): allowed[i] = 1
            want = build_exe.enc_mixed(build_exe.prep(o[ov:o.index(0, ov)].decode('euc_jp', 'replace'), tr[ov])) if ov in tr else o[ov:o.index(0, ov)]
            if n[nv:n.index(0, nv)] != want: bad += 1; print('순서 표 %06X 내용 다름' % p)
    fp = os.path.join(ROOT, 'work', 'build', 'memo_flags.tsv')         # 메모 줄 플래그 바꾼 자리
    if os.path.exists(fp):
        for ln in open(fp, encoding='utf-8').read().splitlines()[1:]:
            a_ = int(ln.split('	')[0], 16); allowed[a_] = allowed[a_ + 1] = 1
    for off, _, _ in build_exe.MEMO_FRAME_PATCH:              # 메모장 쪽 함수 스택 틀 넓힘
        for i in range(off, off + 2): allowed[i] = 1
    outside = [i for i in range(len(o)) if o[i] != n[i] and not allowed[i]]
    print('포인터 검사 %d / 불일치 %d · 허용 밖 바뀐 바이트 %d · 크기 %d → %d' % (checked, bad, len(outside), len(o), len(n)))
    if outside: print([hex(x) for x in outside[:20]])
    mbad = []
    if bad or outside or mbad: raise SystemExit('검산 실패 — 빌드 중단')
main()
