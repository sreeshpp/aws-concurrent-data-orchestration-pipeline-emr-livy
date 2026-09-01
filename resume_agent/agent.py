"""LLM-backed conversational resume analysis agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from resume_agent.config import AgentConfig

AGENT_BUILD_ID = "2026-09-01-anthropic-no-temperature"

SYSTEM_PROMPT = """You are an expert career coach and technical recruiter assistant.
You analyze resumes with precision and empathy.

You have access to the candidate's full resume text. Use only information present in the resume
unless the user asks for general advice. When something is missing, say so clearly.

Help with:
- Overall strengths and positioning
- Skills inventory and gaps
- Experience narrative and impact (STAR-style feedback)
- ATS and keyword optimization
- Tailoring the resume for a target role or job description
- Interview preparation questions based on their background
- Education, certifications, and career progression

Be concise, structured, and actionable. Use bullet points when listing multiple items.
If the user pastes a job description, compare it directly against the resume.
"""


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ResumeAnalysisAgent:
    resume_text: str
    config: AgentConfig = field(default_factory=AgentConfig.from_env)
    history: list[ChatMessage] = field(default_factory=list)

    def reset_conversation(self) -> None:
        self.history.clear()

    def update_resume(self, resume_text: str) -> None:
        self.resume_text = resume_text
        self.reset_conversation()

    def _build_messages(self, user_message: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"RESUME TEXT:\n\n{self.resume_text}",
            },
        ]
        for item in self.history:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(self, user_message: str) -> str:
        if not self.resume_text.strip():
            raise ValueError("Upload a resume before chatting.")

        self.config.validate()
        config = AgentConfig.from_env()
        messages = self._build_messages(user_message)

        if config.provider == "bedrock":
            reply = self._chat_bedrock(messages, config)
        else:
            reply = self._chat_anthropic(messages, config)

        self.history.append(ChatMessage(role="user", content=user_message))
        self.history.append(ChatMessage(role="assistant", content=reply))
        return reply

    def _chat_anthropic(
        self, messages: list[dict[str, str]], config: AgentConfig
    ) -> str:
        from anthropic import Anthropic

        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        client_kwargs: dict[str, str] = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        client = Anthropic(**client_kwargs)
        response = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            system="\n\n".join(system_parts),
            messages=conversation,
        )
        return response.content[0].text

    def _chat_bedrock(
        self, messages: list[dict[str, str]], config: AgentConfig
    ) -> str:
        import json

        import boto3

        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "system": "\n\n".join(system_parts),
            "messages": conversation,
        }

        client = boto3.client("bedrock-runtime", region_name=config.aws_region)
        response = client.invoke_model(
            modelId=self.config.model,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        return body["content"][0]["text"]
