# 061 — QA 생성  (이슈 #9)

retrieval context → Ollama 생성(thinking off) → **요약 + 짧은 인용 + `url#anchor` 딥링크**.

## 실행
```bash
python 06_qa/061_qa/qa.py "질문" [--graph] [--models qwen3:14b gemma3:4b]
```
- 모델: `qwen3:14b`(프롬프트에 `/no_think`로 thinking off), `gemma3:4b`. Ollama `localhost:11434`.
- 저작권: 본문 통째 덤프 금지. 소스당 짧은 인용 + URL.

## 검증 (2026-06-25)
"What is the absurd according to Camus...?" → 양 모델 모두 정확한 답변 + SEP 딥링크 인용
(`#SuiResAbs`, `#HapFacOneFat`), qwen3 thinking off 동작.
