# -*- coding: utf-8 -*-
"""1ST_READ.BIN 문자열 빌더 — 번역(exe:<오프셋>) 을 넣어 work/build/1ST_READ.BIN 을 만든다(디스크 쓰기 없음).

자리 규칙
  · 원문 자리 = [시작, 시작+원문길이+1(NUL)). ★정렬 패딩은 예산에 넣지 않는다(메모리 규칙: 원문 길이 예산).
  · 번역이 원문 길이 이하 → 제자리(남는 꼬리는 0 으로 지우고 «빈 자리 풀»에 넣음).
  · 번역이 같은 문자열이 여럿(히라가나판·가타카나 읽기가 한글로 같아짐) → 첫 것만 두고 나머지 포인터를 그쪽으로, 나머지 자리는 풀로.
  · 원문보다 긴 번역 → 풀에서 맞는 자리로 옮기고 그 문자열을 가리키던 포인터(0x0C010000+오프셋 워드) 전부 바꿈.
    옮긴 목록은 report 에 따로 — 게임이 «원문 길이 버퍼»로 복사하는 곳이면 넘칠 수 있어 실기 확인 대상.
  · 안쪽을 다른 포인터가 가리키는 문자열(3개: 三日月蹴り（みかづきげり） 등)은 옮기지 않고 안쪽 시작 전까지만.
토큰 규칙(어기면 빌드 중단)
  · 원문의 ASCII 덩어리(제어: A/B 머리, 0 줄, 00 빈 줄, G/S/D/C… 서식, 0x 메모 제어)는 «순서까지 그대로».
  · 단 메모장 사전 코드([1-9A-I][0-9] 쌍, 짝수 위치)는 번역에서 풀어 써도 된다(뺄 수만 있음).
  · 「　　」(버튼 그림 자리 전각 공백 두 칸) 개수 유지.

  python tools/build_exe.py <번역 TSV 들…>     (TSV 열: key … ko 마지막 열, 머리줄 key)
"""
import os, sys, re, struct, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import exe_strings
from encode import encode, normalize, to_wide

BASE = 0x8C010000
SRC = os.path.join(ROOT, 'work', 'disc1', '1ST_READ.BIN')
OUT = os.path.join(ROOT, 'work', 'build')
TAIL_END = 0x360000 - 0x10000 - 0x100   # 힙 시작 0x8C360000(0x8C05191A 함수가 설정) 의 파일 오프셋 − 여유 256 B
MEMO_REF = (0x242900, 0x244400)            # II: 메모 줄 포인터가 있는 구역(문자열은 흩어져 있음) — 해독 루틴 0x8C0D6500
DICT_PAIR = re.compile(r'[1-9A-I][0-9]')

def ascii_runs(s):
    return re.findall(r'[\x20-\x7e]+', s)

def memo_tokens(s):
    """메모 문장: 2글자 단위로 읽어 «사전 코드 아닌» ASCII 쌍만 (0x 제어 등)"""
    out = []
    for run in ascii_runs(s):
        for i in range(0, len(run) - 1, 2):
            p = run[i:i+2]
            if not DICT_PAIR.fullmatch(p): out.append(p)
        if len(run) % 2: out.append(run[-1])
    return out

WAZA_REF = (0x24D5DC, 0x24E5FC)           # II: 권법 기술 표(포인터 구역). 설명의 2자리 숫자 = 사전 0x25332C(105낱말) — 풀어 써도 됨

def _pairs(s):
    return [r[i:i+2] for r in ascii_runs(s) for i in range(0, len(r) - 1, 2)] + [r[-1] for r in ascii_runs(s) if len(r) % 2]

def _subseq(small, big):
    it = iter(big); return all(x in it for x in small)

# 전각 공백이 «버튼 그림 자리»가 아니라 «：» 줄 맞춤인 표(손으로 맞춤 — merge_tr.LINE_EDITS)
ALIGN_TABLES = set()

