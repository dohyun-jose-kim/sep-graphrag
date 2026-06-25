# 081 — 챗봇 UI (Streamlit)  (이슈 #11)

SEP GraphRAG 챗봇 화면. **참고 디자인**: `03_Chatbot-RAG-LLM/RAG-LLM_ver2.0.0/06_ui`
(채팅버블 + 사이드바 모델선택 + 소스 expander).

## 실행 (repo 루트에서)
```bash
streamlit run 08_chatbot/app.py        # Qdrant docker + Ollama 떠 있어야 함
```
→ http://localhost:8501

## 구성
- `Retriever`(051) + `qa`(061)를 importlib로 직접 호출 (별도 API 서버 없음, 로컬 단일유저).
- 사이드바: 모델(`qwen3:14b`/`gemma3:4b`) + **Graph 확장 토글** + **🧠 thinking 표시 토글(qwen3)** + 새 세션.
  thinking on이면 qwen3의 `<think>` 트레이스를 expander로 분리 표시(기본 off=/no_think).
- `st.cache_resource`로 모델 1회 로드. assistant 답변 하단 **expander = SEP 출처(url#anchor 딥링크)**.
- 저작권: 요약+인용+딥링크(qa.py), 본문 덤프 금지, **로컬 전용**.

## 검증 (2026-06-25)
headless 기동 OK(`/_stcore/health`), 모듈 로드 무에러. 대화형 풀테스트는 브라우저 필요(retrieve+qa는 별도 검증됨).
