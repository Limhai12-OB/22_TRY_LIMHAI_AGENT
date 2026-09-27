"""Command-line entry point for the safe shopping agent."""
import argparse
from agent import ShoppingAgent
from harness import ToolHarness

def main():
    parser = argparse.ArgumentParser(description="Run the safe shopping agent")
    parser.add_argument("request", nargs="*", help="Request, e.g. 'Find a laptop in stock'")
    parser.add_argument("--role", choices=("customer", "admin"), default="customer")
    parser.add_argument("--show-trace", action="store_true")
    args = parser.parse_args()
    request = " ".join(args.request).strip() or input("What would you like to do? ").strip()
    result = ShoppingAgent(ToolHarness(role=args.role)).run(request)
    if args.show_trace:
        for event in result.trace:
            print(f"[{event['type']}] {event['message']}")
        print()
    print(result.answer)

if __name__ == "__main__":
    main()
