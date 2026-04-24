"""熔断器单元测试 — CircuitBreaker 状态机 + 线程安全"""

import time
import threading
import pytest
from src.tools.data_provider import CircuitBreaker


class TestCircuitBreakerBasic:
    """基础状态机测试"""

    def test_new_source_is_available(self):
        """新数据源默认可用"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
        assert cb.is_available("test") is True

    def test_available_after_few_failures(self):
        """未达阈值仍可用"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
        cb.record_failure("test")
        cb.record_failure("test")
        assert cb.is_available("test") is True

    def test_trip_after_threshold(self):
        """连续失败达到阈值 → 熔断"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
        for _ in range(3):
            cb.record_failure("test")
        assert cb.is_available("test") is False

    def test_success_resets_count(self):
        """成功重置失败计数"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
        cb.record_failure("test")
        cb.record_failure("test")
        cb.record_success("test")
        cb.record_failure("test")  # 只有 1 次失败
        assert cb.is_available("test") is True

    def test_half_open_after_cooldown(self):
        """冷却完成后恢复可用"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure("test")
        cb.record_failure("test")
        assert cb.is_available("test") is False
        time.sleep(0.15)
        assert cb.is_available("test") is True

    def test_multiple_sources_independent(self):
        """不同数据源独立熔断"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=300)
        cb.record_failure("akshare")
        cb.record_failure("akshare")
        assert cb.is_available("akshare") is False
        assert cb.is_available("efinance") is True


class TestCircuitBreakerStatus:
    """get_status 测试"""

    def test_status_closed(self):
        """正常状态显示 closed"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
        cb.record_failure("test")
        status = cb.get_status()
        assert status["test"] == "closed"

    def test_status_open(self):
        """熔断状态显示 open"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=300)
        cb.record_failure("test")
        cb.record_failure("test")
        status = cb.get_status()
        assert status["test"] == "open"

    def test_status_half_open(self):
        """冷却后显示 half_open"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure("test")
        cb.record_failure("test")
        time.sleep(0.15)
        status = cb.get_status()
        assert status["test"] == "half_open"

    def test_status_empty(self):
        """无记录返回空"""
        cb = CircuitBreaker()
        assert cb.get_status() == {}


class TestCircuitBreakerThreadSafety:
    """线程安全测试"""

    def test_concurrent_failures(self):
        """100 个线程并发 record_failure"""
        cb = CircuitBreaker(failure_threshold=200, cooldown_seconds=300)
        threads = [threading.Thread(target=cb.record_failure, args=("test",)) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert cb._states["test"]["failures"] == 100

    def test_concurrent_mixed_ops(self):
        """并发读写不崩溃"""
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=0.01)
        errors = []

        def worker(i):
            try:
                for _ in range(50):
                    cb.record_failure("src")
                    cb.is_available("src")
                    cb.record_success("src")
                    cb.get_status()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"并发错误: {errors}"
