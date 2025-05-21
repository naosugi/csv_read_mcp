import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Start MCP server for RSS System")
    parser.add_argument(
        "--mode",
        choices=["pandas", "db"],
        default="pandas",
        help="Server mode: pandas (default) or db (SQLite)"
    )
    args = parser.parse_args()

    if args.mode == "pandas":
        print("Starting MCP Server in Pandas mode...")
        os.system(f"{sys.executable} server_pandas.py")
    else:
        print("Starting MCP Server in SQLite DB mode...")
        os.system(f"{sys.executable} server_db.py")


if __name__ == "__main__":
    main()