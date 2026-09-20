import logging
import time
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import ClientError

from backend.aws_client import dynamodb
from backend.config import (
    RADAR_LOCK_KEY,
    RADAR_LOCK_LEASE_SECONDS,
    RADAR_LOCK_TABLE_NAME,
)


logger = logging.getLogger(__name__)


@dataclass
class LockLease:
    owner: str
    acquired: bool
    lease_until: int | None = None


class RadarExecutionLock:
    """DynamoDB conditional lease shared by manual and scheduled triggers."""

    def __init__(
        self,
        client: Any = dynamodb,
        table_name: str = RADAR_LOCK_TABLE_NAME,
        lock_key: str = RADAR_LOCK_KEY,
        lease_seconds: int = RADAR_LOCK_LEASE_SECONDS,
    ):
        self.client = client
        self.table_name = table_name
        self.lock_key = lock_key
        self.lease_seconds = lease_seconds

    def acquire(self, owner: str) -> LockLease:
        now = int(time.time())
        lease_until = now + self.lease_seconds
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item={
                    "lock_key": {"S": self.lock_key},
                    "owner": {"S": owner},
                    "lease_until": {"N": str(lease_until)},
                },
                ConditionExpression="attribute_not_exists(lock_key) OR lease_until < :now",
                ExpressionAttributeValues={":now": {"N": str(now)}},
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                logger.info("Radar lock rejected", extra={"owner": owner})
                return LockLease(owner=owner, acquired=False)
            raise

        logger.info("Radar lock acquired", extra={"owner": owner, "lease_until": lease_until})
        return LockLease(owner=owner, acquired=True, lease_until=lease_until)

    def release(self, lease: LockLease) -> bool:
        if not lease.acquired:
            return False
        try:
            self.client.delete_item(
                TableName=self.table_name,
                Key={"lock_key": {"S": self.lock_key}},
                ConditionExpression="owner = :owner",
                ExpressionAttributeValues={":owner": {"S": lease.owner}},
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                logger.warning("Radar lock release skipped: ownership changed", extra={"owner": lease.owner})
                return False
            raise
        logger.info("Radar lock released", extra={"owner": lease.owner})
        return True