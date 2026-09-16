# 인제 일조시간 빈값 처리 결정

2026-04-23 인제(211)의 일조시간(sumSsHr)은 빈값으로 유지한다.
북춘천(93)의 관측값은 참고용이며, 인제 값으로 대체하거나 추정 보간하지 않는다.

일조시간(시간):
- 2026-04-22: 인제 4.2, 북춘천 6.4
- 2026-04-23: 인제 빈값, 북춘천 9.8
- 2026-04-24: 인제 10.7, 북춘천 12.2

북춘천은 공식 ASOS 관측소 좌표로 계산한 인제와의 직선거리가 약 38.3km로 가장 가깝다.
AWS를 포함한 전체 관측망의 최단거리를 의미하지 않는다.
북춘천 값은 2026-09-16 기상청 ASOS 일자료 API로 조회했다.
인제 값은 기존 프로젝트 CSV를 사용했다.
누락 원인은 확인되지 않았으며, 이틀간 관측소 차이만으로 보정값을 확정하지 않는다.
이번 저습도·강풍 분석에서는 일조시간 보간이 필요하지 않다.

공식 관측소 정보: https://minwon.kma.go.kr/main/obvStn.do
자료 조회 API: https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList

재실행:
- python scripts/inspect_data.py
- python scripts/analyze_data_quality.py

두 분석 스크립트에는 pandas가 필요하다: python -m pip install pandas
분석 결과는 프로젝트 outputs 폴더에 저장된다. 원본 CSV는 수정하지 않는다.
