"""Application-owned permission, validation, dispatch, and call-limit boundary."""
from schemas import CheckStockInput, DeleteProductInput, SearchProductsInput, ToolInput, ValidationError
from tools import check_stock, delete_product, search_products

class ToolDefinition:
    def __init__(self, description, input_model, implementation):
        self.description = description
        self.input_model = input_model
        self.implementation = implementation

    @property
    def schema(self):
        return self.input_model.schema

TOOLS = {
    "search_products": ToolDefinition("Find products matching a query", SearchProductsInput, search_products),
    "check_stock": ToolDefinition("Check inventory for one product", CheckStockInput, check_stock),
    "delete_product": ToolDefinition("Permanently remove a product", DeleteProductInput, delete_product),
}
PERMISSIONS = {"customer": {"search_products", "check_stock"}, "admin": set(TOOLS)}

class ToolHarness:
    def __init__(self, role, max_tool_calls=5):
        if role not in PERMISSIONS:
            raise ValueError(f"unknown role: {role}")
        if max_tool_calls <= 0:
            raise ValueError("max_tool_calls must be positive")
        self.role, self.max_tool_calls, self.calls_made = role, max_tool_calls, 0

    def execute(self, tool_name, arguments):
        if self.calls_made >= self.max_tool_calls:
            return {"ok": False, "error": "tool call limit reached", "code": "limit_exceeded"}
        self.calls_made += 1
        definition = TOOLS.get(tool_name)
        if definition is None:
            return {"ok": False, "error": f"unknown tool: {tool_name}", "code": "unknown_tool"}
        if tool_name not in PERMISSIONS[self.role]:
            return {"ok": False, "error": f"role '{self.role}' cannot use '{tool_name}'", "code": "permission_denied"}
        try:
            validated = definition.input_model.validate(arguments)
            return {"ok": True, "data": definition.implementation(validated)}
        except ValidationError as exc:
            return {"ok": False, "error": str(exc), "code": "invalid_arguments"}
        except LookupError as exc:
            return {"ok": False, "error": str(exc), "code": "not_found"}
        except Exception:
            return {"ok": False, "error": "tool execution failed", "code": "tool_error"}
