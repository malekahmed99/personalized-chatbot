# quick standalone check — bypass the API, hit the client directly
from llm.client import LLMClient
import asyncio

async def test():
    await LLMClient.initialize() 
    client = LLMClient.get()
    text = ""
    async for tok in client.generate_stream("""
    My fastapi server doesn't start up because the uvicorn server keeps rebooting endlessly because of log files additions, here is part of the logs:
    
    "
    2026-07-09T00:31:22 | INFO     | app.startup | Logging initialised | level=INFO | file=C:\College\Projects\Chat-bot\chat-ui\backend\logs\app.log
2026-07-09T00:31:22 | INFO     | app.startup | Logging initialised | level=INFO | file=C:\College\Projects\Chat-bot\chat-ui\backend\logs\app.log
2026-07-09T00:31:24 | INFO     | watchfiles.main | 1 change detected
2026-07-09T00:31:24 | INFO     | app.startup | Logging initialised | level=INFO | file=C:\College\Projects\Chat-bot\chat-ui\backend\logs\app.log
2026-07-09T00:31:24 | INFO     | watchfiles.main | 1 change detected
2026-07-09T00:31:25 | INFO     | watchfiles.main | 1 change detected
2026-07-09T00:31:25 | INFO     | watchfiles.main | 1 change detected
2026-07-09T00:31:26 | INFO     | watchfiles.main | 1 change detected
2026-07-09T00:31:26 | INFO     | watchfiles.main | 1 change detected
2026-07-09T00:31:26 | INFO     | watchfiles.main | 1 change detected 
2026-07-09T00:31:27 | INFO     | watchfiles.main | 1 change detected
    " 
    explain why that happens"""):
        text += tok
    print(repr(text[:300]))

asyncio.run(test())