"""인제 ASOS CSV의 기본정보를 확인한다. 원본 데이터는 변경하지 않는다."""

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data/raw/inje_asos_211_daily_20250901_20260831.csv"


def print_report():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    print("읽은 파일:", CSV_PATH)
    print(f"\n[1] 데이터 크기: {df.shape[0]}행 × {df.shape[1]}열")

    print("\n[2] 컬럼 이름과 자료형")
    print(df.dtypes.to_string())

    print("\n[3] 앞 5개 데이터")
    print(df.head().to_string(index=False))

    # 원본 날짜 컬럼은 유지하고, 날짜 검사에 사용할 값만 변환한다.
    dates = pd.to_datetime(df["tm"], format="%Y-%m-%d", errors="coerce")
    print("\n[4] 날짜 범위")
    print("최소 날짜:", dates.min())
    print("최대 날짜:", dates.max())
    print("날짜 변환 실패 또는 결측:", dates.isna().sum())
    valid_dates = dates.dropna()
    print("중복 날짜:", valid_dates.duplicated().sum())
    if not valid_dates.empty:
        expected = pd.date_range(valid_dates.min(), valid_dates.max(), freq="D")
        missing = expected.difference(valid_dates)
        print("기간 내 누락 날짜 수:", len(missing))
        if len(missing):
            print(missing.strftime("%Y-%m-%d").tolist())

    print("\n[5] 컬럼별 결측치 개수")
    print(df.isna().sum().to_string())
    print("전체가 비어 있는 컬럼:", df.columns[df.isna().all()].tolist())

    print("\n[6] 중복 행 개수:", df.duplicated().sum())
    print("\n강수량(sumRn)의 결측치는 의미 확인 전까지 0으로 바꾸지 않습니다.")


def main():
    # 화면에 출력할 내용을 모아 UTF-8 텍스트 파일로도 저장한다.
    buffer = StringIO()
    with redirect_stdout(buffer):
        print_report()
    report = buffer.getvalue()
    output_path = PROJECT_ROOT / "outputs" / "data_basic_info.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8-sig")
    print(report, end="")
    print("\n결과 저장 위치:", output_path)


if __name__ == "__main__":
    main()
