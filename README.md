# Simple Safe Shopping Agent

## 1. Project Overview

This project is a small shopping assistant that receives a request, chooses a tool, observes its result, and decides whether another tool call is needed. Its local decision planner is deterministic and does not require an API key. It demonstrates the agent loop and application-level safety rules without connecting to an external LLM.

## 2. Available Tools

| Tool | What it does | Input |
|---|---|---|
| `search_products` | Finds matching products in the sample catalog. | `query`: non-empty string, up to 80 characters |
| `check_stock` | Returns the inventory count for a product. | `product_id`: positive integer |
| `delete_product` | Removes a product from the sample catalog. | `product_id`: positive integer |

Each tool has an input schema in `schemas.py` and an implementation in `tools.py`.

## 3. Agent Loop

The agent processes a request one action at a time:

```text
User request
    -> agent decides which tool to call
    -> tool call with structured arguments
    -> harness checks permission and validates arguments
    -> tool executes
    -> agent observes the result
    -> agent chooses another action or returns a final answer
```

For an in-stock search, the agent can search for matching products, check one product, and use that stock result to decide whether to check another product.

## 4. Permission Rule

Permissions are enforced in application code by `ToolHarness` in `harness.py`:

| Action | Customer | Admin |
|---|---:|---:|
| `search_products` | Allowed | Allowed |
| `check_stock` | Allowed | Allowed |
| `delete_product` | Denied | Allowed |

The agent can propose an action, but the harness checks the active role before executing it.

## 5. Safety

- **Validation:** Tool schemas reject empty or overlong search queries, non-integer IDs, non-positive IDs, missing arguments, and unknown arguments.
- **Error handling:** Permission failures, invalid inputs, unknown tools, missing products, and unexpected tool errors return controlled error results.
- **Call limit:** `ToolHarness` allows at most five tool calls per run by default.
- **Iteration limit:** `ShoppingAgent` allows at most six decision-loop iterations by default.
- **Empty request:** The agent asks the user to provide a request instead of calling a tool.

## 6. Example Run

Run the in-stock example from the project directory:

```bash
.venv/bin/python main.py "Find a laptop that is currently in stock" --show-trace
```

With the sample catalog, the tool calls and result are:

```text
[action] search_products({'query': 'laptop'})
[observation] {'ok': True, 'data': {'products': [{'id': 1, 'name': 'Everyday Laptop', 'price': 699.0}, {'id': 2, 'name': 'Developer Laptop', 'price': 1299.0}]}}
[action] check_stock({'product_id': 1})
[observation] {'ok': True, 'data': {'product_id': 1, 'name': 'Everyday Laptop', 'stock': 0}}
[action] check_stock({'product_id': 2})
[observation] {'ok': True, 'data': {'product_id': 2, 'name': 'Developer Laptop', 'stock': 5}}
[final] Developer Laptop (product 2) is in stock: 5 available.

Developer Laptop (product 2) is in stock: 5 available.
```

Try the permission rule from the command line:

```bash
.venv/bin/python main.py "Delete product 2" --role customer --show-trace
.venv/bin/python main.py "Delete product 2" --role admin --show-trace
```

Run the automated checks with:

```bash
.venv/bin/python -m unittest -v
```
# 22_TRY_LIMHAI_AGENT
