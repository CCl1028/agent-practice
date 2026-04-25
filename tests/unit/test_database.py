"""数据层单元测试 — SQLAlchemy 模型 + Repository + 迁移"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Holding
from src.database.repositories import PortfolioRepository, ConfigRepository


@pytest.fixture
def db_session(tmp_path):
    """创建临时内存数据库"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    # Patch get_session 返回此 session
    from contextlib import contextmanager

    @contextmanager
    def _mock_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with patch("src.database.repositories.get_session", _mock_session):
        yield factory


class TestHoldingModel:
    """ORM 模型测试"""

    def test_to_dict(self, db_session):
        """to_dict 输出 FundHolding 兼容格式"""
        session = db_session()
        h = Holding(fund_code="005827", fund_name="易方达蓝筹", cost=20000, cost_nav=2.15, shares=9302.33)
        session.add(h)
        session.commit()

        d = h.to_dict()
        assert d["fund_code"] == "005827"
        assert d["fund_name"] == "易方达蓝筹"
        assert d["cost"] == 20000
        assert d["current_nav"] == 0  # 默认值
        assert d["trend_5d"] == []  # 默认值
        session.close()

    def test_unique_fund_code(self, db_session):
        """fund_code 唯一约束"""
        session = db_session()
        session.add(Holding(fund_code="005827", fund_name="A"))
        session.commit()

        from sqlalchemy.exc import IntegrityError
        session2 = db_session()
        session2.add(Holding(fund_code="005827", fund_name="B"))
        with pytest.raises(IntegrityError):
            session2.commit()
        session.close()
        session2.close()


class TestPortfolioRepository:
    """持仓 Repository 测试"""

    def test_list_empty(self, db_session):
        repo = PortfolioRepository()
        assert repo.list_all() == []

    def test_upsert_insert(self, db_session):
        repo = PortfolioRepository()
        result = repo.upsert("005827", fund_name="易方达蓝筹", cost=20000)
        assert result["fund_code"] == "005827"
        assert result["cost"] == 20000
        assert repo.count() == 1

    def test_upsert_update(self, db_session):
        repo = PortfolioRepository()
        repo.upsert("005827", fund_name="易方达蓝筹", cost=20000)
        repo.upsert("005827", cost=30000)
        all_h = repo.list_all()
        assert len(all_h) == 1
        assert all_h[0]["cost"] == 30000

    def test_upsert_many(self, db_session):
        repo = PortfolioRepository()
        data = [
            {"fund_code": "005827", "fund_name": "A", "cost": 10000},
            {"fund_code": "161725", "fund_name": "B", "cost": 15000},
        ]
        count = repo.upsert_many(data)
        assert count == 2
        assert repo.count() == 2

    def test_get_by_code(self, db_session):
        repo = PortfolioRepository()
        repo.upsert("005827", fund_name="测试基金")
        result = repo.get_by_code("005827")
        assert result is not None
        assert result["fund_name"] == "测试基金"

    def test_get_by_code_not_found(self, db_session):
        repo = PortfolioRepository()
        assert repo.get_by_code("999999") is None

    def test_delete(self, db_session):
        repo = PortfolioRepository()
        repo.upsert("005827", fund_name="A")
        assert repo.delete("005827") is True
        assert repo.count() == 0

    def test_delete_nonexistent(self, db_session):
        repo = PortfolioRepository()
        assert repo.delete("999999") is False

    def test_delete_all(self, db_session):
        repo = PortfolioRepository()
        repo.upsert("005827", fund_name="A")
        repo.upsert("161725", fund_name="B")
        n = repo.delete_all()
        assert n == 2
        assert repo.count() == 0


class TestConfigRepository:
    """配置 Repository 测试"""

    def test_get_set(self, db_session):
        repo = ConfigRepository()
        repo.set("BARK_URL", "https://test.bark")
        assert repo.get("BARK_URL") == "https://test.bark"

    def test_get_missing(self, db_session):
        repo = ConfigRepository()
        assert repo.get("NONEXISTENT") is None

    def test_update_existing(self, db_session):
        repo = ConfigRepository()
        repo.set("KEY", "old")
        repo.set("KEY", "new")
        assert repo.get("KEY") == "new"

    def test_get_all(self, db_session):
        repo = ConfigRepository()
        repo.set("A", "1")
        repo.set("B", "2")
        result = repo.get_all()
        assert result == {"A": "1", "B": "2"}

    def test_delete(self, db_session):
        repo = ConfigRepository()
        repo.set("KEY", "val")
        assert repo.delete("KEY") is True
        assert repo.get("KEY") is None


class TestMigration:
    """JSON → SQLite 迁移测试"""

    def test_migrate_success(self, db_session, tmp_path):
        """正常迁移"""
        json_file = tmp_path / "portfolio.json"
        data = [
            {"fund_code": "005827", "fund_name": "A", "cost": 20000, "cost_nav": 2.15},
            {"fund_code": "161725", "fund_name": "B", "cost": 15000},
        ]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        with patch("src.database.migrate.JSON_PATH", json_file), \
             patch("src.database.migrate.init_db"):
            from src.database.migrate import migrate_json_to_sqlite
            count = migrate_json_to_sqlite()

        assert count == 2
        # 旧文件应被重命名为 .bak
        assert not json_file.exists()
        assert json_file.with_suffix(".json.bak").exists()

    def test_migrate_no_file(self, db_session, tmp_path):
        """无 JSON 文件 → 跳过"""
        with patch("src.database.migrate.JSON_PATH", tmp_path / "nonexistent.json"), \
             patch("src.database.migrate.init_db"):
            from src.database.migrate import migrate_json_to_sqlite
            count = migrate_json_to_sqlite()
        assert count == 0

    def test_migrate_empty_file(self, db_session, tmp_path):
        """空 JSON 文件 → 跳过"""
        json_file = tmp_path / "portfolio.json"
        json_file.write_text("[]", encoding="utf-8")

        with patch("src.database.migrate.JSON_PATH", json_file), \
             patch("src.database.migrate.init_db"):
            from src.database.migrate import migrate_json_to_sqlite
            count = migrate_json_to_sqlite()
        assert count == 0
