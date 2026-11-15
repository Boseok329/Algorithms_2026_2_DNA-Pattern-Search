"""공통 실험 CSV를 읽어 한국어 HTML 보고서와 PNG/SVG 그래프를 만든다.

실행: python -B code/render_results.py RESULTS_FOLDER
입력 CSV와 metadata.json은 변경하지 않는다. matplotlib만 추가로 사용한다.
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import statistics
from collections import Counter
from pathlib import Path

ALGORITHMS = ("Naive", "KMP", "Boyer-Moore")
COLORS = {"Naive": "#536273", "KMP": "#087f8c", "Boyer-Moore": "#b84b2d"}
SOURCE_LABELS = {"random": "무작위 DNA", "ecoli": "대장균 DNA", "synthetic_repeat": "반복 DNA"}
CONDITION_LABELS = {
    "end_mismatch": "마지막 글자 불일치",
    "start_mismatch": "첫 글자 불일치",
    "many_matches": "완전 일치 반복",
}
INT_FIELDS = ("experiment", "n", "m", "match_count", "repeats", "preprocessing_comparisons",
              "search_comparisons", "total_comparisons", "peak_python_bytes")
FLOAT_FIELDS = ("mean_ms", "median_ms", "min_ms", "max_ms", "stdev_ms")


def escaped(value):
    return html.escape(str(value), quote=True)


def number(value, digits=3):
    return f"{value:,.{digits}f}"


def load_results(folder):
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8-sig"))
    if metadata.get("status") != "complete":
        raise ValueError("완료된 실험 결과만 보고서로 생성합니다.")
    with (folder / "summary.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in INT_FIELDS:
            row[key] = int(row[key])
        for key in FLOAT_FIELDS:
            row[key] = float(row[key])
        if str(row["correct"]).lower() not in ("true", "1"):
            raise ValueError(f"정답 불일치 결과: {row['case_id']} / {row['algorithm']}")
    if len(rows) != 333 or len({r["case_id"] for r in rows}) != 111:
        raise ValueError("111조건 × 3알고리즘의 333개 요약 행이 필요합니다.")
    if Counter(r["algorithm"] for r in rows) != Counter({a: 111 for a in ALGORITHMS}):
        raise ValueError("알고리즘별 조건 수가 다릅니다.")
    if len({(r["case_id"], r["algorithm"]) for r in rows}) != len(rows):
        raise ValueError("중복된 조건·알고리즘 행이 있습니다.")
    with (folder / "runs.csv").open(encoding="utf-8-sig", newline="") as stream:
        runs = list(csv.DictReader(stream))
    if len(runs) != sum(r["repeats"] for r in rows):
        raise ValueError("원시 시간 측정 수와 요약의 반복 수가 다릅니다.")
    return metadata, rows, runs


def group_mean(rows, field, **selection):
    selected = [r[field] for r in rows if all(r.get(k) == v for k, v in selection.items())]
    if not selected:
        raise ValueError(f"필요한 결과가 없습니다: {selection}")
    return statistics.mean(selected)


def make_figures(folder, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.ticker import FuncFormatter

    available = {f.name for f in font_manager.fontManager.ttflist}
    font = next((n for n in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans CJK SC", "NanumGothic", "Arial") if n in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": font, "axes.unicode_minus": False, "font.size": 10,
        "axes.titlesize": 12, "axes.labelsize": 10, "axes.spines.top": False,
        "axes.spines.right": False, "grid.alpha": .22, "figure.facecolor": "white",
        "savefig.facecolor": "white", "svg.fonttype": "path",
    })
    charts = folder / "charts"
    charts.mkdir(exist_ok=True)
    saved = {}

    def save(fig, name):
        fig.savefig(charts / f"{name}.png", dpi=180, bbox_inches="tight")
        fig.savefig(charts / f"{name}.svg", bbox_inches="tight")
        plt.close(fig)
        saved[name] = "data:image/png;base64," + base64.b64encode((charts / f"{name}.png").read_bytes()).decode("ascii")

    def dual_plot(experiment, field, name, ylabel, title, scale=1):
        fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.3), layout="constrained", sharey=True)
        key = "n" if experiment == 1 else "m"
        xs = sorted({r[key] for r in rows if r["experiment"] == experiment})
        y_max = max(group_mean(rows, field, experiment=experiment, source=source, algorithm=algorithm, **{key: x}) / scale
                    for source in ("random", "ecoli") for algorithm in ALGORITHMS for x in xs)
        for ax, source in zip(axes, ("random", "ecoli")):
            for algorithm in ALGORITHMS:
                ys = [group_mean(rows, field, experiment=experiment, source=source, algorithm=algorithm, **{key: x}) / scale for x in xs]
                ax.plot(xs, ys, label=algorithm, color=COLORS[algorithm], marker="o", markersize=4, linewidth=1.8)
            ax.set_title(SOURCE_LABELS[source])
            ax.set_ylabel(ylabel)
            ax.set_xlabel("DNA 길이 n (bp)" if key == "n" else "패턴 길이 m (bp)")
            if key == "m":
                ax.set_xscale("log", base=2)
                ax.set_xticks(xs, [str(x) for x in xs], rotation=35)
            else:
                ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x / 1_000_000:g}M"))
            ax.grid(True)
            ax.set_ylim(0, y_max * 1.08 if y_max > 0 else 1)
            ax.legend(frameon=False)
        fig.suptitle(title, fontsize=14, fontweight="bold")
        save(fig, name)

    dual_plot(1, "mean_ms", "experiment1_time", "평균 실행 시간 (ms)", "실험 1 · DNA 길이 변화 / m = 32")
    dual_plot(2, "mean_ms", "experiment2_time", "평균 실행 시간 (ms)", "실험 2 · 패턴 길이 변화 / n = 1,000,000")
    dual_plot(2, "peak_python_bytes", "experiment2_memory", "Python 할당 최대치 (KiB)", "실험 2 · 패턴 길이별 메모리 / 입력 문자열 할당 제외", 1024)
    dual_plot(2, "search_comparisons", "experiment2_comparisons", "검색 문자 비교 횟수 (백만 회)", "실험 2 · 검색 문자 비교 횟수 / 전처리 비교는 별도 기록", 1_000_000)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2), layout="constrained")
    xs = sorted({r["n"] for r in rows if r["experiment"] == 3})
    for ax, condition in zip(axes, CONDITION_LABELS):
        for algorithm in ALGORITHMS:
            ys = [group_mean(rows, "mean_ms", experiment=3, repeat_unit="A", condition=condition, algorithm=algorithm, n=n) for n in xs]
            ax.plot(xs, ys, label=algorithm, color=COLORS[algorithm], marker="o", linewidth=1.8, markersize=4)
        ax.set_title(CONDITION_LABELS[condition])
        ax.set_xlabel("DNA 길이 n (bp)")
        ax.set_ylabel("평균 실행 시간 (ms)")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x / 1000:g}k"))
        ax.grid(True)
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, fontsize=9)
    fig.suptitle("실험 3 · A 반복 기본 조건 / m = 32", fontsize=14, fontweight="bold")
    save(fig, "experiment3_time")
    return saved


def winner_statement(rows, experiment, source, n, m):
    values = {a: group_mean(rows, "mean_ms", experiment=experiment, source=source, n=n, m=m, algorithm=a) for a in ALGORITHMS}
    winner = min(values, key=values.get)
    detail = " · ".join(f"{a} {number(values[a])} ms" for a in ALGORITHMS)
    ratio = values["Naive"] / values[winner] if values[winner] > 0 else float("nan")
    suffix = f" Naive 시간은 {winner} 시간의 {number(ratio, 2)}배였습니다." if winner != "Naive" else ""
    return f"{SOURCE_LABELS[source]} n={n:,}, m={m}: <b>{winner}</b>의 관측 평균이 가장 작았습니다.{suffix} <span class='muted'>{detail}</span>"


def summary_table(rows, experiment):
    key = "n" if experiment == 1 else "m"
    headings = ["입력", "DNA 길이 n" if key == "n" else "패턴 길이 m", "Naive (ms)", "KMP (ms)", "Boyer–Moore (ms)", "관측 최솟값"]
    output = ["<div class='table-wrap'><table><thead><tr>", *[f"<th>{h}</th>" for h in headings], "</tr></thead><tbody>"]
    for source in ("random", "ecoli"):
        for x in sorted({r[key] for r in rows if r["experiment"] == experiment and r["source"] == source}):
            values = {a: group_mean(rows, "mean_ms", experiment=experiment, source=source, algorithm=a, **{key: x}) for a in ALGORITHMS}
            winner = min(values, key=values.get)
            output.append(f"<tr><td>{SOURCE_LABELS[source]}</td><td class='num'>{x:,}</td>")
            output.extend(f"<td class='num{' best' if a == winner else ''}'>{number(values[a])}</td>" for a in ALGORITHMS)
            output.append(f"<td>{escaped(winner)}</td></tr>")
    output.append("</tbody></table></div>")
    return "".join(output)


def repeat_table(rows):
    output = ["<div class='table-wrap'><table><thead><tr><th>반복</th><th>조건</th><th>n</th>"]
    output.extend(f"<th>{escaped(a)} (ms)</th>" for a in ALGORITHMS)
    output.append("<th>일치 개수</th></tr></thead><tbody>")
    for unit in ("A", "AC", "ACGT"):
        for condition, label in CONDITION_LABELS.items():
            for n in sorted({r["n"] for r in rows if r["experiment"] == 3}):
                selected = [r for r in rows if r["experiment"] == 3 and r["repeat_unit"] == unit and r["condition"] == condition and r["n"] == n]
                values = {r["algorithm"]: r["mean_ms"] for r in selected}
                winner = min(values, key=values.get)
                output.append(f"<tr><td>{unit}{' · 기본' if unit == 'A' else ' · 보조'}</td><td>{label}</td><td class='num'>{n:,}</td>")
                output.extend(f"<td class='num{' best' if a == winner else ''}'>{number(values[a])}</td>" for a in ALGORITHMS)
                output.append(f"<td class='num'>{selected[0]['match_count']:,}</td></tr>")
    output.append("</tbody></table></div>")
    return "".join(output)


def detail_table(rows):
    ordered = sorted(rows, key=lambda r: (r["experiment"], r["case_id"], ALGORITHMS.index(r["algorithm"])))
    output = []
    for r in ordered:
        text = " ".join(str(r.get(k, "")) for k in ("case_id", "source", "repeat_unit", "condition", "algorithm"))
        output.append(f"<tr data-exp='{r['experiment']}' data-algo='{escaped(r['algorithm'])}' data-search='{escaped(text.lower())}'><td>{escaped(r['case_id'])}</td><td>{escaped(r['algorithm'])}</td>")
        output.append(f"<td class='num'>{r['n']:,}</td><td class='num'>{r['m']:,}</td><td class='num'>{r['match_count']:,}</td>")
        output.extend(f"<td class='num'>{number(r[k])}</td>" for k in ("mean_ms", "median_ms", "stdev_ms"))
        output.extend(f"<td class='num'>{r[k]:,}</td>" for k in ("preprocessing_comparisons", "search_comparisons"))
        output.append(f"<td class='num'>{number(r['peak_python_bytes'] / 1024)}</td></tr>")
    return "".join(output)


def create_html(folder, metadata, rows, runs, images):
    repeats = sorted({r["repeats"] for r in rows})
    if len(repeats) != 1:
        raise ValueError("조건별 시간 측정 횟수가 다릅니다.")
    observations = [winner_statement(rows, 1, source, 4_000_000, 32) for source in ("random", "ecoli")]
    repeat_rows = [r for r in rows if r["experiment"] == 3 and r["repeat_unit"] == "A" and r["condition"] == "many_matches" and r["n"] == 70000]
    values = {r["algorithm"]: r["mean_ms"] for r in repeat_rows}
    counts = {r["algorithm"]: r["search_comparisons"] for r in repeat_rows}
    expected_count = (70000 - 32 + 1) * 32
    observations.append("A 반복 완전 일치 n=70,000에서는 " + " · ".join(f"{a} <b>{number(values[a])} ms</b>" for a in ALGORITHMS) + "를 기록했습니다.")
    if counts["Boyer-Moore"] == expected_count and counts["Naive"] == expected_count:
        observations.append(f"이 조건의 Naive와 Boyer–Moore 검색 비교 횟수는 각각 <b>{expected_count:,}회</b>로 같았습니다. 사용한 Boyer–Moore는 Galil 규칙이 없으며, 완전 일치 후 겹치는 다음 위치에서 문자를 다시 비교합니다. KMP는 <b>{counts['KMP']:,}회</b>를 기록했습니다.")
    case_wins = Counter()
    for case_id in {r["case_id"] for r in rows}:
        selected = [r for r in rows if r["case_id"] == case_id]
        case_wins[min(selected, key=lambda r: r["mean_ms"])["algorithm"]] += 1
    downloaded = [("runs.csv", "개별 시간 측정"), ("summary.csv", "조건별 요약"), ("metadata.json", "실행 환경·측정 기준")]
    for filename, label in (("verification.json", "정확성·보존 검수"), ("source_manifest.json", "원본 해시"), ("preservation.json", "원본 보존 검수")):
        if (folder / filename).exists():
            downloaded.append((filename, label))
    integrity = metadata.get("original_integrity_after", {})
    source_unchanged = integrity.get("unchanged") if isinstance(integrity, dict) else None
    if source_unchanged is None:
        source_unchanged = metadata.get("originals_unchanged") or metadata.get("source_files_unchanged")
    preservation = "원본 보존 여부는 실행 검수 기록에서 확인할 수 있습니다."
    if source_unchanged is True:
        preservation = "실행 전후 원본 파일 해시가 일치하여 원본 보존을 확인했습니다."
    # 메타데이터에 실제로 있는 환경 정보만 표시한다.
    environment = []
    for key, label in (("python", "Python"), ("platform", "운영체제"), ("processor", "CPU"), ("started_at", "시작"), ("finished_at", "완료")):
        if metadata.get(key):
            environment.append(f"<dt>{label}</dt><dd>{escaped(metadata[key])}</dd>")

    def figure(name, title, caption):
        return f"<figure><img src='{images[name]}' alt='{escaped(title)}'><figcaption>{escaped(caption)} <a href='charts/{name}.svg'>SVG</a> · <a href='charts/{name}.png'>PNG</a></figcaption></figure>"

    page = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DNA 패턴 검색 · 통합 실험 결과</title><style>
    :root{--ink:#172c36;--muted:#5c7079;--line:#dce5e9;--teal:#087f8c;--paper:#f3f6f7}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 'Malgun Gothic','Apple SD Gothic Neo',sans-serif}main{max-width:1220px;margin:auto;padding:42px 28px 70px}header{border-bottom:2px solid var(--ink);padding-bottom:26px;margin-bottom:28px}.eyebrow{font-size:12px;letter-spacing:.15em;color:var(--teal);font-weight:700}h1{font-size:34px;line-height:1.3;margin:12px 0}h2{font-size:24px;margin:0 0 16px}h3{font-size:18px;margin:24px 0 10px}p{margin:10px 0}.muted,figcaption,.note{color:var(--muted)}.note,figcaption{font-size:13px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}.card{background:white;border:1px solid var(--line);border-radius:12px;padding:18px}.card b{display:block;font-size:27px;line-height:1.3}.card span{font-size:13px;color:var(--muted)}section{background:white;border:1px solid var(--line);border-radius:14px;padding:26px;margin:22px 0}.findings{padding-left:23px}.findings li{padding:5px 0}.links{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.links a{display:inline-block;padding:7px 13px;border:1px solid var(--line);border-radius:7px;text-decoration:none;background:#fff}a{color:#086e80}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px;margin:16px 0}table{border-collapse:collapse;min-width:100%;font-size:13px;white-space:nowrap}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}th{background:#edf3f5;color:#354e59;position:sticky;top:0;z-index:1}tbody tr:last-child td{border:0}.num{text-align:right;font-variant-numeric:tabular-nums}.best{background:#ecf8f5;color:#066b60;font-weight:bold}figure{margin:24px 0}figure img{display:block;width:100%;height:auto}figcaption{padding:8px 4px}.filters{display:flex;gap:9px;flex-wrap:wrap;align-items:center}select,input{font:inherit;font-size:14px;border:1px solid #bdcdd4;border-radius:6px;padding:8px 11px;background:white}input{min-width:250px;flex:1}.detail{max-height:560px}.detail td:first-child{font-size:12px}dl{display:grid;grid-template-columns:100px 1fr;gap:7px 18px;font-size:13px}dt{font-weight:bold}dd{margin:0;overflow-wrap:anywhere}.protocol{display:grid;grid-template-columns:1fr 1fr;gap:20px}.protocol p{font-size:14px}details>summary{cursor:pointer;font-weight:bold}.footer{font-size:13px;color:var(--muted)}@media(max-width:700px){main{padding:24px 14px}h1{font-size:27px}section{padding:18px}.cards{grid-template-columns:1fr 1fr}.protocol{grid-template-columns:1fr}input{min-width:160px}}@media print{body{background:white}main{padding:0;max-width:none}section{break-inside:avoid;border:0;padding:12px 0}.filters,.links{display:none}.detail{max-height:none}.detail-section{break-before:page}.card{padding:10px}figure{break-inside:avoid}}
    </style></head><body><main>
    <header><div class="eyebrow">D1 · DNA PATTERN SEARCH</div><h1>세 알고리즘, 같은 입력에서 비교</h1><p>Naive · KMP · Boyer–Moore를 같은 PC와 공통 실행기로 측정한 결과입니다.</p>__LINKS__</header>
    <div class="cards"><div class="card"><b>111</b><span>공통 입력 조건</span></div><div class="card"><b>333 / 333</b><span>조건·알고리즘 정답 일치</span></div><div class="card"><b>__RUN_COUNT__</b><span>개별 시간 측정 · 조건마다 __REPEATS__회</span></div><div class="card"><b>별도 측정</b><span>문자 비교 횟수 · Python 메모리</span></div></div>
    <section><h2>이번 실행에서 확인한 결과</h2><ul class="findings">__OBSERVATIONS__</ul><p class="note">111조건에서 평균 시간이 가장 작았던 횟수: __WINS__. 이 수치는 구성한 입력과 이번 실행의 관측값이며, 모든 입력에서의 우열이나 통계적 유의성을 뜻하지 않습니다.</p></section>
    <section><h2>측정 기준</h2><div class="protocol"><div><h3>시간과 정확성</h3><p>조건마다 알고리즘별 워밍업 1회 후 __REPEATS__회 측정했습니다. 알고리즘 실행 순서를 회차별로 바꿨습니다. 전처리·검색·전체 위치 목록 생성을 포함하고, 파일 읽기·정답 확인·비교 계측·메모리 추적은 시간에서 제외했습니다.</p><p>KMP는 원본과 같은 분기·LPS 로직에서 비교 카운터를 제거한 시간 측정용 함수를 사용했습니다. 비교 횟수는 받은 원본 구현으로 측정했습니다. 겹치는 모든 위치를 0부터 시작하는 인덱스로 대조했습니다.</p></div><div><h3>문자 비교와 메모리</h3><p>전처리 비교와 검색 비교를 별도로 기록했습니다. 정수 비교와 해시 연산은 문자 비교 수에 포함하지 않았습니다.</p><p>메모리는 각 조건·알고리즘별 별도 실행에서 tracemalloc으로 측정한 <b>Python 할당 최대치</b>입니다. 전처리 자료구조와 결과 목록을 포함하며, 이미 읽어 둔 입력 문자열은 제외합니다. 전체 프로세스의 최대 메모리(RSS)와는 다릅니다. 1 KiB = 1,024 bytes입니다.</p></div></div><p class="note">__PRESERVATION__</p><details><summary>실행 환경</summary><dl>__ENVIRONMENT__</dl></details></section>
    <section><h2>실험 1 · DNA 길이 변화</h2><p>패턴 길이 32를 고정하고 DNA 길이를 100,000부터 4,000,000까지 늘렸습니다.</p>__E1_FIG__<p class="note">각 점과 표의 값은 패턴 3개의 조건별 평균 시간을 다시 평균한 값입니다. 패턴마다 __REPEATS__회 측정했고, 개별 값은 원시 CSV에 보존했습니다.</p>__E1_TABLE__</section>
    <section><h2>실험 2 · 패턴 길이 변화</h2><p>DNA 길이 1,000,000을 고정하고 패턴 길이를 4부터 1,000까지 바꿨습니다.</p>__E2_FIG__<p class="note">각 점과 표는 패턴 3개 평균입니다. x축은 2를 밑으로 한 로그 눈금입니다.</p>__E2_TABLE__<details open><summary>비교 횟수와 메모리</summary>__CMP_FIG____MEM_FIG__<p class="note">메모리 그래프도 패턴 3개의 별도 메모리 측정값 평균입니다. 짧은 패턴에서 일치 개수가 많으면 결과 위치 목록이 차지하는 메모리도 커집니다. 전처리·검색 비교와 일치 개수는 아래 상세 표에서 함께 확인할 수 있습니다.</p></details></section>
    <section><h2>실험 3 · 반복 문자열</h2><p>A 반복 9조건이 기본 실험입니다. AC·ACGT 반복 18조건을 보조 실험으로 함께 보존했습니다. 모든 패턴 길이는 32입니다.</p>__E3_FIG__<details><summary>A · AC · ACGT 전체 27조건</summary>__E3_TABLE__</details></section>
    <section class="detail-section"><h2>조건별 상세 결과</h2><p class="note">시간 단위 ms · 메모리 단위 KiB. 표준편차는 같은 조건의 __REPEATS__회 시간 측정에 대한 표본 표준편차입니다.</p><div class="filters"><select id="exp"><option value="">전체 실험</option value="1">실험 1</option><option value="2">실험 2</option><option value="3">실험 3</option></select><select id="algo"><option value="">전체 알고리즘</option><option>Naive</option><option>KMP</option><option>Boyer-Moore</option></select><input id="query" type="search" placeholder="조건 ID · random · ecoli · many_matches 검색" aria-label="상세 결과 검색"><span id="visible" class="note">333개</span></div><div class="table-wrap detail"><table id="details"><thead><tr><th>조건 ID</th><th>알고리즘</th><th>n</th><th>m</th><th>일치 수</th><th>평균 ms</th><th>중앙값 ms</th><th>표준편차 ms</th><th>전처리 비교</th><th>검색 비교</th><th>메모리 KiB</th></tr></thead><tbody>__DETAIL_ROWS__</tbody></table></div></section>
    <p class="footer">실험 결과 CSV에서 생성한 보고서입니다. 입력·원본 코드·실험별 원시 측정값은 통합 폴더에서 확인할 수 있습니다.</p>
    </main><script>const exp=document.getElementById('exp'),algo=document.getElementById('algo'),query=document.getElementById('query');function filter(){let count=0;const q=query.value.trim().toLowerCase();for(const row of document.querySelectorAll('#details tbody tr')){const show=(!exp.value||row.dataset.exp===exp.value)&&(!algo.value||row.dataset.algo===algo.value)&&(!q||row.dataset.search.includes(q));row.hidden=!show;if(show)count++;}document.getElementById('visible').textContent=count+'개';}for(const el of [exp,algo,query])el.addEventListener('input',filter);</script></body></html>"""
    replacements = {
        "__LINKS__": "<div class='links'>" + "".join(f"<a href='{filename}' download>{label}</a>" for filename, label in downloaded) + "</div>",
        "__RUN_COUNT__": f"{len(runs):,}", "__REPEATS__": str(repeats[0]),
        "__OBSERVATIONS__": "".join(f"<li>{o}</li>" for o in observations),
        "__WINS__": " · ".join(f"{a} {case_wins[a]}조건" for a in ALGORITHMS),
        "__PRESERVATION__": preservation, "__ENVIRONMENT__": "".join(environment),
        "__E1_FIG__": figure("experiment1_time", "실험 1 시간 그래프", "같은 길이의 패턴 3개 평균 · 선은 측정점 연결"),
        "__E2_FIG__": figure("experiment2_time", "실험 2 시간 그래프", "같은 길이의 패턴 3개 평균 · 선은 측정점 연결"),
        "__E3_FIG__": figure("experiment3_time", "A 반복 시간 그래프", f"A 반복 기본 실험 · 조건별 {repeats[0]}회 시간 측정 평균"),
        "__CMP_FIG__": figure("experiment2_comparisons", "실험 2 검색 비교 횟수", "실행 시간과 분리하여 계측 · 전처리 비교는 상세 표 참조"),
        "__MEM_FIG__": figure("experiment2_memory", "실험 2 Python 할당 최대치", "시간 측정과 분리한 tracemalloc 측정 · 결과 목록 포함"),
        "__E1_TABLE__": summary_table(rows, 1), "__E2_TABLE__": summary_table(rows, 2),
        "__E3_TABLE__": repeat_table(rows), "__DETAIL_ROWS__": detail_table(rows),
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    (folder / "result.html").write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="완료한 DNA 공통 실험 결과의 HTML·그래프 생성")
    parser.add_argument("result_folder", type=Path)
    args = parser.parse_args()
    folder = args.result_folder.resolve()
    metadata, rows, runs = load_results(folder)
    images = make_figures(folder, rows)
    create_html(folder, metadata, rows, runs, images)
    print(json.dumps({"html": str(folder / "result.html"), "charts": len(images), "summary_rows": len(rows), "timed_runs": len(runs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
