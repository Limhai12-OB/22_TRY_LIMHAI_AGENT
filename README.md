# Simple Safe Shopping Agent

## 1. Project Overview

This project is a small shopping assistant that receives a request, chooses a tool, observes its result, and decides whether another tool call is needed. The command-line app uses the local `llama3.2:3b` model through Ollama. No cloud API key is needed. The model proposes actions, while the application harness checks permissions and validates arguments before any tool runs.

## 2. Available Tools

| Tool | What it does | Input |
|---|---|---|
| `search_products` | Finds matching products in the sample catalog. | `query`: non-empty string, up to 80 characters |
| `check_stock` | Returns the inventory count for a product. | `product_id`: positive integer |
| `delete_product` | Removes a product from the sample catalog. | `product_id`: positive integer |

Each tool has an input schema in `schemas.py` and an implementation in `tools.py`. The schemas are also supplied to the model as tool definitions.

## 3. Agent Loop

The system prompt and available tool schemas are sent to Ollama with the user's request. The model can answer directly or propose a structured tool call. The agent processes that action and sends the observation back to the model:

```text
User request
    -> model decides which tool to call
    -> structured tool call from the model
    -> harness checks permission and validates arguments
    -> tool executes
    -> agent observes the result
    -> model chooses another action or returns a final answer
```

For an in-stock search, the model can search for matching products, check one product, and use that stock result to decide whether to check another product.

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
- **Iteration limit:** `ShoppingAgent` allows at most ten decision-loop iterations by default.
- **Empty request:** The agent asks the user to provide a request instead of calling a tool.

## 6. Example Run

Install Ollama for your operating system, then download and start the small model:

```bash
ollama pull llama3.2:3b
ollama run llama3.2:3b
```

Leave Ollama running. In another terminal, run the in-stock example from the project directory:

```bash
.venv/bin/python main.py "Find a laptop that is currently in stock" --show-trace
```

With the sample catalog, a typical tool-call trace and result are:

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

The exact natural-language wording can vary. The sequence should search the catalog, check product stock, and report the available quantity. Run the automated checks with:

```bash
.venv/bin/python -m unittest -v
```

You can choose another Ollama model or server URL with `--model` and `--ollama-url`.
# 22_TRY_LIMHAI_AGENT
