"""Agent loop backed by a small local Ollama model."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from harness import ToolHarness
from harness import TOOLS


class OllamaChatModel:
    """Small HTTP client for Ollama's local chat and tool-calling API."""

    def __init__(self, model="llama3.2:3b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages):
        model_tools = []
        for name, definition in TOOLS.items():
            model_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": definition.description,
                    "parameters": definition.schema,
                },
            })

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": model_tools,
            "stream": False,
            "options": {"temperature": 0},
        }
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))["message"]
        except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as exc:
            raise RuntimeError(
                f"Could not get a response from Ollama model '{self.model}'. "
                "Make sure Ollama is running and the model is installed."
            ) from exc

class AgentAction:
    def __init__(self, tool, arguments):
        self.tool = tool
        self.arguments = arguments

class AgentResult:
    def __init__(self, answer, trace=None):
        self.answer = answer
        self.trace = trace if trace is not None else []

class ShoppingAgent:
    SYSTEM_PROMPT = """You are a safe shopping assistant. Help with product search, stock checks, and product deletion.
When a request needs catalog data or an action, you MUST respond by calling one of the provided tools. Do not describe an intended tool call in text, and do not write JSON that imitates a tool call. After receiving a tool result, call another tool if needed or give a concise final answer.
For an in-stock request, first call search_products using only the product name or category (for example, query "laptop"). Then call check_stock for returned product IDs until one has stock or all matching products have been checked. Never put words like "in stock", "available", or "stock" in the search query. Use product_id as a JSON integer, not a quoted string.
Base every claim about products or inventory on tool results. If a tool fails or the request is unclear, explain that plainly.
Product deletion is restricted by the application; never claim it succeeded unless the tool result confirms success."""

    def __init__(self, harness, max_iterations=10, model=None):
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        self.harness, self.max_iterations = harness, max_iterations
        self.model = model

    def run(self, request):
        request = request.strip()
        if not request:
            return AgentResult("Please provide a non-empty shopping request.")
        if self.model is not None:
            return self._run_with_model(request)
        trace, observations = [], []
        for _ in range(self.max_iterations):
            decision = self._decide(request, observations)
            if isinstance(decision, str):
                trace.append({"type": "final", "message": decision})
                return AgentResult(decision, trace)
            trace.append({"type": "action", "message": f"{decision.tool}({decision.arguments})"})
            result = self.harness.execute(decision.tool, decision.arguments)
            trace.append({"type": "observation", "message": str(result)})
            observations.append({"action": decision, "result": result})
        answer = "I stopped safely because the maximum iteration limit was reached."
        trace.append({"type": "final", "message": answer})
        return AgentResult(answer, trace)

    def _run_with_model(self, request):
        trace = []
        tool_observations = []
        searched_products = []
        checked_product_ids = set()
        wants_stock = any(word in request.lower() for word in ("stock", "available"))
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ]
        try:
            for _ in range(self.max_iterations):
                assistant_message = self.model.chat(messages)
                tool_calls = assistant_message.get("tool_calls", [])
                if not tool_calls:
                    answer = assistant_message.get("content", "").strip()
                    failed_observation = (
                        tool_observations[-1]
                        if tool_observations
                        and not tool_observations[-1]["ok"]
                        and tool_observations[-1].get("code") == "invalid_arguments"
                        else None
                    )
                    denied_observation = (
                        tool_observations[-1]
                        if tool_observations
                        and not tool_observations[-1]["ok"]
                        and tool_observations[-1].get("code") == "permission_denied"
                        else None
                    )
                    unchecked_products = [
                        product for product in searched_products
                        if product.get("id") not in checked_product_ids
                    ]
                    if failed_observation:
                        messages.extend([
                            assistant_message,
                            {
                                "role": "user",
                                "content": (
                                    "Your last tool call failed: " + failed_observation["error"] +
                                    ". Retry with arguments that match the tool schema. "
                                    "Use a real product ID from the search result, as an integer."
                                ),
                            },
                        ])
                        continue
                    if denied_observation:
                        answer = f"I could not complete the request: {denied_observation['error']}."
                        trace.append({"type": "final", "message": answer})
                        return AgentResult(answer, trace)
                    if wants_stock and unchecked_products:
                        available_ids = [product.get("id") for product in unchecked_products]
                        messages.extend([
                            assistant_message,
                            {
                                "role": "user",
                                "content": (
                                    "You have not checked stock for these matching product IDs: "
                                    f"{available_ids}. Do not search again. Call check_stock for one of these "
                                    "actual integer product_id values before answering."
                                ),
                            },
                        ])
                        continue
                    if not answer:
                        answer = "The model returned no answer. Please try again."
                    trace.append({"type": "final", "message": answer})
                    return AgentResult(answer, trace)

                messages.append(assistant_message)
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    tool_name = function.get("name", "")
                    arguments = function.get("arguments", {})
                    if (
                        tool_name in ("check_stock", "delete_product")
                        and isinstance(arguments, dict)
                        and isinstance(arguments.get("product_id"), str)
                        and arguments["product_id"].isdigit()
                    ):
                        arguments["product_id"] = int(arguments["product_id"])
                    trace.append({"type": "action", "message": f"{tool_name}({arguments})"})
                    result = self.harness.execute(tool_name, arguments)
                    trace.append({"type": "observation", "message": str(result)})
                    tool_observations.append(result)
                    if tool_name == "search_products" and result.get("ok"):
                        searched_products.extend(result["data"].get("products", []))
                    if tool_name == "check_stock" and result.get("ok"):
                        checked_product_ids.add(result["data"].get("product_id"))
                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": json.dumps(result),
                    })

            answer = "I stopped safely because the maximum iteration limit was reached."
            trace.append({"type": "final", "message": answer})
            return AgentResult(answer, trace)
        except RuntimeError as exc:
            answer = str(exc)
            trace.append({"type": "error", "message": answer})
            return AgentResult(answer, trace)

    def _decide(self, request, observations):
        lowered = request.lower()
        if any(word in lowered for word in ("delete", "remove")):
            if observations:
                result = observations[-1]["result"]
                return "Product deleted." if result["ok"] else f"I could not complete the request: {result['error']}."
            product_id = self._extract_id(lowered)
            return AgentAction("delete_product", {"product_id": product_id}) if product_id else "Please include a positive product ID to delete."
        if not observations:
            product_id = self._extract_id(lowered)
            if "stock" in lowered and product_id is not None:
                return AgentAction("check_stock", {"product_id": product_id})
            return AgentAction("search_products", {"query": self._extract_query(lowered)})
        last = observations[-1]["result"]
        if not last["ok"]:
            return f"I could not complete the request: {last['error']}."
        data = last["data"]
        if "products" in data:
            if not data["products"]:
                return "I found no matching products."
            return AgentAction("check_stock", {"product_id": data["products"][0]["id"]})
        if "stock" in data:
            if data["stock"] > 0:
                return f"{data['name']} (product {data['product_id']}) is in stock: {data['stock']} available."
            products = observations[0]["result"].get("data", {}).get("products", [])
            checked = {item["action"].arguments["product_id"] for item in observations if item["action"].tool == "check_stock"}
            next_product = next((product for product in products if product["id"] not in checked), None)
            if next_product:
                return AgentAction("check_stock", {"product_id": next_product["id"]})
            return "I found matching products, but none are currently in stock."
        return "The request was completed."

    @staticmethod
    def _extract_id(text):
        match = re.search(r"\b(?:id\s*)?(\d+)\b", text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_query(text):
        cleaned = re.sub(r"\b(find|search|show|me|a|an|the|that|is|currently|available|please|stock|in)\b", " ", text)
        return " ".join(cleaned.split()) or text
