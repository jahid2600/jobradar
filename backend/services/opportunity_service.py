from typing import Any

from boto3.dynamodb.types import TypeDeserializer

from backend.aws_client import dynamodb
from backend.config import DYNAMODB_TABLE_NAME
from backend.intelligence.deduplication import job_identity_keys


class DynamoDBOpportunityService:
    """Read persisted opportunities from DynamoDB."""

    def __init__(self, client: Any = dynamodb, table_name: str = DYNAMODB_TABLE_NAME):
        self.client = client
        self.table_name = table_name
        self._deserializer = TypeDeserializer()

    def list_opportunities(self) -> list[dict[str, Any]]:
        """Scan the table; a queryable identity index is a future optimization."""

        opportunities = []
        scan_kwargs = {"TableName": self.table_name, "ConsistentRead": True}

        while True:
            response = self.client.scan(**scan_kwargs)
            opportunities.extend(
                self._deserialize_item(item)
                for item in response.get("Items", [])
            )

            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break

            scan_kwargs["ExclusiveStartKey"] = last_key

        return sorted(
            opportunities,
            key=lambda opportunity: opportunity["qualification"]["relevance_score"],
            reverse=True,
        )

    def existing_identities(self) -> set[str]:
        identities = set()
        for opportunity in self.list_opportunities():
            job = opportunity["job"]
            identities.update(job_identity_keys(job))
        return identities

    def _deserialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        values = {
            key: self._deserializer.deserialize(value)
            for key, value in item.items()
        }

        return {
            "job": {
                "title": values.get("title", ""),
                "company": values.get("company", ""),
                "location": values.get("location", ""),
                "url": values.get("url", values.get("job_id", "")),
                "source": values.get("source", ""),
                "description": values.get("description") or None,
                "experience": values.get("experience") or None,
                "posted_date": values.get("posted_date") or None,
            },
            "qualification": {
                "qualified": values.get("qualified", False),
                "relevance_score": int(values.get("relevance_score", 0)),
                "reason": values.get("reason", ""),
                "matched_requirements": values.get("matched_requirements", []),
                "skill_gaps": values.get("skill_gaps", []),
                "concerns": values.get("concerns", []),
            },
        }