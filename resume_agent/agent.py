"""LLM-backed conversational resume analysis agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from resume_agent.config import AgentConfig

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
        messages = self._build_messages(user_message)

        if self.config.provider == "bedrock":
            reply = self._chat_bedrock(messages)
        else:
            reply = self._chat_openai(messages)

        self.history.append(ChatMessage(role="user", content=user_message))
        self.history.append(ChatMessage(role="assistant", content=reply))
        return reply

    def _chat_openai(self, messages: list[dict[str, str]]) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def _chat_bedrock(self, messages: list[dict[str, str]]) -> str:
        import json

        import boto3

        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": "\n\n".join(system_parts),
            "messages": conversation,
        }

        client = boto3.client("bedrock-runtime", region_name=self.config.aws_region)
        response = client.invoke_model(
            modelId=self.config.model,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        return body["content"][0]["text"]
