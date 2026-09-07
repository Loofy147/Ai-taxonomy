"""End-to-End Example demonstrating the Procedure Intelligence Framework (PIF)."""

from procedure_intelligence.taxonomy import (
    procedure,
    get_procedure_metadata,
    ExecutionNature,
    SideEffectLevel,
)
from procedure_intelligence.schema import SchemaValidator
from procedure_intelligence.verification import HoareTriple, Predicate, WeakestPrecondition
from procedure_intelligence.metrics import PIVSCalculator
from procedure_intelligence.router import ToolRouter
from procedure_intelligence.orchestration import (
    PlannerExecutor,
    ReActAgent,
    TransactionManager,
    HITLGuard,
)
from procedure_intelligence.mcp import MCPAdapter


# 1. Define procedures decorated with Procedure Intelligence Taxonomy metadata
@procedure(
    name="query_account_balance",
    description="Fetches customer account balance from database",
    execution_nature=ExecutionNature.DETERMINISTIC,
    side_effect=SideEffectLevel.READ_ONLY,
    input_schema={
        "type": "object",
        "properties": {"account_id": {"type": "string"}},
        "required": ["account_id"],
    },
    output_schema={
        "type": "object",
        "properties": {"account_id": {"type": "string"}, "balance": {"type": "number"}},
    },
    tags=["finance", "account", "database"],
)
def query_account_balance(account_id: str) -> dict:
    return {"account_id": account_id, "balance": 5000.0}


@procedure(
    name="transfer_funds",
    description="Transfers funds from source to target account",
    execution_nature=ExecutionNature.DETERMINISTIC,
    side_effect=SideEffectLevel.MUTATIVE_REVERSIBLE,
    input_schema={
        "type": "object",
        "properties": {
            "source_id": {"type": "string"},
            "target_id": {"type": "string"},
            "amount": {"type": "number"},
        },
        "required": ["source_id", "target_id", "amount"],
    },
    output_schema={
        "type": "object",
        "properties": {"status": {"type": "string"}, "transaction_id": {"type": "string"}},
    },
    preconditions=["source_balance >= amount", "amount > 0"],
    postconditions=["source_balance == old_balance - amount"],
    tags=["finance", "payment", "transfer"],
)
def transfer_funds(source_id: str, target_id: str, amount: float) -> dict:
    return {"status": "SUCCESS", "transaction_id": "tx_99812"}


def reverse_transfer_funds(args: dict):
    print(f"Reverting transfer of ${args['amount']} from {args['source_id']} to {args['target_id']}")


def main():
    print("=== Procedure Intelligence Framework E2E Demo ===")

    # 2. Schema Validation & Taxonomy Metadata Inspection
    meta_transfer = get_procedure_metadata(transfer_funds)
    print(f"\n[Taxonomy] Procedure Name: {meta_transfer.name}")
    print(f"[Taxonomy] Side Effect: {meta_transfer.dimensions.side_effect}")

    # 3. Compute Procedure Intelligence Viability Score (PIVS)
    pivs = PIVSCalculator.compute_pivs(meta_transfer, total_invocations=50, successful_invocations=48)
    print(f"[Metrics] PIVS Score: {pivs.pivs}/100 (Clarity: {pivs.schema_clarity}, Penalty: {pivs.complexity_penalty})")

    # 4. Formal State Safety Verification (Hoare Logic & Weakest Precondition)
    print("\n[Formal Verification] Calculating Weakest Precondition wp(balance := balance - amount, balance >= 0)...")
    postcondition = Predicate("balance >= 0")
    wp = WeakestPrecondition.calculate_wp("balance", "balance - amount", postcondition)
    print(f"[Formal Verification] Weakest Precondition Expression: {wp.expression}")

    hoare_triple = HoareTriple(
        precondition=wp,
        command="transfer_funds",
        postcondition=postcondition,
    )
    is_safe = hoare_triple.verify(initial_state={"balance": 5000.0, "amount": 1000.0}, final_state={"balance": 4000.0})
    print(f"[Formal Verification] Hoare Triple Verification Satisfied: {is_safe}")

    # 5. Tool Router Pattern (Context / Token Pruning)
    router = ToolRouter()
    router.register(query_account_balance)
    router.register(transfer_funds)

    pruned_schemas = router.get_pruned_context_schemas("I want to transfer money between accounts", max_tools=1)
    print(f"\n[Tool Router] Intent-Filtered Schemas Count: {len(pruned_schemas)}")
    print(f"[Tool Router] Selected Tool: {pruned_schemas[0]['name']}")

    # 6. Transactional Execution with Rollback Capability
    print("\n[Transactional Execution] Executing transfer with rollback protection...")
    tx_manager = TransactionManager()
    res = tx_manager.execute_transactional(
        transfer_funds,
        {"source_id": "acc_01", "target_id": "acc_02", "amount": 250.0},
        rollback_action=reverse_transfer_funds,
    )
    print(f"[Transactional Execution] Result: {res}")

    # 7. Model Context Protocol (MCP) Adapter Response Generation
    print("\n[MCP Adapter] Handling JSON-RPC 2.0 request...")
    mcp = MCPAdapter(transport_type="stdio")
    mcp.register_tool(query_account_balance)
    mcp_request = {
        "jsonrpc": "2.0",
        "id": "req-101",
        "method": "tools/call",
        "params": {
            "name": "query_account_balance",
            "arguments": {"account_id": "acc_01"},
        },
    }
    mcp_response = mcp.handle_jsonrpc_request(mcp_request)
    print(f"[MCP Adapter] Response: {mcp_response}")

    print("\nE2E Workflow Completed Successfully!")


if __name__ == "__main__":
    main()
