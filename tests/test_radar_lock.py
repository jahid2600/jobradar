from botocore.exceptions import ClientError

from backend.storage.radar_lock import RadarExecutionLock


def conditional_failure():
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "held"}},
        "PutItem",
    )


class FakeDynamo:
    def __init__(self):
        self.item = None

    def put_item(self, **kwargs):
        if self.item and self.item["lease_until"]["N"] >= kwargs["ExpressionAttributeValues"][":now"]["N"]:
            raise conditional_failure()
        self.item = kwargs["Item"]

    def delete_item(self, **kwargs):
        if self.item and self.item["owner"] != kwargs["ExpressionAttributeValues"][":owner"]:
            raise conditional_failure()
        self.item = None


def test_lock_acquisition_and_second_acquisition_are_exclusive():
    lock = RadarExecutionLock(client=FakeDynamo(), lease_seconds=60)

    first = lock.acquire("run-1")
    second = lock.acquire("run-2")

    assert first.acquired is True
    assert second.acquired is False


def test_expired_lock_can_be_acquired(monkeypatch):
    current_time = [100]
    monkeypatch.setattr("backend.storage.radar_lock.time.time", lambda: current_time[0])
    client = FakeDynamo()
    lock = RadarExecutionLock(client=client, lease_seconds=10)

    assert lock.acquire("run-1").acquired is True
    current_time[0] = 111
    assert lock.acquire("run-2").acquired is True


def test_lock_release_allows_next_owner():
    client = FakeDynamo()
    lock = RadarExecutionLock(client=client, lease_seconds=60)
    first = lock.acquire("run-1")

    assert lock.release(first) is True
    assert lock.acquire("run-2").acquired is True