"""Explicit input schemas and validation for every exposed tool."""
class ValidationError(ValueError):
    pass

class ToolInput:
    @classmethod
    def validate(cls, raw):
        if not isinstance(raw, dict):
            raise ValidationError("arguments must be an object")
        allowed = cls.required_fields
        unknown = set(raw) - set(allowed)
        if unknown:
            raise ValidationError(f"unknown argument(s): {', '.join(sorted(unknown))}")
        missing = set(allowed) - set(raw)
        if missing:
            raise ValidationError(f"missing required argument(s): {', '.join(sorted(missing))}")
        try:
            return cls(**raw)
        except TypeError as exc:
            raise ValidationError(f"invalid arguments: {exc}") from exc

class SearchProductsInput(ToolInput):
    required_fields = ("query",)
    schema = {"type": "object", "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 80}}, "required": ["query"], "additionalProperties": False}

    def __init__(self, query):
        self.query = query
        self.__post_init__()

    def __post_init__(self):
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValidationError("query must be a non-empty string")
        if len(self.query) > 80:
            raise ValidationError("query must be at most 80 characters")

class CheckStockInput(ToolInput):
    required_fields = ("product_id",)
    schema = {"type": "object", "properties": {"product_id": {"type": "integer", "minimum": 1}}, "required": ["product_id"], "additionalProperties": False}

    def __init__(self, product_id):
        self.product_id = product_id
        self.__post_init__()

    def __post_init__(self):
        if isinstance(self.product_id, bool) or not isinstance(self.product_id, int):
            raise ValidationError("product_id must be an integer")
        if self.product_id <= 0:
            raise ValidationError("product_id must be positive")

class DeleteProductInput(CheckStockInput):
    schema = CheckStockInput.schema
