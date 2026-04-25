"""JSON → SQLite 迁移脚本

用法：
    python -m src.database.migrate

自动将 data/portfolio.json 中的持仓数据迁移到 SQLite。
迁移完成后保留旧文件为 .bak 备份。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.database.engine import init_db
from src.database.repositories import PortfolioRepository

logger = logging.getLogger(__name__)

JSON_PATH = Path("data/portfolio.json")


def migrate_json_to_sqlite() -> int:
    """将 JSON 持仓数据迁移到 SQLite。

    Returns:
        迁移的持仓数量
    """
    # 1. 初始化数据库
    init_db()

    # 2. 读取 JSON 数据
    if not JSON_PATH.exists():
        logger.info("[迁移] 未找到 %s，跳过迁移", JSON_PATH)
        return 0

    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("[迁移] 读取 JSON 文件失败: %s", e)
        return 0

    if not data:
        logger.info("[迁移] JSON 文件为空，跳过迁移")
        return 0

    # 3. 写入 SQLite
    repo = PortfolioRepository()
    count = repo.upsert_many(data)

    # 4. 验证迁移结果
    db_count = repo.count()
    logger.info("[迁移] JSON → SQLite 完成：JSON %d 条 → SQLite %d 条", len(data), db_count)

    # 5. 备份旧文件
    backup_path = JSON_PATH.with_suffix(".json.bak")
    JSON_PATH.rename(backup_path)
    logger.info("[迁移] 旧文件已备份为 %s", backup_path)

    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    n = migrate_json_to_sqlite()
    print(f"✅ 迁移完成，共迁移 {n} 条持仓数据")
