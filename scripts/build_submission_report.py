"""기존 분석 결과를 제출용 보고서와 독립 그래프 3개로 정리한다."""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build():
    out = ROOT/'outputs'
    detailed = (ROOT/'REPORT.md').read_text(encoding='utf-8')
    (out/'detailed_analysis.md').write_text(detailed.replace('](outputs/', ']('), encoding='utf-8')
    daily = pd.read_csv(out/'wind_dry_daily.csv')
    monthly = pd.read_csv(out/'low_humidity_monthly.csv')
    wind = pd.read_csv(out/'wind_monthly.csv')
    dates = pd.to_datetime(daily['날짜'])
    assert dates.is_monotonic_increasing and dates.is_unique
    assert dates.tolist() == pd.date_range(dates.min(), dates.max()).tolist()

    def finish(fig, axes, name, time=True):
        for ax in axes:
            ax.grid(axis='y', alpha=.22)
            ax.set_axisbelow(True)
            if time:
                ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.set_xlim(dates.min(), dates.max())
            ax.legend(loc='upper left', ncol=2, fontsize=9)
        fig.tight_layout()
        fig.savefig(out/name, dpi=160, facecolor='white')
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].plot(dates, daily['평균습도'], label='일평균 상대습도', color='#2563eb', lw=1)
    axes[0].plot(dates, daily['최소습도'], label='일최저 상대습도', color='#94a3b8', lw=.8)
    axes[0].set(title='그림 1. 인제의 일별 습도 변화 (2025-09~2026-08)', ylabel='상대습도 (%)', ylim=(0,105))
    axes[1].plot(dates, daily['실효습도_계산값'], label='5일 가중 실효습도', color='#0f766e')
    for limit, color in [(35,'#b45309'), (25,'#dc2626')]:
        axes[1].axhline(limit, color=color, ls='--', label=f'건조특보 수치 기준 {limit}%')
    low = daily['실효습도_계산값'].le(35)
    axes[1].scatter(dates[low], daily.loc[low,'실효습도_계산값'], color='#dc2626', zorder=4)
    axes[1].set(ylabel='실효습도 (%)', ylim=(0,90), xlabel='날짜 (월별 눈금)')
    finish(fig, axes, 'humidity_timeseries.png')

    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    for ax, col, limits, upper in [(axes[0],'최대풍속',[14,17,21,24],28), (axes[1],'최대순간풍속',[20,25,26,30],35)]:
        ax.plot(dates, daily[col], label=col, color='#334155', lw=1)
        for limit, label, color in zip(limits, ['육상 주의보','산지 주의보','육상 경보','산지 경보'], ['#b45309','#7c3aed','#dc2626','#9f1239']):
            ax.axhline(limit, ls='--', lw=.8, color=color, label=f'{label} {limit} m/s')
        idx = daily[col].idxmax()
        ax.annotate(f"최대 {daily.loc[idx,col]:.1f} m/s ({dates[idx]:%m/%d})", xy=(dates[idx],daily.loc[idx,col]), xytext=(10,10), textcoords='offset points', fontsize=9)
        ax.set(ylabel='풍속 (m/s)', ylim=(0,upper))
    axes[0].set_title('그림 2. 인제의 일별 바람과 강풍특보 수치 기준')
    axes[1].set_xlabel('날짜 (월별 눈금)')
    finish(fig, axes, 'wind_timeseries.png')

    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    x = list(range(len(monthly)))
    axes[0].bar(x, monthly['평균실효습도'], color='#0f766e', label='월평균 실효습도')
    axes[1].bar(x, wind['평균풍속_월평균'], color='#334155', label='일평균풍속의 월평균')
    for ax, values, fmt in [(axes[0],monthly['평균실효습도'],'.2f'), (axes[1],wind['평균풍속_월평균'],'.2f')]:
        ax.set_xticks(x, monthly['월'], rotation=30, ha='right')
        for i, value in enumerate(values):
            ax.text(i, value, format(value,fmt), ha='center', va='bottom', fontsize=9)
    axes[0].set(title='그림 3. 월별 습도와 평균풍속 비교', ylabel='실효습도 (%)', ylim=(0,85))
    axes[1].set(ylabel='평균풍속 (m/s)', ylim=(0,2.3), xlabel='월')
    finish(fig, axes, 'monthly_weather.png', time=False)

    ai = detailed.split('## AI 사용 로그\n',1)[1].split('## 재현과 파일',1)[0].strip()
    methods = detailed.split('## 공식 기준과 적용 방법\n',1)[1].split('## 월별 결과',1)[0].strip()
    literature = (ROOT/'docs/literature_review.md').read_text(encoding='utf-8')
    literature = literature[literature.index('### 확인한 국내 논문 3편'):literature.index('### 인제 자료와 연결해 말할 수 있는 내용')]
    min_month = monthly.loc[monthly['평균실효습도'].idxmin()]
    max_month = monthly.loc[monthly['평균실효습도'].idxmax()]
    difference = max_month['평균실효습도']-min_month['평균실효습도']
    report = f'''# 인제의 습도·풍속 시계열 분석: 국내 산불 연구를 바탕으로

## 1. 분석 주제 및 선정 이유

산불 관련 기상요인인 습도와 풍속이 인제에서 1년 동안 어떻게 변했는지 분석한다. 국내 선행연구는 기상요인과 산불 발생·대형화의 관련성을 다루고 있어 두 요인을 선정했다. 이번 과제는 기상 변화와 특보 수치 조건을 탐색하는 분석이며, 실제 산불 발생을 예측하거나 검증한 연구는 아니다.

## 2. 분석 질문

1. 습도는 월별로 어떻게 달라지며, 건조특보의 수치·지속 조건에 해당하는 구간은 언제인가?
2. 평균적인 바람이 강한 달과 가장 큰 순간풍속이 나타난 시기는 같은가?
3. 건조와 강풍특보 수치 기준이 같은 날짜에 충족되는가? 이 결과를 국내 산불 연구와 연결해 어디까지 해석할 수 있는가?

## 3. 데이터 설명 및 분석 방법

- 출처: [기상청 기상자료개방포털 ASOS](https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36)의 인제 관측소(211) 일자료.
- 분석 기간: 2025-09-01~2026-08-31, **365일**. 원본 365행·62열, 분석용 표 365행·6열.
- 핵심 변수: 날짜, 평균풍속, 최대풍속, 최대순간풍속, 평균습도, 최소습도. 단위는 m/s와 %.
- 날짜 점검: 오름차순, 중복 0건, 누락 0일. 핵심 변수 결측 0건.
- 처리 기준: 핵심 변수는 원값을 사용했다. 강수량 빈값 219개의 의미가 확인되지 않아 강수량 분석에서 제외했다. 전 기간 결측인 비핵심 변수도 제외했다. IQR 후보는 오류로 단정하지 않고 보존했다. 4월 23일 일조시간은 인근 관측소 값으로 대체하지 않았다.

시계열 분석에는 **① 5일 가중 실효습도 계산 ② 월별 집계(평균·최대·기준 충족 일수) ③ 기준 이하 연속 구간 탐색**을 적용했다. 계산용 선행 4일(2025-08-28~08-31)은 본 분석의 365일 집계에 포함하지 않았다.

{methods}

강풍은 일최대풍속 또는 일최대순간풍속 중 하나가 기준 이상인지 비교했다. 육상 주의보는 14 또는 20 m/s, 산지 주의보는 17 또는 25 m/s, 육상 경보는 21 또는 26 m/s, 산지 경보는 24 또는 30 m/s다. 이는 실제 발령 이력이 아닌 사후 수치 비교다. 인제군 전체를 한 관측소로 대표하거나 산지로 일괄 분류하지 않는다.

## 4. 분석 결과 및 시각화

### 4.1 일별 습도와 건조 구간

![그림 1. 일별 상대습도와 실효습도](outputs/humidity_timeseries.png)

실효습도 35% 이하인 날은 2026-02-23(33.92%)과 02-24(34.19%)로 **2일 연속 1구간**이었다. 25% 이하는 0일이었다. 35%·25%는 상대습도 패널에 직접 적용하지 않았다.

### 4.2 일별 바람과 기준선

![그림 2. 일별 풍속과 강풍특보 수치 기준](outputs/wind_timeseries.png)

일최대풍속의 기간 최댓값은 2026-01-10의 8.1 m/s, 최대순간풍속의 최댓값은 2026-01-11의 19.3 m/s다. 육상 주의보 수치 조건에 도달한 날은 0일이며 더 높은 기준도 0일이었다. 따라서 건조와 강풍 기준의 같은 날짜 충족도 0일이다. 이는 산불 위험이 없었다거나 습도와 풍속이 무관하다는 뜻이 아니다.

### 4.3 월별 변화

![그림 3. 월별 실효습도와 평균풍속](outputs/monthly_weather.png)

월평균 실효습도는 {min_month['월']}에 {min_month['평균실효습도']:.2f}%로 가장 낮고, {max_month['월']}에 {max_month['평균실효습도']:.2f}%로 가장 높았다. 월평균 풍속은 2026년 4월 1.76 m/s로 가장 높았다. 월평균으로 개별 날짜의 특보 조건을 판정하지 않는다.

**시각화 선택 근거:** 일별 그래프는 2일 연속 건조와 짧은 바람 피크를 보존하기 위해, 월별 그래프는 연중 분포를 비교하기 위해 선택했다. 날짜 눈금은 월별이지만 그림 1·2의 값은 일별이다. 습도와 풍속은 단위가 달라 축을 분리했다. 세로축은 0부터 시작하며 그림 2는 기준선을 포함해 변화가 작게 보일 수 있으므로 최댓값 표기를 함께 확인한다. 그림 3의 평균풍속 축은 0~2.3 m/s로 설정했으며 그림 2의 극값과 같은 변수로 비교하지 않는다.

## 5. 인사이트

### 5.1 건조함은 임계값 충족 일수와 월평균을 함께 봐야 한다

- **관찰(Fact):** 그림 1의 실효습도 35% 이하 구간은 2월의 2일뿐이지만, 그림 3의 월평균은 4월이 최저였다. 4월과 9월의 차이는 {difference:.2f}%p다.
- **가능한 설명(Why):** 임계값 분석은 짧은 극단 구간을, 월평균은 한 달의 전반적 수준을 나타내므로 순위가 다를 수 있다. 국내 연구의 봄철 산불 집중은 비교 배경이며 이 기상 차이의 원인이나 인제 산불의 증거는 아니다.
- **후속 행동(Action):** 두 지표를 함께 보고, 다년 자료로 같은 계절 차이가 반복되는지 확인한다.

### 5.2 평균적인 바람과 순간적인 강한 바람의 시기는 다르다

- **관찰(Fact):** 그림 3의 월평균 풍속은 4월 1.76 m/s가 최대지만, 그림 2의 최대순간풍속은 1월 11일 19.3 m/s다.
- **가능한 설명(Why):** 월평균은 반복되는 바람의 수준을, 일최대순간풍속은 짧은 피크를 반영한다. 특정 기압계가 원인이었는지는 이번 분석으로 확인하지 않았다.
- **후속 행동(Action):** 산불 확산을 분석할 때는 발화·확산 시각의 시간자료와 피해면적을 연결하고, 평균풍속 모형에 순간풍속을 대신 넣지 않는다.

### 5.3 기준 동시 충족 0일은 산불 위험 부재의 증거가 아니다

- **관찰(Fact):** 그림 1에서 건조 조건은 2일 있었지만, 그림 2에서 강풍특보 수치 조건은 365일 모두 미충족이었다. 교집합도 0일이다.
- **가능한 설명(Why):** 강풍 조건 자체가 한 번도 충족되지 않아 교집합이 없는 것이다. 특보 기준의 교집합은 두 연속 변수의 상관관계나 산불 발생 확률을 평가하는 방법이 아니다.
- **후속 행동(Action):** 실제 산불 발생일·비발생일을 확보해 비교한다. 습도·풍속 자체의 관계가 질문이라면 산점도·상관계수와 계절별 비교를 별도로 수행한다.

### 5.4 해석을 뒷받침하는 국내 선행연구

{literature}

## 6. 결론 및 한계점

이번 인제 365일 자료에서는 실효습도 35% 이하가 2일 연속 나타났으며, 월평균 실효습도는 4월에 가장 낮았다. 평균풍속의 월평균 최대는 4월, 최대순간풍속의 기간 최대는 1월로 서로 달랐다. 강풍특보 수치 기준 충족과 건조·강풍의 같은 날짜 충족은 모두 0일이었다.

**현재 결론은 기상 조건의 변화에 한정한다.** 실제 산불 기록이 없어 인제 산불의 집중 시기·발생 확률·기상과의 인과관계는 검증하지 못했다. 단일 관측소의 1년 자료로 장기 계절성이나 군 전체 산지의 위험을 일반화할 수 없다. 지형·연료·인위적 발화·진화 조건을 반영하지 않았으며 일자료로 같은 시각의 건조와 바람을 확인할 수 없다. 국내 논문의 전국·장기 결과가 이 한계를 대신 해결하지는 않는다.

후속 분석은 다년 기상자료와 동일 지역의 산불 기록 확보부터 시작한다. 총괄 판단 원칙은 [에이전트 판단 지침](docs/agent_decision_guidelines.md)에 정리했다.

## 7. AI 사용 로그

{ai}

추가로 국내 논문 검색·초록 비교와 제출용 보고서 구조 정리에 AI를 활용했다. 저자·연도·DOI와 저자 초록을 대조했으며 논문 전체 재현을 수행한 것으로 표현하지 않았다. 독립 그래프 3개의 수치는 기존 일별·월별 산출물에서 가져왔다.

## 8. 재현 및 상세 자료

- 전체 보고서·그래프 생성: `python scripts/plot_weather_timeseries.py` (pandas, matplotlib 필요).
- 원본: `data/raw/inje_asos_211_daily_20250901_20260831.csv`.
- 분석용 표: `data/processed/wind_humidity_daily.csv`.
- 계산·집계: `outputs/wind_dry_daily.csv`, `outputs/low_humidity_monthly.csv`, `outputs/wind_monthly.csv`.
- [상세 분석 기록](outputs/detailed_analysis.md), [국내 논문 검토](docs/literature_review.md).

습도 또는 강풍 분석 스크립트만 실행하면 중간 보고서가 생성된다. 제출용 보고서는 위 전체 실행 명령으로 생성한다.
'''
    assert report.count('![그림') == 3
    (ROOT/'REPORT.md').write_text(report, encoding='utf-8')
    print('제출용 REPORT.md 및 독립 그래프 3개 저장 완료')
