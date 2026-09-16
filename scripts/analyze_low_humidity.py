"""기상청 실효습도 산출식과 건조특보 수치·지속 조건의 사후 비교."""
from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/raw/inje_asos_211_daily_20250901_20260831.csv'
CONTEXT = ROOT/'data/raw/inje_asos_211_daily_20250828_20250831.csv'
STANDARD = 'https://www.weather.go.kr/w/forecast/guide/standard.do'
FORMULA = 'https://www.kma.go.kr/kma/servlet/NeoboardProcess?bid=gangwon01&fno=2&k=ATC202204081327142_756f55de-2b9c-4a23-aa00-3e0c9aab39e0.pdf&mode=download&num=11&ses=USERSESSION'
MANUAL = 'https://data.kma.go.kr/resources/images/publication/지상기상관측지침%282022.12.%29.pdf'
COLUMNS = {'tm':'날짜','avgWs':'평균풍속','maxWs':'최대풍속','maxInsWs':'최대순간풍속','avgRhm':'평균습도','minRhm':'최소습도'}


def table(df):
    if df.empty:
        return '해당 기간 없음.'
    def fmt(v):
        return f'{v:.2f}' if isinstance(v,float) else str(v)
    rows = ['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    rows += ['| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None)]
    return '\n'.join(rows)


def effective_humidity(series):
    # 공식 보도자료의 5항 식을 사용하며 가중치 합으로 재정규화하지 않는다.
    return sum(0.3 * 0.7**lag * series.shift(lag) for lag in range(5))


def find_runs(daily, limit):
    mask = daily['실효습도_계산값'].le(limit)
    groups = mask.ne(mask.shift()).cumsum()
    runs = daily.loc[mask].groupby(groups).agg(
        시작일=('날짜','min'),종료일=('날짜','max'),연속일수=('날짜','size'),
        최저실효습도=('실효습도_계산값','min')).reset_index(drop=True)
    runs.insert(0,'기준_pct',limit)
    runs['2일이상'] = runs['연속일수'].ge(2)
    return runs


