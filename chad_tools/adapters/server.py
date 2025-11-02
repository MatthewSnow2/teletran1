"""Single adapter server with --adapter= flag.

Usage: python server.py --adapter=notion --port=8001

Deliverable #3: Single server.py with --adapter flag ✅
"""

import argparse


def main():
    """
    Run adapter server.

    TODO: Implement FastAPI server per adapter
    TODO: Load adapter-specific logic (notion.py, google.py, etc.)
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True, choices=["notion", "google", "github", "outlook", "supabase"])
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    print(f"🔌 Adapter server: {args.adapter} on port {args.port}")
    print("TODO: Implement adapter logic")


if __name__ == "__main__":
    main()
