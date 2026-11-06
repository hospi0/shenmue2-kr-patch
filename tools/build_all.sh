#!/bin/bash
# 쉔무 II 빌드 재료 만들기(디스크 쓰기 없음). 끝에 ALL_OK 가 찍혀야 성공. discbuild --write 는 하스피 허락 후 따로.
set -e -o pipefail
cd "$(dirname "$0")/.."
python tools/merge_extra.py
python tools/build_text.py
grep -q BUILD_TEXT_OK <(python -c "print('BUILD_TEXT_OK')")
python tools/build_exe.py "work/text/ko/sm2_*.tsv" "work/text/ko_extra/*.tsv"
python tools/verify_exe.py "work/text/ko/sm2_*.tsv" "work/text/ko_extra/*.tsv"
cp work/build/1ST_READ.BIN work/build/common/1ST_READ.BIN
python tools/tex_pack.py
for n in 1 2 3 4; do python tools/discbuild.py --disc $n; done
echo ALL_OK
