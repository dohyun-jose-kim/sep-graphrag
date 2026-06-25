#!/usr/bin/env python3
"""081 — SEP GraphRAG 챗봇 (Streamlit).

참고 디자인: 03_Chatbot-RAG-LLM/RAG-LLM_ver2.0.0/06_ui (채팅버블 + 사이드바 모델선택 + 소스 expander).
우리 Retriever(051) + qa(061)를 importlib로 직접 호출(별도 API 서버 없음, 로컬 단일유저).
저작권: 요약+짧은인용+SEP url#anchor 딥링크. 본문 덤프 금지. 로컬 전용.

실행: streamlit run 08_chatbot/app.py   (Qdrant docker + Ollama 떠 있어야 함)
"""
import importlib.util
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


retr_mod = _load("retrieve", "05_retrieve/051_retrieve/retrieve.py")
qa_mod = _load("qa", "06_qa/061_qa/qa.py")


@st.cache_resource(show_spinner="모델 로딩 중...")
def get_retriever():
    return retr_mod.Retriever()


def _sources_expander(sources):
    if sources:
        with st.expander(f"📖 출처 {len(sources)}개 (SEP 딥링크)"):
            for s in sources:
                st.markdown(f"- [{s['slug']} — {s['section_path']}]({s['url']})")


st.set_page_config(page_title="SEP GraphRAG", page_icon="📚")
st.title("📚 SEP GraphRAG Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.selectbox("Model", ["qwen3:14b", "gemma3:4b"], key="model")
st.sidebar.caption("qwen3:14b 고품질(/no_think) · gemma3:4b 빠름")
st.sidebar.toggle("Graph 확장 (비교·멀티홉)", key="use_graph", value=False)
if st.sidebar.button("새 세션"):
    st.session_state.messages = []
    st.rerun()
st.sidebar.caption("로컬 전용 · 요약+인용+딥링크 (SEP 본문 비재배포)")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            _sources_expander(m.get("sources"))

if prompt := st.chat_input("철학 질문을 입력하세요 (예: What is the absurd for Camus?)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("검색 + 생성 중..."):
            res = get_retriever().retrieve(prompt, k_rerank=8, n_parents=5,
                                           use_graph=st.session_state.use_graph)
            parents = res["parents"]
            model = st.session_state.model
            ans = qa_mod.ollama(model, qa_mod.build_prompt(prompt, parents,
                                                           no_think=model.startswith("qwen3")))
        st.markdown(ans)
        sources = [{"slug": p["slug"], "section_path": p["section_path"], "url": p["url"]} for p in parents]
        _sources_expander(sources)
    st.session_state.messages.append({"role": "assistant", "content": ans, "sources": sources})
