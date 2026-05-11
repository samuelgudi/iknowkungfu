"""Example script — no network, no secrets, no dynamic-code-eval builtins."""
import json
import sys


def main():
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    sys.exit(main() or 0)
