# 실험 데이터와 패턴을 팀원 공유용 TXT로 저장하는 코드

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


# 각 실험의 조건 수와 DNA 파일 수 및 패턴 파일 수다
COUNTS = {1: (30, 10, 6), 2: (54, 2, 54), 3: (27, 9, 9)}


def load_descriptions(path):
    # 루트 안내와 세 실험 설명이 모두 준비됐는지 확인한다
    descriptions = json.loads(path.read_text(encoding="utf-8-sig"))
    if set(descriptions) != {"root", "1", "2", "3"}:
        raise ValueError("설명 JSON의 키는 root 1 2 3이어야 합니다")
    if not all(isinstance(text, str) and text.strip() for text in descriptions.values()):
        raise ValueError("설명은 빈 문자열이 아닌 글이어야 합니다")
    return descriptions


def name_part(value):
    # 조건 값을 안전한 파일 이름으로 사용할 수 있는지 확인한다
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"파일 이름에 사용할 수 없는 값: {value!r}")
    return value


def collect_inputs(source):
    texts = {}
    patterns = {}
    text_info = {}
    case_ids = set()

    # 원래 조건 명세에서 공유할 DNA와 패턴을 모은다
    for number, (case_count, text_count, pattern_count) in COUNTS.items():
        folder = Path(f"실험 {number}")
        package = json.loads((source / folder / "cases.json").read_text(encoding="utf-8-sig"))
        cases = package["cases"]
        if len(cases) != case_count:
            raise ValueError(f"실험 {number}의 원본 조건 수가 다릅니다")
        for case in cases:
            case_id = case["case_id"]
            if case_id in case_ids:
                raise ValueError(f"중복 조건: {case_id}")
            case_ids.add(case_id)

            text_name = case["text_file"]
            if not re.fullmatch(r"text_[A-Za-z0-9_]+\.txt", text_name):
                raise ValueError(f"잘못된 텍스트 파일 이름: {text_name}")
            relative_text = folder / text_name
            text_path = (source / relative_text).resolve(strict=True)
            if not text_path.is_relative_to(source):
                raise ValueError("텍스트 파일이 원본 폴더 밖에 있습니다")
            # 여러 조건에서 사용하는 DNA는 한 번 읽어 길이와 해시를 확인한다
            if relative_text not in text_info:
                data = text_path.read_bytes()
                if not data or set(data) - set(b"ACGT"):
                    raise ValueError(f"DNA 문자 외의 내용이 있습니다: {relative_text}")
                text_info[relative_text] = (len(data), hashlib.sha256(data).hexdigest())
                texts[relative_text] = text_path
            if text_info[relative_text] != (case["n"], case["text_sha256"]):
                raise ValueError(f"원본 길이 또는 해시가 다릅니다: {case_id}")

            pattern = case["pattern"].encode("ascii")
            if len(pattern) != case["m"] or not pattern or set(pattern) - set(b"ACGT"):
                raise ValueError(f"잘못된 패턴: {case_id}")
            # 반복 실험은 반복 유형과 조건으로 이름을 만들고 나머지는 원천과 길이를 쓴다
            if number == 3:
                unit = name_part(case["repeat_unit"])
                condition = name_part(case["condition"])
                pattern_name = f"pattern_{unit}_{condition}.txt"
            else:
                source_name = name_part(case["source"])
                pattern_id = name_part(case["pattern_id"])
                pattern_name = f"pattern_{source_name}_{pattern_id}_m{len(pattern)}.txt"
            relative_pattern = folder / "패턴" / pattern_name
            # 같은 이름의 패턴을 한 파일로 묶고 내용이 같은지 확인한다
            if relative_pattern in patterns and patterns[relative_pattern] != pattern:
                raise ValueError(f"같은 이름에 다른 패턴이 있습니다: {relative_pattern}")
            patterns[relative_pattern] = pattern

        # 실험별 DNA와 패턴의 개수 및 원본 파일 목록을 확인한다
        if sum(path.parts[0] == str(folder) for path in texts) != text_count:
            raise ValueError(f"실험 {number}의 텍스트 파일 수가 다릅니다")
        if sum(path.parts[0] == str(folder) for path in patterns) != pattern_count:
            raise ValueError(f"실험 {number}의 패턴 파일 수가 다릅니다")
        if set((source / folder).glob("text_*.txt")) != {
            source / path for path in texts if path.parts[0] == str(folder)
        }:
            raise ValueError(f"실험 {number}의 원본 텍스트 목록이 조건 목록과 다릅니다")
    return texts, patterns


def export(source, out, descriptions):
    # 원본과 출력 위치를 확인하고 새 공유 폴더를 준비한다
    source = source.resolve(strict=True)
    out = out.resolve()
    if out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError("출력 폴더는 원본과 서로 겹치지 않아야 합니다")
    if out.exists():
        raise FileExistsError("출력 폴더는 아직 존재하지 않는 새 경로여야 합니다")
    texts, patterns = collect_inputs(source)

    # 검증한 DNA를 복사하고 패턴을 개별 TXT로 저장한다
    out.mkdir(parents=True)
    for relative_path, original in texts.items():
        target = out / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    for relative_path, pattern in patterns.items():
        target = out / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(pattern)
    # 공통 안내와 실험별 설명을 MD로 저장한다
    (out / "00_공유안내.md").write_text(descriptions["root"], encoding="utf-8", newline="\n")
    for number in COUNTS:
        (out / f"실험 {number}" / "00_설명.md").write_text(
            descriptions[str(number)], encoding="utf-8", newline="\n"
        )

    # 최종 공유 파일 수가 TXT 90개와 MD 4개인지 확인한다
    files = [path for path in out.rglob("*") if path.is_file()]
    if len(files) != 94 or sum(path.suffix == ".txt" for path in files) != 90:
        raise ValueError("출력은 TXT 90개와 MD 4개여야 합니다")
    print("저장 완료: 텍스트 TXT 21개, 패턴 TXT 69개, 설명 MD 4개")


def main():
    # 원패키지와 새 출력 폴더 및 설명 파일을 실행 인자로 받는다
    parser = argparse.ArgumentParser(description="실험 데이터와 패턴을 팀원 공유용 TXT로 저장하는 코드")
    parser.add_argument("--source", type=Path, required=True, help="완전 원패키지 폴더")
    parser.add_argument("--out", type=Path, required=True, help="새 공유용 출력 폴더")
    parser.add_argument("--descriptions", type=Path, required=True, help="root 1 2 3 설명 JSON")
    args = parser.parse_args()
    export(args.source, args.out, load_descriptions(args.descriptions))


if __name__ == "__main__":
    main()
