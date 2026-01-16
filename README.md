# 🤖 Daily Market & Robotics News Agent (Local AI Edition)

**집에 있는 고사양 PC(GPU)를 활용해 주식 정보와 최신 로봇 뉴스를 수집, 번역, 요약하여 GitHub Pages에 배포하는 자동화 프로젝트입니다.**

기존의 클라우드 API(Google Gemini, OpenAI 등)의 **사용량 제한(Rate Limit)과 비용 문제**를 해결하기 위해, 로컬 LLM(**Ollama + Llama 3**)을 사용하여 **무제한, 무료, 고품질**의 뉴스 큐레이션 시스템을 구축했습니다.

---

## ✨ 주요 기능 (Features)

1.  **📉 시장 데이터 대시보드**
    * KOSPI, S&P 500, 원/달러 환율 정보를 실시간으로 수집하여 시각화(Sparkline)합니다.
    * 주요 한국 기업(삼성전자, SK하이닉스 등)의 주가 등락률을 한눈에 보여줍니다.

2.  **🗞️ 글로벌 로봇 뉴스 큐레이션**
    * **Humanoid** 및 **Robot Hand/Gripper** 관련 최신 뉴스를 전 세계 주요 소스(Google News, Tech Xplore, IEEE Spectrum 등)에서 수집합니다.
    * 경제/증시 뉴스도 함께 브리핑합니다.

3.  **🧠 로컬 AI 기반 번역 및 요약 (Key Feature)**
    * **Ollama (Llama 3)** 모델을 사용하여 영어 기사를 **전문적인 한국어 IT 뉴스 스타일**로 번역하고 요약합니다.
    * API 호출 횟수나 비용 걱정 없이 수십, 수백 개의 기사를 처리할 수 있습니다.
    * `prompt.md` 파일을 통해 AI의 페르소나와 요약 스타일을 손쉽게 튜닝할 수 있습니다.

4.  **🚀 자동 배포 시스템**
    * 로컬 PC에서 처리가 완료되면 자동으로 `git commit` 및 `push`를 수행하여 GitHub Pages를 업데이트합니다.

---

## 🛠️ 시스템 요구 사항 (Requirements)

이 프로젝트는 **로컬 PC**에서 구동되도록 설계되었습니다.

* **OS:** Windows, macOS, Linux
* **Hardware:**
    * **GPU:** NVIDIA RTX 3060 이상 권장 (테스트 환경: **RTX 5060 Ti 16GB**)
    * RAM: 16GB 이상 권장
* **Software:**
    * [Python 3.10+](https://www.python.org/)
    * [Git](https://git-scm.com/)
    * [Ollama](https://ollama.com/) (AI 모델 구동용)

---

## 🚀 설치 및 실행 방법 (Installation)

### 1. 프로젝트 클론 (Clone)
```bash
git clone https://github.com/younlea/daily_inform.git
cd daily_inform
```

### 2. 필수 라이브러리 설치
```bash
pip install yfinance feedparser requests ollama
```

### 3. Ollama 설정 및 모델 다운로드
1.  [Ollama 공식 홈페이지](https://ollama.com/)에서 설치 프로그램을 다운로드하여 설치합니다.
2.  터미널(CMD/PowerShell)을 열고 **Llama 3** 모델을 다운로드합니다.
    ```bash
    ollama pull llama3
    ```
    *(참고: 다른 모델을 쓰고 싶다면 `local_update.py` 내부의 `LOCAL_MODEL` 변수를 변경하세요.)*

### 4. 실행 (Run)
PC에서 아래 명령어를 실행하면 뉴스 수집 → AI 요약 → HTML 생성 → GitHub 업로드가 한 번에 진행됩니다.
```bash
python local_update.py
```

---

## ⚙️ 설정 가이드 (Configuration)

### AI 말투/요약 스타일 변경 (`prompt.md`)
`prompt.md` 파일을 수정하여 AI에게 새로운 지시를 내릴 수 있습니다.
* **Role:** 기자의 전문성 설정
* **Tone:** 문체 (~함, ~임 등) 설정
* **Rule:** 고유명사 처리 방식 등

### 수집 대상 변경 (`local_update.py`)
`local_update.py` 파일 내의 `rss_humanoid`, `rss_hand` 리스트를 수정하여 뉴스 소스를 추가하거나 뺄 수 있습니다.

---

## ⏰ 자동화 팁 (Automation)

매번 수동으로 실행하기 귀찮다면?

* **Windows:** [작업 스케줄러]를 이용해 "매일 아침 7시" 혹은 "컴퓨터 켤 때" `python local_update.py`가 실행되도록 등록하세요.
* **Mac/Linux:** `crontab`을 이용해 자동 실행을 등록하세요.

---

## 📂 파일 구조
```
daily_inform/
├── index.html          # 메인 페이지 (시장 지표 + 최신 뉴스)
├── news.html           # 뉴스 전체 보기 페이지
├── news_archive.json   # 수집된 뉴스 데이터베이스 (JSON)
├── local_update.py     # [핵심] 로컬 실행용 메인 스크립트
├── prompt.md           # [핵심] AI 프롬프트 지시서
├── template.html       # 메인 페이지 템플릿
├── news_template.html  # 뉴스 페이지 템플릿
└── README.md           # 프로젝트 설명서
```

---

## License
MIT License
