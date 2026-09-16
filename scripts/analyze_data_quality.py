"""기상청 ASOS 제공 안내를 참고해 빈값과 검토 대상을 분리한다."""
from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/raw/inje_asos_211_daily_20250901_20260831.csv'
URL = 'https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36&tabNo=2'
CORE = ['avgTa', 'minTa', 'maxTa', 'avgWs', 'maxWs', 'maxInsWs', 'avgRhm', 'minRhm']


def main():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    df = pd.read_csv(SOURCE, encoding='utf-8-sig')
    dates = pd.to_datetime(df.tm, format='%Y-%m-%d', errors='coerce')
    winter = dates.dt.month.isin([11, 12, 1, 2, 3])
    summer = dates.dt.month.between(4, 10)
    lines = ['인제 ASOS 데이터 품질 재점검', '', f'원본: {SOURCE.name}',
             f'원본 SHA256: {before}', f'크기: {len(df)}행 × {len(df.columns)}열',
             f'기간: {dates.min().date()} ~ {dates.max().date()}', '',
             '1. 공식 안내와 이번 점검의 구분',
             f'공식 출처: {URL}',
             '공식 안내 확인일: 2026-09-16',
             '공식: 10분·1시간 최다강수량은 4~10월에만 제공된다.',
             '공식: 시간·분 자료의 일부 요소에 QC FLAG(0 정상, 1 오류, 9 결측)를 제공한다.',
             '현재 일자료 CSV에는 QC FLAG가 없다. 시간·분 자료를 조회한 결과가 아니며 공식 QC 통과를 주장하지 않는다.',
             '공식 안내의 겨울철 3시간 간격 강수 제공 설명을 일강수량 빈값의 원인으로 적용하지 않는다.',
             '아래 범위·대소관계 점검 및 IQR은 분석자가 설정한 보조 점검이며 기상청 공식 QC 알고리즘이 아니다.', '',
             '2. 빈값 재분류']
    inventory = []
    for c in df.columns:
        n = int(df[c].isna().sum())
        seasonal = c in ['hr1MaxRn', 'mi10MaxRn']
        off = int((df[c].isna() & winter).sum()) if seasonal else 0
        note = ('공식 미제공 기간과 일치하는 빈값 및 제공기간 내 원인 미확인 빈값' if seasonal else
                '전 기간 빈값: 관측/제공 여부 미확인' if n == len(df) else
                '빈값 원인 미확인' if n else '빈값 없음')
        inventory.append({'column': c, 'empty_count': n, 'off_season_empty': off,
                          'unresolved_empty': n-off, 'interpretation': note})
    lines.append(f'핵심 기온·풍속·습도 8개 컬럼 빈값 합계: {int(df[CORE].isna().sum().sum())}개')
    for c in ['hr1MaxRn', 'mi10MaxRn']:
        lines.append(f'{c}: 전체 빈값 {df[c].isna().sum()}개 / 11~3월 빈값 {(df[c].isna() & winter).sum()}개 / 4~10월 빈값 {(df[c].isna() & summer).sum()}개 / 미제공 기간에 실제 값 존재 {(df[c].notna() & winter).sum()}개')
        for i in df.index[df[c].notna() & winter]:
            lines.append(f'제공기간 안내와 다른 사례: {df.at[i,"tm"]}, {c}={df.at[i,c]} (원자료 확인 필요, 삭제하지 않음)')
    lines += ['11~3월의 위 두 강수량 항목 빈값은 공식 미제공 기간과 일치하므로 일반적인 관측 실패로 세지 않는다.',
              '4~10월 빈값의 원인은 아직 확정할 수 없다. 최다강수 발생시각 컬럼에는 동일 규칙을 자동 적용하지 않는다.',
              f'sumRn: 빈값 {df.sumRn.isna().sum()}개, 0으로 기록 {int(df.sumRn.eq(0).sum())}개, 양수 {int(df.sumRn.gt(0).sum())}개.',
              'sumRn 빈값은 무강수 또는 관측 누락으로 확정하지 않는다. 0 대체·보간·무강수일 계산을 보류한다.',
              'sumSsHr 빈값 날짜: ' + ', '.join(df.loc[df.sumSsHr.isna(), 'tm']),
              f'전부 빈값인 컬럼 {int(df.isna().all().sum())}개: ' + ', '.join(df.columns[df.isna().all()]),
              '이들 컬럼은 원본에 보존하고 이번 저습도·강풍 분석의 입력에서 제외한다.', '',
              '3. 보조 범위·관계 점검']
    checks = {
        '습도 0~100% 범위 이탈': ((df[['avgRhm','minRhm']] < 0) | (df[['avgRhm','minRhm']] > 100)).any(axis=1),
        '풍속·일강수량 음수': (df[['avgWs','maxWs','maxInsWs','sumRn']] < 0).any(axis=1),
        '최저≤평균≤최고 기온 관계 위반': (df.minTa > df.avgTa) | (df.avgTa > df.maxTa),
        '평균≤최대≤최대순간 풍속 관계 위반': (df.avgWs > df.maxWs) | (df.maxWs > df.maxInsWs),
        '최저≤평균 습도 관계 위반': df.minRhm > df.avgRhm,
    }
    for name, mask in checks.items():
        lines.append(f'{name}: {int(mask.sum())}건')
    lines += [f'중복 행: {df.duplicated().sum()}개', f'날짜 변환 실패/빈값: {dates.isna().sum()}개',
              f'중복 유효 날짜: {dates.dropna().duplicated().sum()}개',
              f'기간 내 누락 날짜: {len(pd.date_range(dates.min(), dates.max()).difference(dates.dropna()))}개',
              '검사는 존재하는 값에 대해서만 적용한다. 위반 0건은 원자료의 모든 오류가 없다는 뜻이 아니다.', '',
              '4. 통계적 검토 후보 (오류 확정 아님)',
              '연간 전체의 유효값에서 Q1−1.5×IQR 미만 또는 Q3+1.5×IQR 초과를 표시한다.',
              '계절성을 보정하지 않은 탐색용 기준이다. 강수량은 빈값 제외 분포이므로 해석에 제한이 있다.']
    candidates = []
    for c in CORE + ['sumRn']:
        s = df[c].dropna()
        q1, q3 = s.quantile([.25, .75])
        low, high = q1-1.5*(q3-q1), q3+1.5*(q3-q1)
        mask = (df[c] < low) | (df[c] > high)
        lines.append(f'{c}: 범위 {s.min():g}~{s.max():g}, IQR 경계 {low:.3f}~{high:.3f}, 후보 {int(mask.sum())}개')
        for i in df.index[mask]:
            candidates.append({'date': df.at[i,'tm'], 'column': c, 'value': df.at[i,c],
                               'lower_bound': low, 'upper_bound': high,
                               'decision': '유지·검토 대상, 오류 미확정'})
    lines += ['', '5. 이번 분석의 처리 방침',
              '저습도·강풍의 핵심 8개 컬럼은 365일 모두 빈값 없이 사용할 수 있다. 공식 QC 검증 완료를 뜻하지 않는다.',
              '통계적 극단값은 보존한다. 강풍·건조 사례가 분석 목적이므로 IQR 기준으로 삭제하거나 평균 대체하지 않는다.',
              'sumRn 빈값의 원인 확인 전에는 연간 강수 총량·평균과 무강수 지속일수를 확정하지 않는다.',
              '일조시간을 분석한다면 해당 빈값 날짜를 명시하고 유효일 기준으로 분석한다.',
              '미확인 빈값은 관측/제공 여부나 원자료를 추가 확인한다. 의심되는 풍속·습도 값은 시간자료 및 QC 정보를 확인한다.',
              '낮은 습도·강한 바람을 정하는 분석 임계값은 데이터 오류 판정과 별도로 정한다.',
              '원본의 값 삭제, 0 대체, 보간은 수행하지 않았다.']
    out = ROOT / 'outputs'
    out.mkdir(exist_ok=True)
    (out/'data_quality_review.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8-sig')
    pd.DataFrame(inventory).to_csv(out/'missing_value_review.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(candidates, columns=['date','column','value','lower_bound','upper_bound','decision']).to_csv(out/'outlier_review_candidates.csv', index=False, encoding='utf-8-sig')
    assert before == hashlib.sha256(SOURCE.read_bytes()).hexdigest(), '원본 변경 감지'
    print('\n'.join(lines))
    print(f'\n결과 저장: {out}')


if __name__ == '__main__':
    main()
