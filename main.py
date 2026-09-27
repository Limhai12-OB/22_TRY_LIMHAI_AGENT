"""Command-line entry point for the safe shopping agent."""
import argparse
from agent import OllamaChatModel, ShoppingAgent
from harness import ToolHarness

def main():
    parser = argparse.ArgumentParser(description="Run the safe shopping agent")
    parser.add_argument("request", nargs="*", help="Request, e.g. 'Find a laptop in stock'")
    parser.add_argument("--role", choices=("customer", "admin"), default="customer")
    parser.add_argument("--show-trace", action="store_true")
    parser.add_argument("--model", default="llama3.2:3b", help="Local Ollama model name")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server URL")
    args = parser.parse_args()
    request = " ".join(args.request).strip() or input("What would you like to do? ").strip()
    model = OllamaChatModel(model=args.model, base_url=args.ollama_url)
    result = ShoppingAgent(ToolHarness(role=args.role), model=model).run(request)
    if args.show_trace:
        for event in result.trace:
            print(f"[{event['type']}] {event['message']}")
        print()
    print(result.answer)

if __name__ == "__main__":
    main()
