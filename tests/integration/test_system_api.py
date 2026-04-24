"""系统 API 集成测试 — /api/health, /api/version, /api/logs"""


class TestHealthAPI:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestVersionAPI:
    def test_version_returns_dict(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "build_time" in data
        assert "git_commit" in data


class TestLogsAPI:
    def test_get_logs_empty(self, client):
        r = client.get("/api/logs")
        assert r.status_code == 200
        data = r.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)

    def test_get_logs_with_limit(self, client):
        r = client.get("/api/logs?limit=10")
        assert r.status_code == 200

    def test_get_logs_with_level_filter(self, client):
        r = client.get("/api/logs?level=ERROR")
        assert r.status_code == 200

    def test_clear_logs(self, client):
        r = client.delete("/api/logs")
        assert r.status_code == 200
        assert r.json()["ok"] is True
