"""Small, inspectable agent loop with a deterministic local decision model."""
import re
from harness import ToolHarness

class AgentAction:
    def __init__(self, tool, arguments):
        self.tool = tool
        self.arguments = arguments

class AgentResult:
    def __init__(self, answer, trace=None):
        self.answer = answer
        self.trace = trace if trace is not None else []

class ShoppingAgent:
    def __init__(self, harness, max_iterations=6):
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        self.harness, self.max_iterations = harness, max_iterations

    def run(self, request):
        request = request.strip()
        if not request:
            return AgentResult("Please provide a non-empty shopping request.")
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

