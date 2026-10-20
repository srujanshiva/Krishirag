import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop_spec = "asyncio.windows_events:SelectorEventLoop"
    else:
        loop_spec = "auto"
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, loop=loop_spec)
