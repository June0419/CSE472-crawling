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

Mastodon은 분산형 서비스이므로 선택한 서버가 알고 있는 게시물만 반환합니다. 목표 수량이 부족하면 관련 해시태그나 seed user를 추가하거나, 해당 사건의 게시물을 더 많이 알고 있는 서버를 사용해야 합니다.

## 공식 API 문서

- [Mastodon API 시작하기](https://docs.joinmastodon.org/client/intro/)
- [해시태그 타임라인](https://docs.joinmastodon.org/methods/timelines/#tag)
- [계정 API](https://docs.joinmastodon.org/methods/accounts/)
