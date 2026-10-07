#!/usr/bin/env python3
"""Build scoped search links for manual review of public professional sources."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode


TOOL_NAME = "linkedin-recon"
SCHEMA_VERSION = 1
SEARCH_ENGINES = {
    "google": "https://www.google.com/search",
    "bing": "https://www.bing.com/search",
}
TECH_TERMS = (
    '"AWS" OR "Azure" OR "GCP" OR Kubernetes OR Terraform OR Ansible OR '
    "Python OR Go OR Java OR C# OR JavaScript OR TypeScript OR Ruby OR Rust OR "
    'React OR Django OR Spring OR Rails OR Laravel OR "Node.js" OR Angular'
)
DISCLAIMER = (
    "Search links only. Review results manually and follow source terms, "
    "applicable law, and your authorization."
)


def _clean_scope_value(value: str, label: str, limit: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must not be empty")
    if len(cleaned) > limit:
        raise ValueError(f"{label} must be no more than {limit} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError(f"{label} must not contain control characters")
    return cleaned


def _quoted_phrase(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _search_link(engine: str, query: str) -> str:
    return f"{SEARCH_ENGINES[engine]}?{urlencode({'q': query})}"


def build_search_plan(
    company: str,
    title: str = "Engineer",
    engine: str = "google",
    include_tech: bool = False,
) -> Dict[str, Any]:
    """Return a query plan; this function does not make network requests."""
    company = _clean_scope_value(company, "Company", 120)
    title = _clean_scope_value(title, "Title", 80)
    if engine not in SEARCH_ENGINES:
        raise ValueError(f"Unsupported search engine: {engine}")

    company_phrase = _quoted_phrase(company)
    profile_query = f"site:linkedin.com/in {company_phrase} {_quoted_phrase(title)}"
    searches: List[Dict[str, str]] = [
        {
            "type": "employee_profiles",
            "engine": engine,
            "query": profile_query,
            "url": _search_link(engine, profile_query),
        }
    ]
    if include_tech:
        tech_query = f"{company_phrase} jobs engineering ({TECH_TERMS})"
        searches.append(
            {
                "type": "job_posting_technology_signals",
                "engine": engine,
                "query": tech_query,
                "url": _search_link(engine, tech_query),
            }
        )

    return {
        "tool": TOOL_NAME,
        "schema_version": SCHEMA_VERSION,
        "scope": {"company": company, "title": title},
        "searches": searches,
        "notice": DISCLAIMER,
    }


def render_text(plan: Dict[str, Any]) -> str:
    scope = plan["scope"]
    lines = [
        f"Search plan for {scope['company']} — {scope['title']}",
        "No pages were fetched; open and review these search links manually.",
    ]
    for search in plan["searches"]:
        lines.extend(
            [
                "",
                f"[{search['type']}] via {search['engine']}",
                f"Query: {search['query']}",
                f"URL: {search['url']}",
            ]
        )
    lines.extend(["", plan["notice"]])
    return "\n".join(lines) + "\n"


def _write_atomically(path: Path, content: str) -> None:
    if not path.parent.is_dir():
        raise OSError(f"Output directory does not exist: {path.parent}")

    temp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            delete=False,
        ) as output:
            temp_path = output.name
            output.write(content)
        os.replace(temp_path, path)
    except OSError:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def _scope_argument(label: str, limit: int):
    def parse(value: str) -> str:
        try:
            return _clean_scope_value(value, label, limit)
        except ValueError as error:
            raise argparse.ArgumentTypeError(str(error))

    return parse


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build manually reviewed search links for public professional sources. "
            "This tool does not fetch search results or profile pages."
        ),
        epilog=DISCLAIMER,
    )
    parser.add_argument(
        "company",
        type=_scope_argument("Company", 120),
        help="Company name to include in the search scope",
    )
    parser.add_argument(
        "--title",
        default="Engineer",
        type=_scope_argument("Title", 80),
        help="Job title to include in the profile search (default: Engineer)",
    )
    parser.add_argument(
        "--engine",
        choices=sorted(SEARCH_ENGINES),
        default="google",
        help="Search engine whose query link to generate (default: google)",
    )
    parser.add_argument(
        "--tech",
        action="store_true",
        help="Also generate a search for technology terms in job postings",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write output to this file instead of standard output",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    plan = build_search_plan(args.company, args.title, args.engine, args.tech)
    content = (
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        if args.format == "json"
        else render_text(plan)
    )

    if args.out:
        try:
            _write_atomically(args.out, content)
        except OSError as error:
            print(f"linkedin-recon: could not write output: {error}", file=sys.stderr)
            return 2
        print(f"Search plan written to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
