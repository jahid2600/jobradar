import api


def test_scheduling_disabled_is_safe(monkeypatch):
    monkeypatch.setattr(api, "RADAR_SCHEDULE_ENABLED", False)
    monkeypatch.setattr(api, "RADAR_LOCK_ENABLED", True)

    result = api.run_scheduled_radar()

    assert result["status"] == "disabled"


def test_scheduled_invocation_uses_shared_lock_and_trigger(monkeypatch, tmp_path):
    store = api.RadarRunStore(tmp_path / "runs.json")
    monkeypatch.setattr(api, "run_store", store)
    monkeypatch.setattr(api, "RADAR_SCHEDULE_ENABLED", True)
    monkeypatch.setattr(api, "RADAR_LOCK_ENABLED", True)

    class Lease:
        acquired = True

    class FakeLock:
        def acquire(self, owner):
            return Lease()

        def release(self, lease):
            return True

    monkeypatch.setattr(api, "radar_lock", FakeLock())
    monkeypatch.setattr(api, "execute_radar", lambda run_id, trigger_type, lease: store.update(
        run_id,
        status="completed",
        current_stage="completed",
        trigger={"type": trigger_type},
    ))

    result = api.run_scheduled_radar()

    assert result["status"] == "completed"
    assert store.get(result["run_id"])["trigger"] == {"type": "scheduled"}


def test_scheduled_invocation_skips_when_lock_is_held(monkeypatch):
    monkeypatch.setattr(api, "RADAR_SCHEDULE_ENABLED", True)
    monkeypatch.setattr(api, "RADAR_LOCK_ENABLED", True)

    class Lease:
        acquired = False

    class FakeLock:
        def acquire(self, owner):
            return Lease()

    monkeypatch.setattr(api, "radar_lock", FakeLock())

    result = api.run_scheduled_radar()

    assert result == {"status": "skipped", "reason": "active_run"}