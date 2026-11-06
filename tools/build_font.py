# -*- coding: utf-8 -*-
"""쉔무 한글 글꼴 생성 — DC_KANJI.FON(7806칸 × 45B, 24×15 1bpp, 행 3B LSB=x0) 에 한글을 그린다.

칸 배치(코드 수정 없음):
  · KS X 1001 한글 2,350자 = EUC-KR 바이트 그대로 = JIS 16~40구 칸 (구·점이 같은 94×94 판)
  · 완성형 밖 음절 = 41구 1점부터 차례로 (extra 표 → work/font/extra_map.tsv, 인코더가 씀)
  · 1~15구(기호·영숫자·가나)는 그대로 — 단 «…»(1구 36점) 은 한국식 바닥선 점 셋으로 다시 그림
글씨: 갈무리14 비트맵을 가로 1.6배(최근접)로 늘려 24×15 칸 가운데에 (원본은 24×24 디자인을 15행으로 누른 모양)

  python tools/build_font.py [--extra 뷁쀍…]   → work/font/DC_KANJI.FON, extra_map.tsv, preview.png
디스크에는 쓰지 않는다.
"""
import os, sys, argparse
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from bdf import Font

SRC = os.path.join(ROOT, 'work', 'disc1', 'MISC', 'DC_KANJI.FON')
OUT = os.path.join(ROOT, 'work', 'font')
GAL = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
GW, GH, GB = 24, 15, 45
GAL_TOP = 4              # 갈무리14 draw() 에서 한글 잉크 첫 행(실측 4..17)
EXTRA_ROW0 = 41          # 완성형 밖 음절 시작 구
EXTRA_LAST_ROW = 84      # 7806칸 = 83구 + 4칸 → 안전하게 83구까지만
ELLIPSIS = (1, 36)

def slot(ku, ten): return (ku - 1) * 94 + (ten - 1)

def put(buf, idx, img):
    for y in range(GH):
        v = 0
        for x in range(GW):
            if img.getpixel((x, y)): v |= 1 << x
        o = idx * GB + y * 3
        buf[o:o+3] = bytes((v & 255, v >> 8 & 255, v >> 16 & 255))

def get(buf, idx):
    im = Image.new('1', (GW, GH), 0)
    for y in range(GH):
        o = idx * GB + y * 3; v = buf[o] | buf[o+1] << 8 | buf[o+2] << 16
        for x in range(GW):
            if v >> x & 1: im.putpixel((x, y), 1)
    return im

