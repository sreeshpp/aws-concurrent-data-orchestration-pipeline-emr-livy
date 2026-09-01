"""Streamlit chatbot for LLM-powered resume analysis."""

from __future__ import annotations

import streamlit as st

from resume_agent.agent import ResumeAnalysisAgent
from resume_agent.config import AgentConfig
from resume_agent.parser import SUPPORTED_EXTENSIONS, parse_resume
from resume_agent.paths import SAMPLE_RESUME

st.set_page_config(
    page_title="Resume Analysis Agent",
    page_icon="📄",
    layout="wide",
)

QUICK_PROMPTS = [
    "Give me an overall assessment of this resume.",
    "What are the top 5 strengths?",
    "What skills or keywords are missing for a Senior Data Engineer role?",
    "Suggest 3 bullet-point improvements for the Amazon experience section.",
    "Generate 5 likely interview questions based on this resume.",
]

PROVIDER_LABELS = {
    "anthropic": "Using Anthropic API",
    "bedrock": "Using AWS Bedrock",
}


def _init_session() -> None:
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "resume_name" not in st.session_state:
        st.session_state.resume_name = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "loaded_file_id" not in st.session_state:
        st.session_state.loaded_file_id = None


def _load_resume(uploaded_file) -> None:
    resume_text = parse_resume(uploaded_file.getvalue(), uploaded_file.name)
    st.session_state.agent = ResumeAnalysisAgent(resume_text=resume_text)
    st.session_state.resume_name = uploaded_file.name
    st.session_state.loaded_file_id = f"{uploaded_file.name}:{uploaded_file.size}"
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                f"Resume **{uploaded_file.name}** loaded. "
                "Ask me anything about strengths, gaps, tailoring, ATS, or interview prep."
            ),
        }
    ]


def _load_sample_resume() -> None:
    if not SAMPLE_RESUME.exists():
        st.error("Sample resume not found in data/sample_resume.pdf")
        return
    resume_text = parse_resume(SAMPLE_RESUME.read_bytes(), SAMPLE_RESUME.name)
    st.session_state.agent = ResumeAnalysisAgent(resume_text=resume_text)
    st.session_state.resume_name = SAMPLE_RESUME.name
    st.session_state.loaded_file_id = f"{SAMPLE_RESUME.name}:{SAMPLE_RESUME.stat().st_size}"
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Loaded the bundled **sample resume**. "
                "Try a quick prompt or ask your own question."
            ),
        }
    ]


def _provider_label(provider: str) -> str:
    return PROVIDER_LABELS.get(provider, f"Using {provider}")


def _reload_agent() -> bool:
    """Recreate the agent so code and config changes take effect."""
    if st.session_state.agent is None:
        return False

    resume_text = st.session_state.agent.resume_text
    st.session_state.agent = ResumeAnalysisAgent(resume_text=resume_text)
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Agent reloaded with the latest configuration. "
                "Chat history was cleared."
            ),
        }
    ]
    return True


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("Resume")
        uploaded = st.file_uploader(
            "Upload resume",
            type=[ext.lstrip(".") for ext in sorted(SUPPORTED_EXTENSIONS)],
            help="PDF or plain text",
        )
        if uploaded is not None:
            file_id = f"{uploaded.name}:{uploaded.size}"
            if st.session_state.loaded_file_id != file_id:
                _load_resume(uploaded)
                st.session_state.loaded_file_id = file_id

        if st.button("Use sample resume", use_container_width=True):
            _load_sample_resume()

        if st.session_state.resume_name:
            st.success(f"Active: {st.session_state.resume_name}")
            with st.expander("Preview extracted text"):
                st.text(st.session_state.agent.resume_text[:4000])

        st.divider()
        st.header("Model")
        try:
            config = AgentConfig.from_env()
            st.info(_provider_label(config.provider))
            st.caption(f"Model: `{config.model}`")
            if config.provider == "anthropic" and not config.api_key:
                st.warning(
                    "Set `ANTHROPIC_API_KEY` in `~/.config/resume-agent/config.env`."
                )
        except Exception as exc:
            st.warning(str(exc))

        if st.button(
            "Reload agent",
            use_container_width=True,
            help="Recreate the agent after code or config changes without restarting Streamlit",
        ):
            if _reload_agent():
                st.success("Agent reloaded.")
            else:
                st.info("Load a resume first, then reload the agent.")
            st.rerun()

        st.divider()
        if st.session_state.agent and st.button("Clear chat", use_container_width=True):
            st.session_state.agent.reset_conversation()
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Chat cleared. What would you like to analyze?",
                }
            ]
            st.rerun()


def _render_chat() -> None:
    st.title("Resume Analysis Agent")
    try:
        provider = AgentConfig.from_env().provider
        provider_note = _provider_label(provider)
    except Exception:
        provider_note = "Upload a resume and chat with an LLM career coach."

    st.caption(f"{provider_note}. Upload a resume to get started.")

    if st.session_state.agent is None:
        st.info("Upload a resume in the sidebar or load the sample resume to begin.")
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    for prompt in QUICK_PROMPTS:
        if st.button(prompt, key=f"quick-{prompt[:24]}"):
            _handle_user_message(prompt)

    if user_input := st.chat_input("Ask about this resume..."):
        _handle_user_message(user_input)


def _handle_user_message(user_input: str) -> None:
    agent: ResumeAnalysisAgent = st.session_state.agent
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                reply = agent.chat(user_input)
            except Exception as exc:
                reply = f"Sorry, I could not complete that request: {exc}"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()


def main() -> None:
    _init_session()
    _render_sidebar()
    _render_chat()


if __name__ == "__main__":
    main()
