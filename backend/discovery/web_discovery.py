import json

from backend.discovery.job_search import generate_search_strategy


def get_search_queries():
    strategy = generate_search_strategy()

    queries = strategy.get("search_queries", [])

    if not queries:
        raise ValueError("Bedrock returned no search queries.")

    return queries


def main():
    print("Running JobRadar web discovery...\n")

    queries = get_search_queries()

    print("===== SEARCH QUERIES =====")

    for index, query in enumerate(queries, start=1):
        print(f"{index}. {query}")

    print("\n===== DISCOVERY STATUS =====")
    print(json.dumps({
        "query_count": len(queries),
        "status": "ready_for_web_search"
    }, indent=2))


if __name__ == "__main__":
    main()