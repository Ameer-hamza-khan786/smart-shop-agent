from typing import TypedDict, List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from config import GLOBAL_LLM  # Use the global LLM from config


# ── Pydantic schemas ─────────────────────────────────────────────────
class RouteDecision(BaseModel):
    route: Literal["rag", "answer", "end"]
    reply: str | None = Field(None, description="Filled only when route == 'end'")


class RagJudge(BaseModel):
    sufficient: bool


# ── LLM instances with structured output where needed ───────────────
router_llm = GLOBAL_LLM.with_structured_output(RouteDecision)
judge_llm = GLOBAL_LLM.with_structured_output(RagJudge)
answer_llm = GLOBAL_LLM


# ── Shared state type ────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: List[BaseMessage]
    route: Literal["rag", "answer", "end"]
    rag: str
    web: str
    Rag_Citation: Optional[List[str]]
    Web_Citation: Optional[List[str]]
