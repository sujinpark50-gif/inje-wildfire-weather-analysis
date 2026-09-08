# 인제군 산불 위험 기상 조건 시계열 분석

기상청 인제 ASOS(211) 일별 기상자료를 활용하여 저습도·강풍 조건의 시간적 패턴을 분석하는 과제입니다.

## 분석 기간

2025-09-01 ~ 2026-08-31

## 분석 질문

1. 저습도 기간은 언제 집중되는가?
2. 강풍 기간은 언제 집중되는가?
3. 저습도와 강풍이 동시에 나타난 날은 어느 시기에 많은가?

## 데이터 출처

기상청 기상자료개방포털 ASOS 인제 관측소(211)

## 실행 방법

Python 3.10 이상과 공공데이터포털 인증키가 필요합니다. 먼저
[기상청 지상(종관, ASOS) 일자료 조회서비스](https://www.data.go.kr/data/15059093/openapi.do)에서
활용 신청 후 발급받은 일반 인증키를 환경변수에 설정합니다.

프로젝트 폴더의 `.env.example`을 `.env`로 복사한 뒤 발급받은 일반 인증키를 입력합니다.

```powershell
Copy-Item .env.example .env
notepad .env
python scripts/collect_asos_daily.py
```

`.env` 파일 내용:

```dotenv
DATA_GO_KR_SERVICE_KEY=발급받은_일반_인증키
```

기본 실행은 인제 ASOS(211)의 `2025-09-01`~`2026-08-31` 일자료를
`data/raw/inje_asos_211_daily_20250901_20260831.csv`에 저장합니다. 날짜나 출력 경로는 바꿀 수 있습니다.

```powershell
python scripts/collect_asos_daily.py --start 20250901 --end 20260831 --output data/raw/inje_asos.csv
```

일자료는 전일(D-1)까지만 제공됩니다. CSV에는 날짜, 기온, 강수량, 평균·최대·순간최대 풍속,
평균·최저 상대습도 등 API가 반환한 관측 요소가 포함됩니다. 인증키가 Git에 올라가지 않도록
`.env`는 `.gitignore`에서 제외됩니다. `.env.example`에는 실제 인증키를 입력하지 마세요.
