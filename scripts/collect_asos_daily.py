#!/usr/bin/env python3
"""공공데이터포털에서 인제 ASOS(211) 일자료를 수집해 CSV로 저장한다."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, unquote
from urllib.request import Request, urlopen


API_URL = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
DEFAULT_STATION_ID = "211"
DEFAULT_START_DATE = "20250901"
DEFAULT_END_DATE = "20260831"
DEFAULT_OUTPUT = Path("data/raw/inje_asos_211_daily_20250901_20260831.csv")
ROWS_PER_PAGE = 999
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 분석에 자주 쓰는 열을 CSV 앞쪽에 둔다. API가 추가 필드를 반환하면 뒤에 보존한다.
PREFERRED_FIELDS = [
    "tm",
    "stnId",
    "stnNm",
    "avgTa",
    "minTa",
    "maxTa",
    "sumRn",
    "avgWs",
    "maxWs",
    "maxWsWd",
    "maxInsWs",
    "maxInsWsWd",
    "avgRhm",
    "minRhm",
    "minRhmHrmt",
]


class CollectionError(RuntimeError):
    """API 호출 또는 응답 검증에 실패했을 때 발생한다."""


def load_env_file(path: Path) -> None:
    """간단한 KEY=VALUE 형식의 .env를 환경변수로 불러온다."""
    if not path.is_file():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise CollectionError(f"{path}의 {line_number}번째 줄이 KEY=VALUE 형식이 아닙니다.")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key:
            raise CollectionError(f"{path}의 {line_number}번째 줄에 변수명이 없습니다.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def parse_yyyymmdd(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("날짜는 YYYYMMDD 형식이어야 합니다.") from exc


def request_json(params: dict[str, str | int], retries: int = 3) -> dict[str, Any]:
    # 포털이 제공하는 Encoding 키와 Decoding 키를 모두 받을 수 있게 한 번 정규화한다.
    normalized = dict(params)
    normalized["ServiceKey"] = unquote(str(normalized["ServiceKey"]))
    url = f"{API_URL}?{urlencode(normalized)}"
    request = Request(url, headers={"User-Agent": "inje-wildfire-weather-analysis/1.0"})

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8-sig")
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                snippet = " ".join(raw[:300].split())
                raise CollectionError(f"JSON이 아닌 응답을 받았습니다: {snippet}") from exc
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries:
                raise CollectionError(f"API 호출에 {retries}회 실패했습니다: {exc}") from exc
            time.sleep(2 ** (attempt - 1))

    raise AssertionError("도달할 수 없는 코드")


def response_body(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response", {})
    header = response.get("header", {})
    code = str(header.get("resultCode", ""))
    if code != "00":
        message = header.get("resultMsg", "알 수 없는 오류")
        raise CollectionError(f"API 오류 {code}: {message}")
    body = response.get("body")
    if not isinstance(body, dict):
        raise CollectionError("응답에 body가 없습니다.")
    return body


def collect_daily(
    service_key: str, station_id: str, start: date, end: date
) -> list[dict[str, Any]]:
    if start > end:
        raise CollectionError("시작일은 종료일보다 늦을 수 없습니다.")

    latest_available = date.today() - timedelta(days=1)
    if end > latest_available:
        raise CollectionError(
            f"일자료는 전일까지만 제공됩니다. 종료일을 {latest_available:%Y%m%d} 이하로 지정하세요."
        )

    records: list[dict[str, Any]] = []
    page = 1
    total_count: int | None = None

    while total_count is None or len(records) < total_count:
        payload = request_json(
            {
                "ServiceKey": service_key,
                "pageNo": page,
                "numOfRows": ROWS_PER_PAGE,
                "dataType": "JSON",
                "dataCd": "ASOS",
                "dateCd": "DAY",
                "startDt": start.strftime("%Y%m%d"),
                "endDt": end.strftime("%Y%m%d"),
                "stnIds": station_id,
            }
        )
        body = response_body(payload)
        total_count = int(body.get("totalCount", 0))
        page_items = body.get("items", {}).get("item", []) if body.get("items") else []
        if isinstance(page_items, dict):
            page_items = [page_items]
        if not isinstance(page_items, list):
            raise CollectionError("응답의 items.item 형식이 올바르지 않습니다.")
        records.extend(item for item in page_items if isinstance(item, dict))

        if not page_items:
            break
        page += 1

    if not records:
        raise CollectionError("조건에 맞는 관측자료가 없습니다.")

    # 중복을 제거하고 날짜순으로 정렬한다.
    unique = {(str(row.get("tm", "")), str(row.get("stnId", ""))): row for row in records}
    return sorted(unique.values(), key=lambda row: str(row.get("tm", "")))


def fieldnames_for(rows: list[dict[str, Any]]) -> list[str]:
    available = {key for row in rows for key in row}
    preferred = [key for key in PREFERRED_FIELDS if key in available]
    return preferred + sorted(available.difference(preferred))


def write_csv(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = fieldnames_for(rows)
    temp_name: str | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_name = temp.name
            writer = csv.DictWriter(temp, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_name, output)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="인제 ASOS(211) 일자료를 CSV로 수집합니다.")
    parser.add_argument("--start", type=parse_yyyymmdd, default=parse_yyyymmdd(DEFAULT_START_DATE))
    parser.add_argument("--end", type=parse_yyyymmdd, default=parse_yyyymmdd(DEFAULT_END_DATE))
    parser.add_argument("--station", default=DEFAULT_STATION_ID, help="ASOS 지점번호 (기본값: 211)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        load_env_file(PROJECT_ROOT / ".env")
        service_key = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
        if not service_key:
            print("오류: .env 또는 DATA_GO_KR_SERVICE_KEY 환경변수에 인증키를 설정하세요.", file=sys.stderr)
            return 2
        rows = collect_daily(service_key, args.station, args.start, args.end)
        write_csv(rows, args.output)
    except CollectionError as exc:
        print(f"수집 실패: {exc}", file=sys.stderr)
        return 1

    print(f"수집 완료: {len(rows)}건 -> {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
