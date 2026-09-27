"""Business logic for the shopping tools."""
from schemas import CheckStockInput, DeleteProductInput, SearchProductsInput

PRODUCTS = {
    1: {"name": "Everyday Laptop", "category": "laptop", "price": 699.00, "stock": 0},
    2: {"name": "Developer Laptop", "category": "laptop", "price": 1299.00, "stock": 5},
    3: {"name": "Wireless Mouse", "category": "accessory", "price": 29.00, "stock": 14},
    4: {"name": "Mechanical Keyboard", "category": "accessory", "price": 89.00, "stock": 3},
}

def search_products(args):
    words = args.query.strip().lower().split()
    matches = [{"id": key, "name": value["name"], "price": value["price"]} for key, value in PRODUCTS.items() if all(word in f"{value['name']} {value['category']}".lower() for word in words)]
    return {"products": matches}

def check_stock(args):
    product = PRODUCTS.get(args.product_id)
    if product is None:
        raise LookupError(f"product {args.product_id} was not found")
    return {"product_id": args.product_id, "name": product["name"], "stock": product["stock"]}

def delete_product(args):
    product = PRODUCTS.pop(args.product_id, None)
    if product is None:
        raise LookupError(f"product {args.product_id} was not found")
    return {"deleted": True, "product_id": args.product_id, "name": product["name"]}
