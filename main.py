"""基金投资助手 — 主入口

启动 FastAPI 服务，供 C 端页面调用。

用法：
  python main.py              # 默认 0.0.0.0:8000
  python main.py --port 9000  # 自定义端口
"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "dev") == "dev",
    )


if __name__ == "__main__":
    main()
