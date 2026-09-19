import api


class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, function, *args, **kwargs):
        self.tasks.append((function, args, kwargs))


def test_run_endpoint_returns_unique_run_id_and_status(monkeypatch, tmp_path):
    store = api.RadarRunStore(tmp_path / "runs.json")
    monkeypatch.setattr(api, "run_store", store)
    tasks = FakeBackgroundTasks()

    first = api.run_radar(tasks)
    second = api.run_radar(FakeBackgroundTasks())

    assert first["status"] == "started"
    assert first["run_id"]
    assert second["status"] == "running"
    assert second["run_id"] == first["run_id"]
    assert tasks.tasks[0][1] == (first["run_id"],)


def test_run_history_endpoint_returns_persisted_runs(monkeypatch, tmp_path):
    store = api.RadarRunStore(tmp_path / "runs.json")
    store.create("run-1")
    store.create("run-2")
    monkeypatch.setattr(api, "run_store", store)

    history = api.radar_runs()

    assert [run["run_id"] for run in history] == ["run-2", "run-1"]
    assert "metrics" in history[0]
    assert "generated_query_count" in history[0]


def test_failed_run_persists_failed_stage(monkeypatch, tmp_path):
    store = api.RadarRunStore(tmp_path / "runs.json")
    store.create("run-failed")
    monkeypatch.setattr(api, "run_store", store)

    def fail_pipeline(**kwargs):
        raise RuntimeError("controlled pipeline failure")

    monkeypatch.setattr(api, "run_pipeline", fail_pipeline)
    api.execute_radar("run-failed")

    failed = store.get("run-failed")
    assert failed["status"] == "failed"
    assert failed["current_stage"] == "failed"
    assert failed["completed_at"]
    assert "controlled pipeline failure" in failed["failures"][-1]