_gal = None
def glyph(ch):
    """갈무리14 → 가로 1.6배 최근접 → 24×15 가운데. 세로 위치는 «글꼴 기준선» 그대로(잉크로 자르지 않음)."""
    global _gal
    _gal = _gal or Font(GAL)
    pts, adv = _gal.draw(ch, 0, 0)
    im = Image.new('1', (GW, GH), 0)
    if not pts: return im
    xs = [p[0] for p in pts]; x0 = min(xs); w = max(xs) - x0 + 1
    src = Image.new('1', (w, GH), 0)
    for x, y in pts:
        yy = y - GAL_TOP                        # 갈무리14 한글 잉크 = y 4..17 (14행) → 0..13
        if 0 <= yy < GH: src.putpixel((x - x0, yy), 1)
    W = min(GW, round(w * 1.6))
    g = src.resize((W, GH), Image.NEAREST)
    im.paste(g, ((GW - W) // 2, 0))
    return im

KANA_LABEL = '파워스피드빈틈'   # 기술 화면 왼쪽 라벨: 게임이 2바이트 글자의 뒤 바이트를 DC_KANA 칸으로 찍는다 → 그 칸에 한글을 그린다(뒤 바이트 7개 전부 다름)
def kana_font(k):
    """DC_KANA(256칸 × 16비트 15행, u16 LE, ★왼쪽 = 최하위 비트 — 실기로 확인) 라벨 칸 덮기. 원본 가나 잉크 = 비트 0..11, 행 0..13 → 갈무리11(폭 12) 을 그 안에"""
    from encode import encode
    f = Font(GAL.replace('Galmuri14', 'Galmuri11'))
    b = bytearray(k); seen = set()
    for ch in KANA_LABEL:
        code = encode(ch)[1]; assert code not in seen; seen.add(code)
        pts, adv = f.draw(ch, 0, 0); x0 = min(p[0] for p in pts); w = max(p[0] for p in pts) - x0 + 1
        y0 = min(p[1] for p in pts); h = max(p[1] for p in pts) - y0 + 1; assert w <= 12 and h <= 14, (ch, w, h)
        rows = [0] * 15; oy = (14 - h) // 2
        for x, y in pts: rows[oy + y - y0] |= 1 << ((12 - w) // 2 + x - x0)
        for r, v in enumerate(rows): b[code * 30 + r * 2:code * 30 + r * 2 + 2] = v.to_bytes(2, 'little')
    return bytes(b)

def ellipsis():
    im = Image.new('1', (GW, GH), 0)
    for cx in (4, 11, 18):                      # 바닥선 점 셋(2×2)
        for dx in (0, 1):
            for dy in (0, 1): im.putpixel((cx + dx, 12 + dy), 1)
    return im

def ks_syllables():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try: out.append(((hi, lo), bytes((hi, lo)).decode('euc_kr')))
            except UnicodeDecodeError: pass
    return out

HAND_TTF = r'C:\claude\utils\font\poorstory\PoorStory-Regular.ttf'   # 메모장 손글씨(하스피 «적당한 거 골라» → 푸어스토리, 2026-11-03)
_hand = None
def hand_glyph(ch, thr=70):
    """TTF 를 크게 그려 «한글 높이 = 15행»으로 맞추고 가로는 같은 배율(24/높이)로 줄여 칸 가운데에."""
    from PIL import ImageDraw, ImageFont
    global _hand
    _hand = _hand or ImageFont.truetype(HAND_TTF, 96)
    big = Image.new('L', (160, 160), 0); dr = ImageDraw.Draw(big)
    ref = dr.textbbox((0, 0), '갉뷁', font=_hand)
    dr.text((20 - ref[0], 20 - ref[1]), ch, font=_hand, fill=255)
    rh = ref[3] - ref[1]; cb = big.getbbox() or (0, 0, 1, 1)
    w = max(1, min(GW, round((cb[2] - cb[0]) * GW / rh)))
    sm = big.crop((cb[0], 20, cb[2], 20 + rh)).resize((w, GH), Image.BOX).point(lambda v: 1 if v >= thr else 0, '1')
    im = Image.new('1', (GW, GH), 0); im.paste(sm, ((GW - w) // 2, 0)); return im

# 출력 글꼴 → 한글 그리는 함수 — 기호·영숫자 칸은 각 원본 그대로
TARGETS = {'DC_KANJI.FON': glyph,       # 대사·메뉴 (갈무리14 ×1.6, 하스피 확정)
           'RYOU.FON': hand_glyph}      # 메모장 涼 손글씨 (II 에는 WAZA 없음)

def jis_slot(ch):
    """원본 글꼴에서 그 글자(EUC-JP) 칸 번호 — 한글이 덮은 한자를 «원본 그림 그대로» 옮겨 쓸 때"""
    b = ch.encode('euc_jp'); return slot(b[0] - 0xA0, b[1] - 0xA0)

def extra_slots(extra, avoid):
    """41구부터 차례로, 번역·원문에 실제로 쓰이는 글자 칸은 건너뜀"""
    out = []; k = 0
    while len(out) < len(extra):
        ku, ten = EXTRA_ROW0 + k // 94, 1 + k % 94; k += 1
        if ku >= EXTRA_LAST_ROW: raise SystemExit('extra 칸 모자람')
        try: c = bytes((ku + 0xA0, ten + 0xA0)).decode('euc_jp')
        except UnicodeDecodeError: c = None
        if c and c in avoid: continue
        out.append((ku, ten))
    return out

def build_one(name, draw, ks, extra, slots):
    src = os.path.join(ROOT, 'work', 'disc1', 'MISC', name)
    orig = open(src, 'rb').read()
    buf = bytearray(orig); assert len(buf) == 7806 * GB
    for (hi, lo), ch in ks:
        put(buf, slot(hi - 0xA0, lo - 0xA0), draw(ch))
    for ch, (ku, ten) in zip(extra, slots):
        if '가' <= ch <= '힣': put(buf, slot(ku, ten), draw(ch))
        else:                                     # 한자: 이 글꼴 원본 칸 그림 그대로 옮김
            i = jis_slot(ch); o = slot(ku, ten); buf[o * GB:(o + 1) * GB] = orig[i * GB:(i + 1) * GB]
    put(buf, slot(*ELLIPSIS), ellipsis())
    open(os.path.join(OUT, name), 'wb').write(buf)
    return buf

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--extra', default=''); ap.add_argument('--avoid', default='')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    ks = ks_syllables(); assert len(ks) == 2350, len(ks)
    ks_set = {c for _, c in ks}
    def need(c):
        if '가' <= c <= '힣': return c not in ks_set
        try: b = c.encode('euc_jp')
        except UnicodeEncodeError: return False
        return len(b) == 2 and 16 <= b[0] - 0xA0 <= 40          # 한글이 덮은 구의 한자
    extra = sorted({c for c in a.extra if need(c)})
    avoid = set(open(a.avoid, encoding='utf-8').read()) if a.avoid else set()
    slots = extra_slots(extra, avoid)
    rows = ['%s\t%02X%02X\n' % (ch, ku + 0xA0, ten + 0xA0) for ch, (ku, ten) in zip(extra, slots)]
    bufs = {n: build_one(n, f, ks, extra, slots) for n, f in TARGETS.items()}
    buf = bufs['DC_KANJI.FON']
    open(os.path.join(OUT, 'extra_map.tsv'), 'w', encoding='utf-8', newline='\n').write(''.join(rows))
    # 미리보기: 표본 문장을 게임 비율(세로 1.6배)과 1:1 로
    sample = ['료는 그 남자를 찾아 거리로 나섰다…', '아버지의 원수는 내가 갚는다!!', '쉔무 한글화 시험 문장입니다. 괜찮아?']
    def enc(ch):
        if ch in extra: return slot(*slots[extra.index(ch)])
        b = ch.encode('euc_kr') if '\uac00' <= ch <= '\ud7a3' else ch.encode('euc_jp')
        return slot(b[0] - 0xA0, b[1] - 0xA0) if len(b) == 2 else None
    W = max(len(s) for s in sample) * GW
    pv = Image.new('L', (W, len(sample) * 40), 30); y = 0
    for s in sample:
        for k, ch in enumerate(s):
            i = enc(ch.replace(' ', '\u3000')) if ch != ' ' else slot(1, 1)
            if i is None: continue
            g = get(buf, i).convert('L').point(lambda v: 235 if v else 30)
            pv.paste(g.resize((GW, 24), Image.NEAREST), (k * GW, y))
        y += 40
    pv.resize((pv.width * 2, pv.height * 2), Image.NEAREST).save(os.path.join(OUT, 'preview.png'))
    print('한글 %d + 완성형 밖 %d 칸, → %s' % (len(ks), len(extra), OUT))

if __name__ == '__main__':
    main()