_SAVE_JP = None
SAVE_MACRO = 0x252948      # II 저장 안내 표(34개)
def save_expand(s, depth=0):
    """저장 안내 사전 원문의 매크로(A~z, 포인터 표 0x2932F8) 펼치기 — H(예/아니오 상자)·9X 코드는 그대로"""
    global _SAVE_JP
    if _SAVE_JP is None:
        d = open(SRC, 'rb').read(); _SAVE_JP = {}
        for k in range(34):
            v = struct.unpack_from('<I', d, SAVE_MACRO + 4 * k)[0] - BASE
            _SAVE_JP[chr(65 + k) if k < 26 else chr(97 + k - 26)] = d[v:d.find(b'\0', v)].decode('euc_jp')
    if depth > 5: return s
    return re.sub(r'(?<!9)[A-GI-Za-z]', lambda m: save_expand(_SAVE_JP[m.group()], depth + 1), s)

MEMO_SET = set(); WAZA_SET = set(); SAVE_SET = set()

def check_tokens(off, jp, ko):
    if off in MEMO_SET:
        a, b = memo_tokens(jp), memo_tokens(ko)
    elif off in WAZA_SET or 0x226840 <= off < 0x228000:   # 기술 설명 구역 — 사전 코드 풀어 써도 됨(work/text/waza_desc.tsv)
        a, b = _pairs(jp.replace('#', '')), _pairs(ko.replace('#', ''))
        if not _subseq(b, a) or any(not x.isdigit() or len(x) != 2 for x in b):
            return '사전 코드 다름(원문 코드에서 빼기만 가능): 원문 %r / 번역 %r' % (a, b)
        a = b
    elif off in SAVE_SET:
        # 저장 안내 사전: 번역은 매크로를 펼친 완성 문장(H 예/아니오 상자·9X 코드만 남김) → 원문도 펼친 뒤 숫자·코드 순서 비교
        if re.search(r'(?<!9)[A-GI-Za-z]', ko): return '저장 안내: H 말고 매크로 글자가 남음 %r' % ko
        a = [r.replace('0', '') for r in ascii_runs(save_expand(jp)) if r.replace('0', '')]
        b = [r.replace('0', '') for r in ascii_runs(ko) if r.replace('0', '')]
    else:
        # 설명 글의 줄바꿈 0 은 번역 길이에 맞춰 다시 접을 수 있다 — 0 을 뺀 서식 토큰(A/B/K/E/M/O/C…)만 순서까지 같게
        a = [r.replace('0', '') for r in ascii_runs(jp) if r.replace('0', '')]
        b = [r.replace('0', '') for r in ascii_runs(ko) if r.replace('0', '')]
    if a != b: return '제어 토큰 다름: 원문 %r / 번역 %r' % (a, b)
    nrun = lambda s: len(re.findall('　{2,}', s))          # 아이콘 칸 맞춤(merge_tr.align_icons)으로 공백 줄이 길어질 수 있어 «줄» 개수로
    if off not in ALIGN_TABLES and ko.strip('　') and nrun(jp) != nrun(ko): return '버튼 자리(전각 공백 두 칸) 개수 다름'
    return None

def prep(jp, ko):
    """원문에 반각 기호·공백이 없으면, 번역의 반각 기호·공백은 글자(전각)로 본다 — 영숫자만 제어 토큰."""
    # 번역문의 반각 부호·공백은 글자(전각) — 원문 제어 토큰에 없는 글자만. 원문 영문 줄의 세 칸 공백은 유지
    jt = ''.join(ascii_runs(jp))
    ko = re.sub(r'(?<! )(?<=[^\x20-\x7e]) (?! )|(?<! ) (?=[가-힣])(?<! )', '　', ko)
    ko = re.sub(r'(?<![ ]) (?=[^\x20-\x7e])', '　', ko)
    for ch in '.,!?:;()~/-':
        if ch not in jt: ko = ko.replace(ch, to_wide(ch))
    if ' ' not in jt: ko = ko.replace(' ', '　')
    ko = re.sub('소켓[ 　]?1', '소켓　１', ko)
    if jp.startswith('　　') and not ko.startswith('　　'): ko = '　' + ko     # 앞 두 칸 = 체크 표시 자리
    if re.search(r'[ -/:-@[-`{-~]', jp): return ko
    return re.sub(r'[ -"$-/:-@[-`{-~]', lambda m: to_wide(m.group()), ko)   # # 는 기술 설명 줄바꿈 제어 — 전각으로 바꾸면 글자로 찍힌다

