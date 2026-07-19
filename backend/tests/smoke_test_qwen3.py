import asyncio
from llm.client import LLMClient
from llm.prompt import format_chat_prompt

TESTS = [
    # Test 1: Short factual answer — must stop cleanly
    ("What is ARP poisoning? One sentence.", "stop"),
    # Test 2: Forensic log input — must use forensic schema
    ("Error: Connection refused at 127.0.0.1:5432\nTraceback: psycopg2.OperationalError", "stop"),
    # Test 3: Security analysis — must use Causal Analysis schema
    ("How does a SQL injection attack work?", "stop"),
]

async def smoke_test():
    await LLMClient.initialize()
    client = LLMClient.get()

    for prompt_text, expected_reason in TESTS:
        prompt = format_chat_prompt([{"role": "user", "content": prompt_text}])
        tokens = []
        async for tok in client.generate_stream(prompt):
            tokens.append(tok)
        response = "".join(tokens)
        reason = client.last_finish_reason

        print(f"\n{'='*60}")
        print(f"Input: {prompt_text[:60]}...")
        print(f"Response (first 200 chars): {response[:200]}")
        print(f"Finish reason: {reason}")

        assert reason == expected_reason, f"Expected '{expected_reason}', got '{reason}'"
        assert "<think>" not in response, "Thinking tokens leaking"

        # Schema checks
        if "Traceback" in prompt_text or "Error:" in prompt_text:
            assert "Root Cause" in response or "## Security Causal" in response, \
                "Forensic input not producing expected schema"

    print("\n✅ All smoke tests passed")

asyncio.run(smoke_test())
