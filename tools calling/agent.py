"""
CyberSentry agent: loads the fine-tuned Qwen3-4B GGUF model and wires it
into a LangGraph tool-calling loop with all 8 cybersecurity tools.

Supports two backends, chosen via the LLM_BACKEND env var:

  - "llamacpp" (default): connects to llama-cpp-python's OpenAI-compatible
    server. Start it first with:
        python -m llama_cpp.server \\
            --model /content/qwen3-4b-instruct-2507.Q4_K_M.gguf \\
            --n_ctx 8192 --chat_format chatml-function-calling
    (or omit --chat_format to use the GGUF's embedded chat template)

  - "ollama": connects to a running Ollama server with the model already
    loaded via `ollama create <name> -f Modelfile`.
"""
import os
from dotenv import load_dotenv
load_dotenv()  # reads .env from the current working directory

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from tools import ALL_TOOLS
from system_prompt import SYSTEM_PROMPT

LLM_BACKEND = os.getenv("LLM_BACKEND", "llamacpp").lower()
MODEL_NAME = os.getenv("CYBERSENTRY_MODEL", "cybersentry")

# llama.cpp server settings
LLAMACPP_BASE_URL = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8000/v1")

# Ollama settings (only used if LLM_BACKEND=ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _build_llm():
    if LLM_BACKEND == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.2)

    if LLM_BACKEND == "llamacpp":
        from langchain_openai import ChatOpenAI
        # llama-cpp-python's server mimics the OpenAI API; api_key is
        # required by the client but ignored by the local server.
        return ChatOpenAI(
            model=MODEL_NAME,
            base_url=LLAMACPP_BASE_URL,
            api_key="not-needed",
            temperature=0.2,
        )

    raise ValueError(f"Unknown LLM_BACKEND '{LLM_BACKEND}', expected 'llamacpp' or 'ollama'.")


def build_agent():
    llm = _build_llm()
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