def enc_mixed(s):
    """ASCII 제어 토큰은 1바이트 그대로, 나머지는 encode()(한글 EUC-KR·기호 EUC-JP 전각). 「＼ｔ」 = 탭 0x09(extract2 표기)."""
    out = bytearray()
    for part in re.split(r'([\x09\x20-\x7e]+)', normalize(s.replace('＼ｔ', '\t'))):
        if not part: continue
        out += part.encode('ascii') if re.fullmatch(r'[\x09\x20-\x7e]+', part) else encode(part)
    return bytes(out)

def load_tr(paths):
    tr = {}
    for p in paths:
        for i, ln in enumerate(open(p, encoding='utf-8')):
            c = ln.rstrip('\n').split('\t')
            if i == 0 and c[0] == 'key': continue
            if c[0].startswith('exe:') and c[-1]:   # ★전각 공백만 있는 줄도 번역(비움) — .strip() 으로 거르면 일본어로 남는다
                tr[int(c[0][4:], 16)] = c[-1].replace('\\n', '\n')
    return tr

ITEM_TABLES = ((0x23E02C, 23), (0x23E20C, 33), (0x23E658, 279), (0x23FD14, 26))   # II 20 B 행: …·+12 이름 18 B
def field_limits(d):
    """★표에 묶인 문자열은 게임이 고정 버퍼로 복사한다 — 아이템 이름에 126 B 를 넣었더니 메뉴 여는 순간 멈춤(2026-11-03 2차 시험).
    한도 = 그 칸 원문 최대 길이(이름 18 B · 읽기 30 B)."""
    lim = {}
    for t, n in ITEM_TABLES:
        for a in range(t, t + 20 * n, 20):
            v = struct.unpack_from('<I', d, a + 12)[0]
            if BASE <= v < BASE + len(d): lim[v - BASE] = 18
    return lim

# ★«순서·이웃 간격»을 게임이 쓰는 포인터 표 — 하나라도 길어지면 표 전체를 원래 순서대로 덧붙임 구역에 이어 붙인다.
#   헬프 표(145개, 문자열이 주소 순서로 빈틈없이 이어짐): 【メモ帳】 하나만 파일 끝으로 옮겼더니 헬프가 통째로 안 뜸(4차 시험) —
#   «길이 = 다음 포인터 − 이 포인터» 로 쓰는 것으로 추정.
ORDERED_TABLES = [(0x2368CC, 0x2368CC + 20 * 4), (0x23DC8C, 0x23DC8C + 212 * 4)]   # II 도움말 표(빈 칸·다른 글은 ordered() 가 거름)
HELP_LO, HELP_HI = 0x213000, 0x21D000
def ordered(d, a, b):
    """표 칸 중 도움말 문자열을 가리키는 것만 [(칸 위치, 문자열 위치)]"""
    out = []
    for p in range(a, b, 4):
        o = struct.unpack_from('<I', d, p)[0] - BASE
        if HELP_LO <= o < HELP_HI: out.append((p, o))
    return out
MEMO_FRAME_PATCH = []     # II 는 메모 줄 버퍼가 32 B 라 스택 패치 불필요(0x8C0D5ACE 실측)
SETTING_LABELS = (0x23B2A8, 0x23B2A8 + 18 * 8)     # II 설정 메뉴 (포인터, 폭) 쌍 — 폭×4 B 넘으면 크래시(1편 실기)
SETTING_DESC = (0, 0)

