"""인제 습도·풍속 시계열과 공식 기준선을 그리고 전체 보고서를 갱신한다."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'outputs/.matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import pandas as pd
import analyze_wind_dry_overlap as analysis


def main():
    analysis.main()
    daily = pd.read_csv(ROOT/'outputs/wind_dry_daily.csv')
    dates = pd.to_datetime(daily['날짜'])
    assert len(daily)==365 and dates.is_unique
    font_path = Path('C:/Windows/Fonts/malgun.ttf')
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        plt.rcParams['font.family'] = ['NanumGothic','Noto Sans CJK KR','DejaVu Sans']
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':10,'axes.titlesize':13,
                         'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(4,1,figsize=(14,16),sharex=True)
    fig.subplots_adjust(left=.08,right=.98,top=.91,bottom=.09,hspace=.38)
    fig.suptitle('인제의 습도·풍속 변화와 공식 기준선',x=.08,y=.975,ha='left',fontsize=22,fontweight='bold')
    fig.text(.08,.946,'인제 ASOS 211  |  2025.09.01–2026.08.31  |  365일 관측자료',fontsize=12,color='#475569')
    colors = ['#b45309','#dc2626','#7c3aed','#9f1239']
    axes[0].plot(dates,daily['평균습도'],color='#2563eb',lw=1.2,label='일평균 상대습도')
    axes[0].plot(dates,daily['최소습도'],color='#94a3b8',lw=.9,alpha=.9,label='일최저 상대습도')
    axes[0].set(title='1. 상대습도 — 관측값 (건조특보 기준을 직접 적용하지 않음)',ylabel='상대습도 (%)',ylim=(0,105))
    axes[1].plot(dates,daily['실효습도_계산값'],color='#0f766e',lw=1.5,label='실효습도 (5일 가중 계산값)')
    for limit,color,label in [(35,colors[0],'주의보 수치 기준 35%'),(25,colors[1],'경보 수치 기준 25%')]:
        axes[1].axhline(limit,color=color,ls='--',lw=1.2,label=label)
    low = daily['실효습도_계산값'].le(35)
    axes[1].scatter(dates[low],daily.loc[low,'실효습도_계산값'],color=colors[1],s=30,zorder=5)
    if low.any():
        idx = daily.loc[low,'실효습도_계산값'].idxmin()
        axes[1].annotate('2월 23–24일: 35% 이하 연속 2일',
            xy=(dates[idx],daily.loc[idx,'실효습도_계산값']),xytext=(28,32),textcoords='offset points',
            arrowprops={'arrowstyle':'->','color':'#475569'},fontsize=10,
            bbox={'facecolor':'white','edgecolor':'#cbd5e1','boxstyle':'round,pad=.4'})
    axes[1].set(title='2. 실효습도 — 건조특보는 기준 이하가 2일 이상 지속될 것으로 예상될 때',ylabel='실효습도 (%)',ylim=(0,90))
    for ax,col,limits,title,upper in [
        (axes[2],'최대풍속',[14,17,21,24],'3. 일최대풍속과 강풍 기준',28),
        (axes[3],'최대순간풍속',[20,25,26,30],'4. 일최대순간풍속과 강풍 기준',35),
    ]:
        ax.plot(dates,daily[col],color='#334155',lw=1.2,label=col)
        for limit,color,label,style in zip(limits,colors,['육상 주의보','산지 주의보','육상 경보','산지 경보'],['--',':','-.','--']):
            ax.axhline(limit,color=color,ls=style,lw=1.1,label=f'{label} {limit}m/s')
        idx = daily[col].idxmax()
        ax.scatter([dates[idx]],[daily.loc[idx,col]],color='#2563eb',s=25,zorder=5)
        ax.annotate(f"기간 최댓값 {daily.loc[idx,col]:.1f}m/s ({dates[idx]:%m/%d})",
                    xy=(dates[idx],daily.loc[idx,col]),xytext=(12,12),textcoords='offset points',fontsize=9)
        ax.set(title=title,ylabel='풍속 (m/s)',ylim=(0,upper))
    for ax in axes:
        ax.grid(axis='y',color='#e2e8f0',lw=.7)
        ax.set_axisbelow(True)
        ax.set_xlim(dates.iloc[0],dates.iloc[-1])
        ax.legend(loc='upper left',bbox_to_anchor=(0,1.015),ncol=3,fontsize=8.5,frameon=False)
        ax.tick_params(axis='x',labelbottom=True)
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.text(.08,.047,'기준선은 공식 특보의 수치 조건과 사후 비교한 것입니다. 실제 특보 발령·산불 발생 여부를 뜻하지 않습니다.',fontsize=10,color='#475569')
    fig.text(.08,.029,'강풍은 최대풍속 또는 최대순간풍속 중 하나가 기준 이상인 날을 비교했습니다. 육상·산지 기준을 함께 표시했습니다.',fontsize=10,color='#475569')
    fig.text(.08,.011,'출처: 기상청 ASOS 일자료 · 기상청 특보 발표기준 · 강원지방기상청 실효습도 산출식 (REPORT.md 참조)',fontsize=9,color='#64748b')
    out = ROOT/'outputs'
    fig.savefig(out/'weather_timeseries.png',dpi=160,facecolor='white')
    fig.savefig(out/'weather_timeseries.svg',facecolor='white')
    plt.close(fig)
    report = ROOT/'REPORT.md'
    report.write_text(report.read_text(encoding='utf-8')+'''

## 습도·풍속 시계열 그래프

![인제의 습도·풍속 변화와 공식 기준선](outputs/weather_timeseries.png)

상대습도 관측값과 계산한 실효습도를 별도 패널로 구분했다. 35%·25% 기준선은 실효습도에만 적용했다. 최대풍속과 최대순간풍속은 서로 다른 기준선을 사용한다. 건조특보의 지속·예상 조건과 강풍의 OR 조건은 앞의 분석 방법을 따른다.

그래프에서는 겨울·봄의 실효습도가 여름·초가을보다 대체로 낮게 나타난다. 기준선 아래에 해당하는 구간은 2026-02-23~02-24이며, 두 풍속 계열은 모두 육상 주의보 기준선에 도달하지 않는다. 한 관측소의 1년 변화이므로 장기 기후 특성이나 실제 특보·산불 발생으로 일반화하지 않는다.

### 시간 축·스케일·집계 단위 선택

- **시간 축:** 2025-09-01~2026-08-31의 365일을 날짜 오름차순으로 표시했다. 날짜 중복과 누락은 모두 0건이다. 가로축 눈금은 월 단위지만, 선을 구성하는 관측값은 일별 값이다.
- **스케일:** 습도(%)와 풍속(m/s)을 별도 패널로 나누고, 세로축은 0부터 표시했다. 상대습도는 0~105%, 실효습도는 0~90%, 최대풍속은 0~28 m/s, 최대순간풍속은 0~35 m/s로 설정해 관측값과 기준선을 함께 볼 수 있게 했다. 이 때문에 풍속 변화가 상대적으로 작아 보일 수 있으므로 실제 범위와 최댓값 표기를 함께 확인한다. 최대풍속 범위는 1.2~8.1 m/s, 최대순간풍속 범위는 2.1~19.3 m/s이다. 패널마다 축 범위가 다르므로 선의 기울기만으로 변수 간 변화량을 비교하지 않는다.
- **집계 단위:** 일별 그래프는 건조 조건의 2일 연속 여부와 짧은 강풍 피크를 보존하기 위해 선택했다. 월별 표는 연중 어느 시기에 조건 충족일이 집중되는지 비교하기 위해 사용하며, 월별 일수가 다르므로 일수와 비율을 함께 해석한다. 월평균으로는 개별 날짜의 기준 충족 여부를 판정하지 않는다. 이번 질문에는 일별 지속성과 월별 분포가 직접 대응하므로 주별 집계는 추가하지 않았다.

그래프까지 포함한 전체 재실행: `python scripts/plot_weather_timeseries.py`
필요 패키지: `python -m pip install pandas matplotlib`
그림 파일: `outputs/weather_timeseries.png`, `outputs/weather_timeseries.svg`.
이 명령은 습도·강풍 분석을 재실행하고 보고서에 그래프를 추가한다.
''',encoding='utf-8')
    print('시계열 그래프 PNG·SVG 및 REPORT.md 저장 완료')


if __name__ == '__main__':
    main()
