# Full Optimized LangGraph Map-Reduce Summarization Pipeline
import asyncio
from typing import Annotated, List, Literal, TypedDict
import operator
import logging
import os

from langchain.chains.combine_documents.reduce import (
    acollapse_docs,
    split_list_of_docs,
)
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage
from langchain.text_splitter import CharacterTextSplitter
from langchain import hub
from langgraph.constants import Send, START, END
from langgraph.graph import StateGraph
from utils.ingestor import RobustIngestor  # 👈 import the ingestor
from config import GLOBAL_LLM, CHUNK_SIZE, CHUNK_OVERLAP


# ── Setup logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── LLM Setup ───────────────────────────────────────────────────
llm = GLOBAL_LLM

# ── Prompts ─────────────────────────────────────────────────────
map_prompt = hub.pull("rlm/map-prompt")

reduce_template = """
The following is a set of summaries:
{docs}
Take these and distill it into a final, consolidated summary
of the main themes.
- do extract important object names, dates, and numbers
- do not repeat information
"""
reduce_prompt = ChatPromptTemplate.from_messages([("human", reduce_template)])

# ── Token Limit ─────────────────────────────────────────────────
token_max = 1000


def length_function(documents: List[Document]) -> int:
    return sum(llm.get_num_tokens(doc.page_content) for doc in documents)


# ── State Definitions ───────────────────────────────────────────
class OverallState(TypedDict):
    contents: List[str]
    summaries: Annotated[list, operator.add]
    collapsed_summaries: List[Document]
    final_summary: str


class SummaryState(TypedDict):
    content: str


# ── Summarization Functions ─────────────────────────────────────
async def generate_summary(state: SummaryState):
    prompt = map_prompt.invoke(state["content"])
    response = await llm.ainvoke(prompt)
    return {"summaries": [response.content]}


def map_summaries(state: OverallState):
    logger.info(f"Mapping {len(state['contents'])} content blocks to summary nodes...")
    return [
        Send("generate_summary", {"content": content}) for content in state["contents"]
    ]


def collect_summaries(state: OverallState):
    logger.info(
        f"Collected {len(state['summaries'])} summaries. Wrapping into Document objects..."
    )
    return {
        "collapsed_summaries": [
            Document(page_content=summary) for summary in state["summaries"]
        ]
    }


async def _reduce(input: dict) -> str:
    prompt = reduce_prompt.invoke(input)
    response = await llm.ainvoke(prompt)
    return response.content


async def collapse_summaries(state: OverallState):
    logger.info("Collapsing summaries to fit token limits...")
    doc_lists = split_list_of_docs(
        state["collapsed_summaries"], length_function, token_max
    )
    results = [await acollapse_docs(doc_list, _reduce) for doc_list in doc_lists]
    return {"collapsed_summaries": results}


def should_collapse(
    state: OverallState,
) -> Literal["collapse_summaries", "generate_final_summary"]:
    num_tokens = length_function(state["collapsed_summaries"])
    logger.info(f"Checking token count: {num_tokens} tokens.")
    return "collapse_summaries" if num_tokens > token_max else "generate_final_summary"


async def generate_final_summary(state: OverallState):
    logger.info("Generating final summary...")
    if not state["collapsed_summaries"]:
        return {"final_summary": "No content to summarize."}
    response = await _reduce({"docs": state["collapsed_summaries"]})
    return {"final_summary": response}


# ── Graph Construction ──────────────────────────────────────────
graph = StateGraph(OverallState)
graph.add_node("generate_summary", generate_summary)
graph.add_node("collect_summaries", collect_summaries)
graph.add_node("collapse_summaries", collapse_summaries)
graph.add_node("generate_final_summary", generate_final_summary)

graph.add_conditional_edges(START, map_summaries, ["generate_summary"])
graph.add_edge("generate_summary", "collect_summaries")
graph.add_conditional_edges("collect_summaries", should_collapse)
graph.add_conditional_edges("collapse_summaries", should_collapse)
graph.add_edge("generate_final_summary", END)

# ── Compile Graph ───────────────────────────────────────────────
app = graph.compile()


# ── Run With Ingestor ───────────────────────────────────────────
async def main():
    input_file = "documents/laptop_bill.pdf"  # Set your input file path here

    ingestor = RobustIngestor(input_file=input_file)
    chunks = ingestor.run()

    # Run the summarization graph
    result = await app.ainvoke(
        {
            "contents": chunks,
            "summaries": [],
            "collapsed_summaries": [],
            "final_summary": "",
        }
    )

    print("\n\n==== FINAL SUMMARY ====")
    print(result["final_summary"])


if __name__ == "__main__":
    asyncio.run(main())