HELP_SHORT = [tuple(l.rstrip('\n').split('\t')) for l in open(os.path.join(ROOT, 'work', 'text', 'help_short.tsv'), encoding='utf-8') if '\t' in l]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    paths = [q for p in sys.argv[1:] for q in glob.glob(p)]
    tr = load_tr(paths)
    d = bytearray(open(SRC, 'rb').read())
    rows = exe_strings.main(SRC, os.path.join(ROOT, 'work', 'exe_strings.tsv'))
    info = {t: (refs, ln, room, s) for t, refs, ln, s, room in rows}
    for t, (refs, ln, room, s) in info.items():
        if any(MEMO_REF[0] <= r < MEMO_REF[1] for r in refs): MEMO_SET.add(t)
        if any(WAZA_REF[0] <= r < WAZA_REF[1] for r in refs): WAZA_SET.add(t)
        pass   # II 저장 안내는 매크로 없이 일반 토큰 비교
    errs = []; new = {}
    lim = field_limits(d)
    help_set = {o for a, b in ORDERED_TABLES for p, o in ordered(d, a, b)}
    desc_set = {struct.unpack_from('<I', d, p)[0] - BASE for p in range(SETTING_DESC[0], SETTING_DESC[1], 4)}
    for off, ko in list(tr.items()):
        if off in help_set:                                  # 도움말 줄 버퍼 — 긴 문장은 work/text/help_short.tsv 대로 줄임
            for x_, y_ in HELP_SHORT: ko = ko.replace(x_, y_)
        if off in info: ko = tr[off] = prep(info[off][3], ko)   # 원문에 반각 기호 없으면 번역의 반각 기호·공백 → 전각
        if off not in info:
            # 처음 추출 때 «코드 안 우연한 값»을 포인터로 보고 뽑힌 가짜 문자열(25E2FF·270724) — 번역 TSV 에 남아 있어도 건너뜀
            print('경고: %06X 는 실제 포인터가 없는 문자열이라 건너뜀' % off); continue
        e = check_tokens(off, info[off][3], ko)
        if e: errs.append('%06X %s' % (off, e)); continue
        try: new[off] = enc_mixed(ko)
        except ValueError as x: errs.append('%06X %s' % (off, x)); continue
        if off in help_set:
            # 헬프 그리기(0x0C0E2514): 0 마다 조각 하나를 52 B 줄 버퍼(0x0C2153C4, 바로 뒤 쓰기 포인터)에 모아 그림.
            #   조각 i = 줄 i//2 · 칸 (i%2)×19 격자, 조각 배열 20칸(매크로 펼친 합계), 버튼 안내·아이콘은 원문 격자에 고정
            #   → 조각 수(0 개수)는 원문과 같게 · 한 조각 ≤ 50 B (2026-11-04 기술 화면 겹침·넘침)
            jz, kz = info[off][3].count('0'), new[off].count(b'0')
            if jz != kz: errs.append('%06X 헬프 조각 수(0) %d ≠ 원문 %d: %s' % (off, kz, jz, ko))
            for seg in re.split(rb'[0A-Z]', new[off]):                 # 대문자 = 매크로(도움말 표 문자열 끼움, 대개 0 으로 시작·끝)
                n = len(re.sub(rb'[A-Za-z]', b'', seg))
                if n > 50: errs.append('%06X 헬프 한 조각 %d B > 50 B(줄 버퍼 52 B): %s' % (off, n, seg.decode('euc_jp', 'replace')))
        if off in desc_set and len(new[off]) > 38:
            errs.append('%06X 설정 설명 줄 %d B > 38 B: %s' % (off, len(new[off]), ko))
        if off in lim and len(new[off]) > lim[off]:
            errs.append('%06X 아이템 칸 한도 %d B 초과(%d B): %s' % (off, lim[off], len(new[off]), ko))
    if errs:
        print('\n'.join(errs[:50])); raise SystemExit('토큰·글자 오류 %d건 — 빌드 중단' % len(errs))
    orig = bytes(d)
    # 0) 순서 표: 길어진 문자열이 있으면 표 전체를 통째로 옮길 대상으로
    group_move = []
    for a, b in ORDERED_TABLES:
        mem = sorted({o for p, o in ordered(d, a, b)}, key=lambda o: o)
        if any(o in new and len(new[o]) > info[o][1] for o in mem) and mem not in group_move: group_move.append(mem)
    in_group = {o for g in group_move for o in g}
    # 1) 같은 번역끼리 합치기
    first = {}; alias = {}
    for off in sorted(o for o in new if o not in in_group):
        if new[off] in first and info[off][2] >= info[off][1] + 1: alias[off] = first[new[off]]
        else: first.setdefault(new[off], off)
    # 2) 빈 자리 풀
    free = []
    def give(a, b):
        if b > a: d[a:b] = b'\0' * (b - a); free.append([a, b])
    placed = {}; moved = []
    slen = lambda o: info[o][1] if o in info else orig.index(0, o) - o     # 표 안 1글자 문자열(「0」)은 목록에 없음
    for g in group_move:
        for off in g: give(off, off + slen(off) + 1)
    for off, b in new.items():
        if off in in_group: continue
        refs, ln, room, s = info[off]
        inner = room < ln + 1
        if off in alias: give(off, off + ln + 1); continue
        if len(b) <= ln or (inner and len(b) <= room - 1):
            d[off:off+len(b)] = b; d[off+len(b)] = 0
            give(off + len(b) + 1, off + ln + 1); placed[off] = off
        elif inner:
            errs.append('%06X 안쪽 참조가 있어 옮길 수 없는데 %d B > %d B' % (off, len(b), room - 1))
        else:
            give(off, off + ln + 1); moved.append(off)
    if errs: print('\n'.join(errs)); raise SystemExit('빌드 중단')
    # 풀 합치기
    free.sort(); merged = []
    for a, b in free:
        if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    # 파일 끝 뒤 덧붙임 자리: RAM 0x0C2A5964(파일 끝)~0x0C2CA000(malloc 힙 시작) 149 KB —
    #   가리키는 리터럴·포인터 0, 스테이트 22장 전부 0 → 안 쓰는 자리로 판정(2026-11-03 정적, 시험 빌드에서 재확인)
    tail0 = (len(d) + 3) & ~3
    tail = [tail0, TAIL_END]
    for g in group_move:                       # 표 통째로: 원래 순서, 각 시작 4 정렬(원본도 0~3 B 패딩)
        for off in g:
            b = new.get(off, orig[off:off + slen(off)])
            at = (tail[0] + 3) & ~3; need = at - tail[0] + len(b) + 1
            if tail[1] - tail[0] < need: raise SystemExit('덧붙임 구역 부족(순서 표)')
            if len(d) < at + len(b) + 1: d.extend(bytes(1) * (at + len(b) + 1 - len(d)))
            d[at:at+len(b)] = b; d[at+len(b)] = 0; tail[0] = at + len(b) + 1; placed[off] = at
    for off in sorted(moved, key=lambda o: -len(new[o])):
        b = new[off]; need = len(b) + 1
        slot = next((m for m in merged if m[1] - m[0] >= need), None) or (tail if tail[1] - tail[0] >= need else None)
        if slot is tail and len(d) < tail[0] + need: d.extend(bytes(1) * (tail[0] + need - len(d)))
        if slot is None: raise SystemExit('빈 자리 부족: %06X %d B (풀 최대 %d B)' % (off, need, max((m[1]-m[0] for m in merged), default=0)))
        at = slot[0]; d[at:at+len(b)] = b; d[at+len(b)] = 0; slot[0] += need; placed[off] = at
    for off, to in alias.items(): placed[off] = placed.get(to, to)
    # 3) 포인터 고치기
    nptr = 0
    grp_refs = collections.defaultdict(list)
    for a, b in ORDERED_TABLES:
        for p, o in ordered(orig, a, b): grp_refs[o].append(p)
    for off, at in placed.items():
        if at == off: continue
        for r in sorted(set(info[off][0] if off in info else []) | set(grp_refs.get(off, []))):
            assert struct.unpack_from('<I', d, r)[0] == BASE + off
            struct.pack_into('<I', d, r, BASE + at); nptr += 1
    # 3b) 메모장 줄 다시 나누기(tools/memo_reflow.py → work/build/memo_layout.tsv): 표 자리마다 새 줄을 빈 자리에 놓고 포인터를 바꾼다.
    #     해독 루틴이 한 줄을 24 B 스택 버퍼로 sprintf → 23 B 넘는 줄은 크래시(2026-11-04 실기).
    lay_p = os.path.join(OUT, 'memo_layout.tsv'); nmemo = 0
    if os.path.exists(lay_p):
        put_at = {}
        for ln in open(lay_p, encoding='utf-8').read().splitlines()[1:]:
            slot, txt = ln.split('\t', 1); slot = int(slot, 16)
            if not txt: struct.pack_into('<I', d, slot, 0); continue
            b = enc_mixed(txt)
            if len(b) > 22: raise SystemExit('메모 줄 %06X %d B > 22 B: %s' % (slot, len(b), txt))
            if b not in put_at:
                need = len(b) + 1
                sl = next((m for m in merged if m[1] - m[0] >= need), None) or (tail if tail[1] - tail[0] >= need else None)
                if sl is None: raise SystemExit('메모 줄 놓을 자리 부족')
                if sl is tail and len(d) < tail[0] + need: d.extend(bytes(tail[0] + need - len(d)))
                at = sl[0]; d[at:at + len(b)] = b; d[at + len(b)] = 0; sl[0] += need; put_at[b] = at
            struct.pack_into('<I', d, slot, BASE + put_at[b]); nmemo += 1
        print('메모장 줄 다시 나누기: 표 자리 %d · 새 문자열 %d' % (nmemo, len(put_at)))
        # 줄마다 사건 플래그(쪽 기록표) — 빈 칸을 빌린 줄은 그 묶음 플래그로(memo_reflow → memo_flags.tsv)
        fp = os.path.join(OUT, 'memo_flags.tsv'); nfl = 0
        if os.path.exists(fp):
            for ln in open(fp, encoding='utf-8').read().splitlines()[1:]:
                a_, f_ = ln.split('\t'); struct.pack_into('<H', d, int(a_, 16), int(f_, 16)); nfl += 1
        print('메모장 줄 플래그 바꿈 %d' % nfl)
    # 4) 설정 메뉴 글자표(포인터, 폭) — 폭 n(1·2·4) × 4 B 가 글자판 크기. 「声と字幕」(n=2, 8 B)에 «음성과 자막» 12 B 를 넣었더니
    #    침대 메뉴 «설정» 들어가는 순간 멈춤(2026-11-04 실기). 번역 바이트에 맞게 n 을 올린다(게임이 이미 쓰는 값 1·2·4 안에서).
    for p in range(SETTING_LABELS[0], SETTING_LABELS[1], 8):
        off = struct.unpack_from('<I', orig, p)[0] - BASE; n = struct.unpack_from('<I', orig, p + 4)[0]
        if off not in new: continue
        need = (len(new[off]) + 3) // 4
        if need > n:
            nn = next((v for v in (1, 2, 4) if v >= need), None)
            if nn is None: raise SystemExit('설정 메뉴 낱말 %06X %d B > 16 B' % (off, len(new[off])))
            struct.pack_into('<I', d, p + 4, nn); print('설정 메뉴 폭 %06X: %d → %d (%d B)' % (off, n, nn, len(new[off])))
    # 5) 메모장 쪽 그리기 함수(0x0C0F46C8) 스택 틀 108 → 124 B: 펼친 줄 버퍼 SP+0x58 이 20 B(바로 뒤 복귀 주소)라
    #    한글 줄(10칸 = 20 B + 끝 0)이 복귀 주소를 덮어 크래시(2026-11-04 실기 2회). 틀만 넓히면 버퍼 36 B.
    for off, old, new_ in MEMO_FRAME_PATCH:
        assert d[off:off + 2] == old, '메모 틀 패치 자리 원본 아님 %06X' % off
        d[off:off + 2] = new_
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, '1ST_READ.BIN'), 'wb').write(d)
    with open(os.path.join(OUT, 'exe_report.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('kind\toff\tnew_at\tjp_len\tko_len\tjp\n')
        for off in sorted(moved): w.write('moved\t%06X\t%06X\t%d\t%d\t%s\n' % (off, placed[off], info[off][1], len(new[off]), info[off][3]))
        for g in group_move:
            for off in g: w.write('group\t%06X\t%06X\t%d\t%d\t%s\n' % (off, placed[off], slen(off), len(new.get(off, b'')), info[off][3] if off in info else orig[off:off + slen(off)].decode('euc_jp', 'replace')))
        for off in sorted(alias): w.write('alias\t%06X\t%06X\t%d\t%d\t%s\n' % (off, placed[off], info[off][1], len(new[off]), info[off][3]))
    left = sum(m[1] - m[0] for m in merged)
    if len(d) % 4: d.extend(bytes(1) * (4 - len(d) % 4))
    open(os.path.join(OUT, '1ST_READ.BIN'), 'wb').write(d)
    print('번역 %d · 제자리 %d · 옮김 %d · 합침 %d · 포인터 %d곳 · 남은 빈 자리 %d B · 덧붙임 %d B (한도 %d B)' %
          (len(new), len(new) - len(moved) - len(alias), len(moved), len(alias), nptr, left, max(0, tail[0] - tail0), TAIL_END - tail0))

if __name__ == '__main__':
    main()
