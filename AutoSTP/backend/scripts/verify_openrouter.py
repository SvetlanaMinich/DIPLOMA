from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


async def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env")
    load_dotenv(_ROOT / ".env")

    from app.services import openrouter_service as ors

    ors.reset_client()
    try:
        text = await ors.ping_model()
    except ors.OpenRouterConfigError as e:
        print("Config:", e)
        return 2
    except ors.OpenRouterRequestError as e:
        print("API:", e)
        return 3
    except Exception as e:
        print("Error:", type(e).__name__, e)
        return 1

    print("Model reply:", ascii(text))
    print("OK: key and model respond.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
