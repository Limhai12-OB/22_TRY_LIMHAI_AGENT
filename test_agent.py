import unittest
from agent import ShoppingAgent
from harness import ToolHarness

class ShoppingAgentTests(unittest.TestCase):
    def test_search_then_checks_until_in_stock(self):
        result = ShoppingAgent(ToolHarness("customer")).run("Find a laptop that is currently in stock")
        actions = [event["message"] for event in result.trace if event["type"] == "action"]
        self.assertEqual(len(actions), 3)
        self.assertIn("5 available", result.answer)

    def test_customer_cannot_delete(self):
        result = ShoppingAgent(ToolHarness("customer")).run("Delete product 2")
        self.assertIn("cannot use", result.answer)

    def test_admin_can_delete(self):
        result = ShoppingAgent(ToolHarness("admin")).run("Delete product 4")
        self.assertEqual(result.answer, "Product deleted.")

    def test_validation_and_limit_return_controlled_errors(self):
        harness = ToolHarness("customer", max_tool_calls=1)
        self.assertEqual(harness.execute("check_stock", {"product_id": -1})["code"], "invalid_arguments")
        self.assertEqual(harness.execute("check_stock", {"product_id": 1})["code"], "limit_exceeded")

if __name__ == "__main__":
    unittest.main()
