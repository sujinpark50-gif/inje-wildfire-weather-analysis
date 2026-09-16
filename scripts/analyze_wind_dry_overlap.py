"""공식 강풍 수치 기준과 건조·강풍의 같은 날짜 발생을 사후 비교한다."""
from pathlib import Path
import pandas as pd
import analyze_low_humidity as humidity

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    '육상_주의보': (14,20), '산지_주의보': (17,25),
    '육상_경보': (21,26), '산지_경보': (24,30),
}


def wind_condition(max_wind, gust, wind_limit, gust_limit):
    return (max_wind >= wind_limit) | (gust >= gust_limit)


def main():
    # 일별 건조 분석부터 다시 계산해 입력 및 보고서의 최신 상태를 보장한다.
    humidity.main()
    out = ROOT/'outputs'
    daily = pd.read_csv(out/'effective_humidity_daily.csv')
    assert len(daily)==365 and daily['날짜'].is_unique
    assert not daily[['최대풍속','최대순간풍속','실효습도_계산값']].isna().any().any()
    summaries = []
    for label,(wind_limit,gust_limit) in RULES.items():
        flag = wind_condition(daily['최대풍속'],daily['최대순간풍속'],wind_limit,gust_limit)
        daily[label+'_수치충족'] = flag
        daily[label+'_건조동일일'] = flag & daily['기준35이하']
        daily[label+'_건조연속구간중'] = flag & daily['기준35_2일이상구간']
        summaries.append({'비교기준':label,'풍속_mps':wind_limit,'순간풍속_mps':gust_limit,
                          '수치충족일수':int(flag.sum()),
                          '실효습도35이하와동일일':int(daily[label+'_건조동일일'].sum()),
                          '건조2일이상구간중':int(daily[label+'_건조연속구간중'].sum())})
    summary = pd.DataFrame(summaries)
    daily['월'] = daily['날짜'].str[:7]
    monthly = daily.groupby('월',as_index=False).agg(
        관측일수=('날짜','size'),평균풍속_월평균=('평균풍속','mean'),
        최대풍속_월최대=('최대풍속','max'),최대순간풍속_월최대=('최대순간풍속','max'),
        실효습도35이하일수=('기준35이하','sum'))
    for label in RULES:
        counts = daily.groupby('월')[[label+'_수치충족',label+'_건조동일일']].sum()
        for c in counts:
            monthly[c+'일수'] = monthly['월'].map(counts[c])
    cols = ['날짜','평균풍속','최대풍속','최대순간풍속','평균습도','실효습도_계산값','육상_주의보_수치충족']
    strongest = daily.sort_values(['최대순간풍속','날짜'],ascending=[False,True]).head(10)[cols]
    dry = daily.loc[daily['기준35이하'],cols]
    for name,frame in [('wind_dry_daily.csv',daily.drop(columns='월')),('wind_monthly.csv',monthly),
                       ('wind_threshold_summary.csv',summary),('wind_top10_days.csv',strongest),
                       ('dry_days_wind_comparison.csv',dry)]:
        frame.to_csv(out/name,index=False,encoding='utf-8-sig')
    brief_monthly = monthly[['월','관측일수','평균풍속_월평균','최대풍속_월최대','최대순간풍속_월최대','실효습도35이하일수']]
    report_path = ROOT/'REPORT.md'
    report = report_path.read_text(encoding='utf-8').replace('강풍 및 건조·강풍 동시 발생 분석은 아직 수행하지 않았다.','강풍 및 건조·강풍의 같은 날짜 발생 비교는 아래에 이어서 제시한다.')
    section = f'''

## 두 번째 질문: 강풍 기간은 언제 집중되는가?

기상청의 강풍특보 기준을 아래와 같이 적용했다. 풍속 또는 순간풍속 중 하나만 기준 이상이어도 수치 충족으로 센다. 단위는 m/s다. [기상청 특보 발표기준]({humidity.STANDARD}) (확인: 2026-09-16)

{humidity.table(summary)}

기준 비교에는 일평균풍속이 아니라 일최대풍속(maxWs)과 일최대순간풍속(maxInsWs)을 사용했다. 이는 일자료의 극값과 특보 수치 기준을 대조하는 사후 분석이다. 예보에 기반한 실제 특보 발령 여부를 판정하지 않는다. 인제군 전체를 산지 또는 일반 육상으로 단정하지 않고 양쪽 기준을 병렬 제시했다. 한 관측소의 결과를 군 전체나 주변 산지에 적용하지 않는다.

365일 중 최대풍속의 최댓값은 **{daily['최대풍속'].max():.1f}m/s**, 최대순간풍속의 최댓값은 **{daily['최대순간풍속'].max():.1f}m/s**였다. 육상 주의보 수치 기준(14 또는 20m/s)에 도달한 날은 **{int(daily['육상_주의보_수치충족'].sum())}일**이다. 더 높은 산지·경보 기준도 위 표와 같다. 따라서 이 자료에서는 공식 강풍 수치 기준에 해당하는 날의 계절적 집중 시기를 찾을 수 없다. “그해 인제군에 강풍특보가 없었다”거나 “바람에 의한 위험이 없었다”는 의미는 아니다.

### 월별 바람의 크기

{humidity.table(brief_monthly)}

이 표는 기준 미만의 바람도 포함한 기술통계다. 기준을 낮춰 강풍 사례를 만들지 않았다. 평균풍속의 월평균과 월중 최대순간풍속은 서로 다른 특성을 나타낸다.

### 최대순간풍속 상위 10일

{humidity.table(strongest)}

상위 10일은 값의 순위일 뿐 별도의 강풍 판정 기준이 아니다.

## 세 번째 질문: 건조와 강풍이 같은 날 나타났는가?

실효습도 35% 이하와 강풍 수치 기준 충족이 같은 날짜에 나타나는지를 비교했다. 건조 2일 이상 연속 구간에 포함된 날짜와의 교집합도 따로 계산했다. 일자료로는 하루 안에서 같은 시각에 두 조건이 겹쳤는지 알 수 없다.

{humidity.table(dry)}

육상 주의보 수치 기준의 강풍 자체가 **{int(daily['육상_주의보_수치충족'].sum())}일**이므로, 실효습도 35% 이하와 같은 날 충족한 경우도 **{int(daily['육상_주의보_건조동일일'].sum())}일**이다. 산지 및 경보 기준의 같은 날짜 발생도 요약 표에 제시했다. 건조 전후의 강풍은 같은 날짜 발생에 포함하지 않는다.

{(ROOT/'docs/literature_review.md').read_text(encoding='utf-8')}
## 현재 분석의 결론과 후속 과제

이 1년의 인제 ASOS 관측값에서는 실효습도 35% 이하가 2일 연속 나타난 구간이 확인됐으나 공식 강풍 수치 기준에 도달한 날은 없었다. 건조·강풍의 같은 날짜 기준 충족도 없었다. 이 결과 자체를 그대로 보고하며 기준을 바꾸어 사례를 늘리지 않는다.

실제 산불 발생 기록과의 비교는 사용자 결정에 따라 후속 과제로 남겼다. 국내 선행연구는 습도·풍속을 산불 관련 변수로 검토할 근거를 제공하지만, 현재 보고서의 기상 조건 분석이 인제의 산불 발생률·인과관계·예측 정확도를 검증한 것은 아니다. 습도와 풍속이 무관하거나 강풍특보 기준 미만에서 산불 위험이 없다는 결론도 내리지 않는다. 후속 검증에는 인제의 날짜별 산불 기록과 더 긴 기간의 관측자료가 필요하다.

### 전체 분석 재실행 및 결과

- 전체 실행: `python scripts/analyze_wind_dry_overlap.py` (습도 분석도 먼저 재실행한다)
- 일별 판정: `outputs/wind_dry_daily.csv`
- 월별 바람·같은 날짜 발생: `outputs/wind_monthly.csv`
- 네 가지 공식 수치 기준 비교: `outputs/wind_threshold_summary.csv`
- 최대순간풍속 상위 날짜: `outputs/wind_top10_days.csv`
- 건조한 날의 바람: `outputs/dry_days_wind_comparison.csv`

`analyze_low_humidity.py`만 실행하면 보고서가 습도 부분으로 재생성되므로 전체 보고서에는 위 전체 실행 명령을 사용한다.
'''
    report_path.write_text(report+section,encoding='utf-8')
    assert monthly['관측일수'].sum()==len(daily)
    for label in RULES:
        assert monthly[label+'_수치충족일수'].sum()==daily[label+'_수치충족'].sum()
        assert (daily[label+'_건조동일일'] <= daily[label+'_수치충족']).all()
    # 경계값 포함과 OR 조건을 실제 데이터에 사례가 없더라도 검증한다.
    a = pd.Series([14,13.9,0,0])
    b = pd.Series([0,19.9,20,19.9])
    assert wind_condition(a,b,14,20).tolist()==[True,False,True,False]
    print(summary.to_string(index=False))
    print(dry.to_string(index=False))
    print('강풍·건조 교집합 분석과 경계 조건 검증 완료')


if __name__ == '__main__':
    main()
