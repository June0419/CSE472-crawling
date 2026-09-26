# CSE 472 - Social Media Data Analysis

Mastodon 재난 데이터 수집, 네트워크 분석, Gephi 시각화 및 LLM 콘텐츠 분석을 위한 프로젝트입니다.

## 현재 준비된 기능

- API 토큰이 정상인지 확인
- 여러 재난 해시태그에서 게시물을 중복 없이 수집하고 관련 답글 문맥도 수집
- seed user에서 시작해 재난 관련 게시물의 멘션·답글 관계로 사용자를 확장하고, 부족한 수는 검증된 사건 게시물 작성자로 보충
- 최종 데이터 파일을 `data/posts.json`, `data/users.json`으로 저장

## 1. Python 환경 준비

PowerShell에서 프로젝트 폴더로 이동한 다음 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Mastodon 설정 입력

프로젝트 루트의 `.env` 파일에 다음 정보를 입력합니다.

```text
MASTODON_BASE_URL=https://가입한-서버-주소
MASTODON_ACCESS_TOKEN=발급받은-access-token
DISASTER_NAME=선택한 재난 사건 이름
DISASTER_HASHTAGS=관련태그1,관련태그2,관련태그3
SEED_USERS=사용자1@서버주소,사용자2@서버주소
```

`DISASTER_HASHTAGS`에는 `#`을 쓰지 않아도 됩니다. 여러 값은 쉼표로 구분합니다. `.env`에는 실제 토큰이 들어가므로 GitHub에 업로드하지 않습니다. Git에 올릴 수 있는 설정 예시는 `.env.example`에 있습니다.

## 3. API 연결 확인

```powershell
python src/test_connection.py
```

성공하면 연결된 Mastodon 계정명이 표시됩니다.

## 4. 데이터 수집

게시물 데이터:

```powershell
python src/collect_posts.py
```

사용자 및 멘션 관계 데이터:

```powershell
python src/collect_users.py
```

## 5. 네트워크 구성 및 Gephi 파일 생성

```powershell
python src/build_networks.py
python src/plot_network_previews.py
```

`output/networks/`에 두 네트워크의 GEXF, GraphML, 노드 CSV, 엣지 CSV가 생성됩니다. Gephi에서는 GEXF 파일을 열면 됩니다.

- `information_diffusion.gexf`: 게시물이 노드이며, 원 게시물에서 답글로 향하는 방향성 엣지를 사용합니다.
- `user_network.gexf`: 사용자가 노드이며, 멘션·답글·재게시 관계가 있으면 무방향 엣지를 사용합니다.

`output/figures/`의 PNG는 데이터와 레이아웃을 빠르게 확인하기 위한 미리보기입니다. 최종 보고서에는 Gephi에서 서로 다른 레이아웃과 노드 크기 설정을 적용해 내보낸 이미지를 사용합니다.

## 6. Gephi Toolkit으로 최종 시각화 자동 생성

Gephi Desktop과 같은 엔진을 사용하는 `GephiRender.java`는 정보확산망에 ForceAtlas2, 사용자망에 Yifan Hu 레이아웃을 적용합니다. 노드 크기는 degree에 따라 조정하고, 정보확산망은 게시물 유형, 사용자망은 modularity community에 따라 색을 입힙니다.

```powershell
javac --release 17 -cp tools/gephi-toolkit-0.11.3-all.jar -d build/gephi src/GephiRender.java

& "tools/Gephi-0.11.3/jre-x64/jdk-17.0.20.1+1-jre/bin/java.exe" `
  --add-opens=java.base/java.net=ALL-UNNAMED `
  -cp "tools/gephi-toolkit-0.11.3-all.jar;build/gephi" `
  GephiRender information output/networks/information_diffusion.gexf output/gephi

& "tools/Gephi-0.11.3/jre-x64/jdk-17.0.20.1+1-jre/bin/java.exe" `
  --add-opens=java.base/java.net=ALL-UNNAMED `
  -cp "tools/gephi-toolkit-0.11.3-all.jar;build/gephi" `
  GephiRender users output/networks/user_network.gexf output/gephi
```

`output/gephi/`에는 각 네트워크의 PNG, 스타일이 포함된 GEXF, 편집 가능한 `.gephi` 프로젝트 파일이 생성됩니다. GEXF와 `.gephi`에는 모든 노드가 보존되며, 보고서용 PNG는 연결 구조를 읽기 쉽도록 degree가 0인 고립 노드만 제외합니다.

## 7. 네트워크 지표와 LLM 키워드 분석

```powershell
python src/analyze_networks.py
python src/plot_user_measures.py
ollama pull llama3.2:3b
python src/extract_keywords_llm.py
python src/analyze_content.py
```

`output/analysis/`에는 네트워크 지표, 200명 전원의 1-hop 관계 및 중심성, 게시물별 LLM 키워드 3개, 키워드 빈도와 분석 결과가 생성됩니다. `output/figures/`에는 PageRank·degree·betweenness 분포, 보고서용 워드클라우드와 상위 키워드 막대그래프가 생성됩니다.

- 네트워크 경로 길이와 지름은 그래프가 분리되어 있으므로 가장 큰 연결 성분에서만 계산합니다.
- 키워드 분석은 네트워크 문맥을 위해 추가로 받은 답글을 제외하고, 해시태그 타임라인에서 직접 수집한 500개 게시물만 사용합니다.
- Llama 3.2 3B를 Ollama로 로컬 실행하여 게시물마다 정확히 3개의 키워드를 생성합니다. 실제 토큰이나 유료 API는 필요하지 않습니다.
- `extract_keywords_llm.py`는 중간 결과를 매 배치 저장하므로 중단되어도 기본 실행으로 이어서 처리합니다. 처음부터 다시 하려면 `--overwrite`를 사용합니다.

## 8. 최종 보고서와 제출 ZIP

키워드 추출과 분석까지 끝난 뒤 실행합니다.

```powershell
python src/generate_report.py
python src/build_submission.py
```

- 최종 보고서: `output/pdf/CSE472_Project1_Report.pdf`
- Gradescope 제출 파일: `output/submission/CSE472_Project1_Submission.zip`

제출 ZIP은 실제 `.env`와 API 토큰, 로컬 프로그램, 임시 파일 및 Java 보조 코드를 제외합니다. 과제에서 요구한 두 JSON 데이터셋, Python 소스, Gephi 프로젝트·이미지, 분석 결과와 PDF 보고서만 포함합니다.

Mastodon은 분산형 서비스이므로 선택한 서버가 알고 있는 게시물만 반환합니다. 목표 수량이 부족하면 관련 해시태그나 seed user를 추가하거나, 해당 사건의 게시물을 더 많이 알고 있는 서버를 사용해야 합니다.

## 공식 API 문서

- [Mastodon API 시작하기](https://docs.joinmastodon.org/client/intro/)
- [해시태그 타임라인](https://docs.joinmastodon.org/methods/timelines/#tag)
- [계정 API](https://docs.joinmastodon.org/methods/accounts/)