def main():
    hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,CONTEXT]}
    raw = pd.read_csv(SOURCE,encoding='utf-8-sig')
    context = pd.read_csv(CONTEXT,encoding='utf-8-sig')
    combined = pd.concat([context,raw],ignore_index=True).sort_values('tm').reset_index(drop=True)
    dates = pd.to_datetime(combined.tm,format='%Y-%m-%d',errors='raise')
    assert not dates.duplicated().any()
    assert combined.stnId.eq(211).all()
    assert dates.tolist() == list(pd.date_range('2025-08-28','2026-08-31'))
    assert combined.avgRhm.between(0,100).all()
    combined['실효습도_계산값'] = effective_humidity(combined.avgRhm)
    daily = combined.loc[combined.tm.between('2025-09-01','2026-08-31'),list(COLUMNS)+['실효습도_계산값']].rename(columns=COLUMNS).reset_index(drop=True)
    analysis = daily[list(COLUMNS.values())].copy()
    assert analysis.shape == (365,6) and not daily.isna().any().any()
    for limit in [35,25]:
        daily[f'기준{limit}이하'] = daily['실효습도_계산값'].le(limit)
    runs = pd.concat([find_runs(daily,35),find_runs(daily,25)],ignore_index=True)
    for limit in [35,25]:
        daily[f'기준{limit}_2일이상구간'] = False
        for row in runs.loc[runs['기준_pct'].eq(limit)&runs['2일이상']].itertuples(index=False,name=None):
            daily.loc[daily['날짜'].between(row[1],row[2]),f'기준{limit}_2일이상구간'] = True
    monthly = daily.assign(월=daily['날짜'].str[:7]).groupby('월',as_index=False).agg(
        관측일수=('날짜','size'),평균실효습도=('실효습도_계산값','mean'),
        최저실효습도=('실효습도_계산값','min'),
        기준35이하일수=('기준35이하','sum'),기준25이하일수=('기준25이하','sum'),
        기준35_2일이상구간일수=('기준35_2일이상구간','sum'),
        기준25_2일이상구간일수=('기준25_2일이상구간','sum'))
    selected = daily.loc[daily['기준35이하']].copy()
    qualifying = runs.loc[runs['2일이상']]
    rounding_diff = {limit:int((((daily['실효습도_계산값']+.5)//1).le(limit) != daily['실효습도_계산값'].le(limit)).sum()) for limit in [35,25]}
    out = ROOT/'outputs'
    processed = ROOT/'data/processed'
    out.mkdir(exist_ok=True)
    processed.mkdir(parents=True,exist_ok=True)
    analysis.to_csv(processed/'wind_humidity_daily.csv',index=False,encoding='utf-8-sig')
    for name,frame in [('effective_humidity_daily.csv',daily),('low_humidity_monthly.csv',monthly),('low_humidity_days.csv',selected),('low_humidity_runs.csv',runs)]:
        frame.to_csv(out/name,index=False,encoding='utf-8-sig')
    report = f'''# 인제군 산불 위험 기상 조건 시계열 분석

## 데이터 점검

원본 데이터는 365일 62개 열로 구성되며 날짜 누락과 중복은 없었다. 풍속·습도 핵심 변수에는 결측치가 없어 원값을 사용했다. 전 기간 빈값인 비핵심 변수와 빈값 의미가 확인되지 않은 강수량 변수는 이번 분석에서 제외했다. 극단적 풍속·습도 값은 분석 목적상 이상치로 삭제하지 않았다.

분석용 표는 날짜 / 평균풍속 / 최대풍속 / 최대순간풍속 / 평균습도 / 최소습도의 365행 6열이다. 풍속 단위는 m/s, 습도는 %다. 원본의 minRhm은 일최저 상대습도다. 2026-04-23 일조시간은 빈값으로 유지하며 북춘천 값으로 대체하지 않았다.

## 공식 기준과 적용 방법

기상청의 건조주의보는 실효습도 35% 이하가 2일 이상 지속될 것으로 예상될 때, 건조경보는 실효습도 25% 이하가 2일 이상 지속될 것으로 예상될 때 발표한다. [기상청 특보 발표기준]({STANDARD}) (확인: 2026-09-16)

이는 일평균 상대습도나 일최저 상대습도에 35%·25%를 직접 적용하는 기준이 아니다. 본 분석은 실효습도를 계산해 두 수치 이하인 날과 2일 이상 연속 구간을 구분했다. **과거 관측값의 사후 비교이며 실제 특보 발령일이나 예보 판단을 재현한 결과가 아니다.**

실효습도는 강원지방기상청 보도자료 2쪽의 5일 산출식을 적용했다.

`EH(t) = 0.3 × [RH(t) + 0.7 RH(t−1) + 0.7² RH(t−2) + 0.7³ RH(t−3) + 0.7⁴ RH(t−4)]`

RH는 일평균 상대습도(avgRhm)다. 당일을 포함한 5일을 사용하며, 산출식에 없는 가중치 재정규화는 하지 않았다. [기상청 실효습도 산출식, 2쪽]({FORMULA}), [지상기상관측지침 2022.12, 3.3.8절]({MANUAL})

시작 4일을 계산하기 위해 2025-08-28~08-31 인제 일자료를 기상청 API로 추가 조회했다. 이 4일은 계산용이며 365일 분석 집계에 포함하지 않았다. 일별 실효습도는 반올림 전 계산값을 임계값과 비교했다. 표에만 소수 둘째 자리까지 표시한다. 정수 반올림을 가정해도 35% 기준 변경 {rounding_diff[35]}일, 25% 기준 변경 {rounding_diff[25]}일로 이번 결과는 동일했다. 공식 운영 시스템의 세부 반올림이나 지역별 특보 판단까지 검증한 것은 아니다.

## 월별 결과

{table(monthly)}

실효습도 35% 이하인 날은 **{len(selected)}일**, 25% 이하인 날은 **{int(daily['기준25이하'].sum())}일**이다. 35% 이하가 2일 이상 연속된 구간은 **{int((qualifying['기준_pct']==35).sum())}개**, 25% 이하가 2일 이상 연속된 구간은 **{int((qualifying['기준_pct']==25).sum())}개**다.

### 기준 이하 날짜

{table(selected[['날짜','평균습도','실효습도_계산값']])}

### 2일 이상 연속 구간

{table(qualifying)}

## 첫 질문에 대한 답

이번 1년의 관측자료에 공식 건조특보의 수치·지속 조건을 사후 적용한 결과는 위 표와 같다. 실제 건조주의보 발령 여부는 판정하지 않는다.

기존 “평균습도 하위 25%, 59.4% 이하” 분석은 공식 기준이 아니므로 본문의 근거에서 제외했다. 그때의 92일과 1월·4월 집중 결론을 공식 기준 결과로 사용하지 않는다. 이전 산출물은 outputs/archive_percentile에 구분 보관했다.

이 결과는 인제 ASOS 한 지점과 1년에 한정된다. 적은 발생 사례만으로 장기적인 계절 집중 경향을 확정하기 어렵다. 실효습도 기준을 넘는 날도 다른 조건에 따라 산불 위험이 있을 수 있다. 실제 특보 발령 여부는 별도 특보 이력으로 확인해야 한다. 강풍 및 건조·강풍 동시 발생 분석은 아직 수행하지 않았다.

## AI 사용 로그

이 과제에서는 ChatGPT/Codex를 데이터 점검, 분석 코드 작성·실행, 공식 자료 검색, 시각화, 결과 해석 및 보고서 문장 작성에 활용했다. 아래 검증은 AI가 도구로 수행한 확인이며, 사용자가 모든 코드와 결과를 독립적으로 검증했다는 뜻은 아니다. 분석 데이터는 기상청 관측자료이며 AI가 관측값을 생성하거나 빈값을 추정해 채우지 않았다.

| 사용 작업 | 사용 이유 | 검증 방법 및 수행 결과 |
| --- | --- | --- |
| CSV 기본정보 점검과 분석용 열 선택 | 반복 점검 시간을 줄이고 누락·중복·빈값을 일관되게 확인하기 위해 | 원본 365행·62열, 날짜 연속성과 중복 여부를 코드로 확인했다. 저장한 365행·6열 표를 읽어 원값과 일치하는지 비교했으며 원본 파일 해시로 변경 여부를 확인했다. |
| 빈값·극단값 처리 기준 검토 | 무조건적인 0 대체나 극단값 삭제를 피하고 대안을 검토하기 위해 | 기상청 ASOS 제공 안내와 대조해 계절적 미제공 항목을 구분했다. 강수량 빈값의 의미는 미확인으로 남겼다. IQR 후보는 오류로 확정하지 않았으며, 4월 23일 일조시간도 북춘천 값으로 대체하지 않았다. |
| 공식 기준 검색과 실효습도 계산 코드 작성 | 습도 지표와 특보 기준을 혼동하지 않고 재현 가능한 계산을 만들기 위해 | 기상청 특보 발표기준 및 실효습도 산출식과 대조했다. 추가 조회한 선행 4일을 포함해 365일을 계산하고, 첫날 계산을 별도의 스칼라 계산과 비교했다. 정수 반올림 가정에 따른 판정 변화가 0일임을 확인했다. |
| 월별 집계·연속 기간·건조와 강풍의 같은 날짜 발생 분석 | 반복 집계와 여러 조건의 비교를 자동화하기 위해 | 전체 분석을 재실행하고 일별·월별·연속 기간의 일수 합계가 맞는지 확인했다. 강풍 임계값과 정확히 같은 값의 포함 여부, 두 풍속 조건 중 하나만 충족하는 OR 조건을 별도 예시로 점검했다. |
| 시계열 그래프 생성 | 관측값 변화와 공식 기준선을 쉽게 비교하기 위해 | 생성한 PNG를 직접 열어 한글, 축 단위, 범례, 기준선, 날짜 표시를 육안 확인했다. 상대습도와 실효습도를 분리하고, 기준 이하 2일 및 최대풍속·최대순간풍속 최댓값 표시를 계산 결과와 대조했다. |
| 해석·문장 정리와 참고자료 검색 | 수치에 근거해 질문에 답하고 해석의 범위를 명확히 하기 위해 | 보고서 수치를 결과 CSV와 대조하고 출처 링크를 기록했다. 관측값의 수치 조건 충족을 실제 특보 발령이나 산불 발생으로 단정하지 않았다. 실제 산불 기록과의 통계적 검증은 수행하지 않았으며 후속 과제로 남겼다. |

**AI 제안의 수정 이력:** 처음 AI가 제안한 “평균습도 하위 25%”는 공식 기준이 아니었다. 사용자의 지적 이후 공식 실효습도 산출식과 건조특보 수치·지속 조건으로 분석을 수정했다. 이전 분위수 결과는 별도 보관하고 현재 결론의 근거에서 제외했다.

**남아 있는 검증 한계:** 실제 기상청 특보 발령 이력, 시간자료의 공식 QC, 산불 발생 기록과의 관계는 검증하지 않았다. 이 보고서는 한 관측소의 1년 관측자료를 이용한 사후 기상 조건 분석이다.

## 재현과 파일

- 실행: `python scripts/analyze_low_humidity.py` (pandas 필요)
- 분석용 표: `data/processed/wind_humidity_daily.csv`
- 일별 계산·조건: `outputs/effective_humidity_daily.csv`
- 월별 결과: `outputs/low_humidity_monthly.csv`
- 기준 이하 날짜: `outputs/low_humidity_days.csv`
- 연속 기간: `outputs/low_humidity_runs.csv`
- 본자료: `data/raw/{SOURCE.name}`
- 계산용 선행자료: `data/raw/{CONTEXT.name}` (2026-09-16 조회)
- 원본 SHA256: `{hashes[SOURCE]}`
- 선행자료 SHA256: `{hashes[CONTEXT]}`

원본 값은 보간·삭제·대체하지 않았다. 추가한 실효습도는 공식 산출식에 따른 분석자 계산값이며 기상청이 직접 제공한 실효습도 관측값은 아니다.
'''
    (ROOT/'REPORT.md').write_text(report,encoding='utf-8')
    pd.testing.assert_frame_equal(pd.read_csv(processed/'wind_humidity_daily.csv'),analysis)
    assert monthly['관측일수'].sum()==365
    for limit in [35,25]:
        assert runs.loc[runs['기준_pct'].eq(limit),'연속일수'].sum()==daily[f'기준{limit}이하'].sum()
    first = sum(.3*.7**i*combined.avgRhm.iloc[4-i] for i in range(5))
    assert abs(first-daily['실효습도_계산값'].iloc[0])<1e-10
    assert abs(effective_humidity(pd.Series([100.]*5)).iloc[-1]-sum(.3*.7**i*100 for i in range(5))) < 1e-10
    for p,h in hashes.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h
    print(selected[['날짜','평균습도','실효습도_계산값']].to_string(index=False))
    print('365일 계산, 원값 보존, 월별·연속구간 합계 검증 완료')


if __name__ == '__main__':
    main()
