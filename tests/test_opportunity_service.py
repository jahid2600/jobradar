from backend.services.opportunity_service import DynamoDBOpportunityService


class FakeDynamoDBClient:
    def __init__(self):
        self.scan_calls = []

    def scan(self, **kwargs):
        self.scan_calls.append(kwargs)

        if len(self.scan_calls) == 1:
            return {
                "Items": [
                    {
                        "job_id": {"S": "job-1"},
                        "title": {"S": "Lower match"},
                        "relevance_score": {"N": "65"},
                        "qualified": {"BOOL": True},
                    }
                ],
                "LastEvaluatedKey": {"job_id": {"S": "job-1"}},
            }

        return {
            "Items": [
                {
                    "job_id": {"S": "job-2"},
                    "title": {"S": "Higher match"},
                    "relevance_score": {"N": "90"},
                    "qualified": {"BOOL": True},
                }
            ]
        }


def test_opportunity_service_scans_pages_and_sorts_by_score():
    client = FakeDynamoDBClient()
    service = DynamoDBOpportunityService(client=client, table_name="test-jobs")

    opportunities = service.list_opportunities()

    assert [item["job"]["title"] for item in opportunities] == [
        "Higher match",
        "Lower match",
    ]
    assert client.scan_calls[0] == {
        "TableName": "test-jobs",
        "ConsistentRead": True,
    }
    assert client.scan_calls[1]["ExclusiveStartKey"] == {
        "job_id": {"S": "job-1"}
    }