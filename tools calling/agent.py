"""
CyberSentry agent: loads the fine-tuned Qwen3-4B GGUF model (served via
Ollama) and wires it into a LangGraph tool-calling loop with all 8
cybersecurity tools.

Prerequisite: the model must already be loaded into Ollama, e.g.
    ollama create cybersentry -f Modelfile
See Modelfile in this directory for the template setup.
"""
import os
from dotenv import load_dotenv
load_dotenv()  # reads .env from the current working directory

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from tools import ALL_TOOLS
from system_prompt import SYSTEM_PROMPT

MODEL_NAME = os.getenv("CYBERSENTRY_MODEL", "cybersentry")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def build_agent():
    llm = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.2)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def call_model(state: MessagesState):
        messages = state["messages"]
        # Ensure the system prompt is always the first message
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()


async def ask(app, question: str, verbose: bool = True) -> str:
    """Run one question through the agent, optionally printing intermediate tool calls."""
    state = {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]}
    final_text = ""
    async for event in app.astream(state, stream_mode="values"):
        last = event["messages"][-1]
        if verbose:
            role = last.__class__.__name__
            if getattr(last, "tool_calls", None):
                for tc in last.tool_calls:
                    print(f"  -> calling tool: {tc['name']}({tc['args']})")
            elif role == "ToolMessage":
                print(f"  <- tool result: {str(last.content)[:200]}")
        if hasattr(last, "content") and last.content:
            final_text = last.content
    return final_text


if __name__ == "__main__":
    import asyncio

    app = build_agent()

    async def main():
        q = "Is 8.8.8.8 a known malicious IP?"
        print(f"Q: {q}")
        answer = await ask(app, q)
        print(f"\nA: {answer}")

    asyncio.run(main())
