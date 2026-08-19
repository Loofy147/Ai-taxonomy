# Procedure Intelligence Framework (PIF)

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Bridging Probabilistic AI Reasoning and Deterministic Code Execution**

The **Procedure Intelligence Framework (PIF)** is an open-source tool-orchestration, formal-verification, and multi-dimensional taxonomy framework designed for autonomous AI agent ecosystems. It provides a mathematically sound bridge between LLM reasoning and deterministic code execution.

---

## 🚀 Key Features & Architectural Pillars

| Feature | Description | Architecture Implementation |
| --- | --- | --- |
| **Multi-Dimensional Taxonomy** | Classifies procedures along execution nature, statefulness, side-effects, and meta-levels. | `@procedure` decorator, `ProcedureDimension`, `ProcedureMetadata` |
| **Strict Schema Enforcement** | Prevents parameter hallucinations and malformed API payloads. | `SchemaValidator` (`strict: True`, `outputSchema` validation) |
| **Formal Safety Verification** | Certifies state correctness before and after procedure execution. | Hoare logic triples $\{P\} C \{Q\}$, Weakest Precondition $wp(V := E, Q)$ solver |
| **Router Pattern & Context Pruning** | Eliminates token bloat by dynamically injecting only relevant schemas. | `ToolRouter` intent filter cutting $I_{total}$ context costs |
| **Transactional Resilience & Rollbacks** | Safeguards mutative procedures with transactional boundaries. | `TransactionManager` (Try-Catch / Rollback handler) |
| **Human-In-The-Loop (HITL) Guards** | Blocks non-reversible operations until human permission is granted. | `HITLGuard` for side-effect level `NON_REVERSIBLE` |
| **Procedure Intelligence Viability Score (PIVS)** | Scientific health metric grading schema clarity, complexity, and reliability. | `PIVSCalculator` computing $PIVS = \frac{\text{Clarity} \times \text{Reliability}}{1 + \text{Complexity}}$ |
| **MCP Integration** | Native Model Context Protocol adapter for local `stdio` and remote `http`/`sse`. | `MCPAdapter` with `validate_authorization_server_url` |

---

## 🎯 Where Can You Use It?

1. **Autonomous AI Agent Ecosystems**: Standardized tool calling via MCP protocols with strict schema contracts.
2. **Enterprise DevOps & Infrastructure Automation**: Safe execution of cloud provisioning, CI/CD, and database migrations with automated rollbacks.
3. **Cybersecurity & Threat Response**: Secure incident response systems and honeypot simulations.
4. **Enterprise Data Pipelines**: Multi-step ETL/ELT pipelines and dynamic query orchestrators.
5. **Low-Code / No-Code Workflow Engines**: Dynamic composition of verified Directed Acyclic Graphs (DAGs).

---

## 💻 Quick Start

### Installation

```bash
pip install procedure-intelligence
```

### Basic Example

```python
from procedure_intelligence.taxonomy import procedure, ExecutionNature, SideEffectLevel
from procedure_intelligence.schema import SchemaValidator
from procedure_intelligence.mcp import MCPAdapter

@procedure(
    name="backup_database",
    description="Creates a compressed backup of a database",
    execution_nature=ExecutionNature.DETERMINISTIC,
    side_effect=SideEffectLevel.READ_ONLY,
    input_schema={
        "type": "object",
        "properties": {"db_name": {"type": "string"}},
        "required": ["db_name"]
    }
)
def backup_database(db_name: str) -> str:
    return f"backup_{db_name}.tar.gz"

# Register with Model Context Protocol (MCP) Adapter
mcp = MCPAdapter(transport_type="stdio")
mcp.register_tool(backup_database)

# Handle JSON-RPC 2.0 tool invocation
response = mcp.handle_jsonrpc_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "backup_database",
        "arguments": {"db_name": "production_db"}
    }
})

print(response)
```

---

## 🔬 Formal Verification (Hoare Logic & Weakest Precondition)

Before executing side-effecting code, PIF evaluates Backward Verification Rules:

$$wp(V := E, Q) = Q[V \mapsto E]$$

```python
from procedure_intelligence.verification import Predicate, HoareTriple, WeakestPrecondition

# Postcondition Q: balance >= 0
postcondition = Predicate("balance >= 0")

# Calculate Weakest Precondition wp(balance := balance - amount, balance >= 0)
wp = WeakestPrecondition.calculate_wp("balance", "balance - amount", postcondition)
print(f"Calculated Weakest Precondition: {wp.expression}") # (balance - amount) >= 0

# Verify Hoare Triple {P} C {Q}
triple = HoareTriple(precondition=wp, command="withdraw", postcondition=postcondition)
is_valid = triple.verify(
    initial_state={"balance": 500.0, "amount": 100.0},
    final_state={"balance": 400.0}
)
assert is_valid is True
```

---

## ⚙️ Running End-to-End Demo & Tests

Run the included end-to-end workflow example:

```bash
python examples/e2e_workflow.py
```

Run the unit test suite:

```bash
pytest
```

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
