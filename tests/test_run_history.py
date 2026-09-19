from backend.storage.run_store import RadarRunStore


def test_run_store_persists_partial_and_completed_status(tmp_path):
    store = RadarRunStore(tmp_path / "runs.json")
    created = store.create("run-1")

    assert created["status"] == "running"
    assert created["started_at"].endswith("Z")

    updated = store.update(
        "run-1",
        current_stage="qualifying",
        stage_progress=50,
        metrics={"unique": 4},
    )
    assert updated["current_stage"] == "qualifying"
    assert store.get("run-1")["metrics"] == {"unique": 4}

    completed = store.update(
        "run-1",
        status="completed",
        current_stage="completed",
        completed_at="2026-09-20T12:00:00Z",
        duration_ms=123,
    )
    assert completed["completed_at"].endswith("Z")
    assert store.list_recent()[0]["run_id"] == "run-1"


def test_run_store_history_is_newest_first(tmp_path):
    store = RadarRunStore(tmp_path / "runs.json")
    store.create("older")
    store.create("newer")

    assert [run["run_id"] for run in store.list_recent()] == ["newer", "older"]