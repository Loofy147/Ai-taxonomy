from pif.models import ToolContract
from pif.router import ToolRouter

def test_router_pruning():
    tool1 = ToolContract(
        name="sql_query",
        description="Execute BigQuery SQL analytical query",
        category="atomic",
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )
    tool2 = ToolContract(
        name="sftp_upload",
        description="Upload file to secure remote SFTP server",
        category="atomic",
        inputSchema={"type": "object", "properties": {}},
        outputSchema={"type": "object"}
    )

    registry = {"sql_query": tool1, "sftp_upload": tool2}
    router = ToolRouter(registry)

    candidates = router.route_and_filter("Run SQL database query", top_k=1)
    assert len(candidates) == 1
    assert candidates[0].name == "sql_query"

    savings = ToolRouter.calculate_token_savings(total_tools_count=100, filtered_tools_count=5)
    assert savings["tokens_saved"] == 23750
    assert savings["reduction_percentage"] == 95.0
