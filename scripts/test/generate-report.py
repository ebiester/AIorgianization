#!/usr/bin/env python3
"""
generate-report.py - Generate combined test report with UAT coverage.

Aggregates results from Python, TypeScript, and MCP tests into:
- combined-report.md: Human-readable markdown report
- uat-coverage.json: Machine-readable UAT coverage (extracted from markers)
- manual-test-checklist.md: Checklist for manual tests
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def load_json_file(path: Path) -> dict:
    """Load a JSON file, returning empty dict if not found."""
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def extract_uat_markers_from_source(project_root: Path) -> dict[str, list[str]]:
    """Extract UAT markers directly from source files.

    Returns a mapping of test function names to their UAT IDs.
    """
    uat_map: dict[str, list[str]] = {}  # test_name -> [UAT-001, UAT-002, ...]

    tests_dir = project_root / "tests"
    if not tests_dir.exists():
        return uat_map

    # Scan all Python test files
    for test_file in tests_dir.rglob("test_*.py"):
        content = test_file.read_text()

        # Find all @pytest.mark.uat('UAT-XXX') decorators followed by def test_xxx
        # Pattern matches decorator and the following function
        pattern = r'@pytest\.mark\.uat\(["\']?(UAT-\d+)["\']?\).*?def (test_\w+)'
        matches = re.findall(pattern, content, re.DOTALL)

        for uat_id, func_name in matches:
            if func_name not in uat_map:
                uat_map[func_name] = []
            uat_map[func_name].append(uat_id)

    return uat_map


def extract_uat_markers(python_results: dict, project_root: Path = None) -> dict[str, list[dict]]:
    """Extract UAT markers from pytest JSON report combined with source parsing."""
    uat_coverage: dict[str, list[dict]] = {}

    # First, get UAT markers from source files
    if project_root is None:
        project_root = Path.cwd()
    source_uat_map = extract_uat_markers_from_source(project_root)

    tests = python_results.get("tests", [])
    for test in tests:
        node_id = test.get("nodeid", "")
        outcome = test.get("outcome", "")
        passed = outcome == "passed"

        # Extract function name from node_id (e.g., "tests/integration/test_cli.py::TestAddCommand::test_add_task")
        func_name = node_id.split("::")[-1] if "::" in node_id else ""

        # Check if this test has UAT markers from source
        if func_name in source_uat_map:
            for uat_id in source_uat_map[func_name]:
                if uat_id not in uat_coverage:
                    uat_coverage[uat_id] = []
                uat_coverage[uat_id].append({
                    "test": node_id,
                    "type": "python",
                    "passed": passed,
                })
            continue

        # Fallback: check keywords for 'uat' marker presence
        # (This won't have the UAT ID, but indicates test has uat marker)
        keywords = test.get("keywords", [])
        if "uat" in keywords:
            # We can't get the UAT ID from keywords alone
            # Skip or log this case
            pass

    return uat_coverage


def summarize_python_results(results: dict) -> dict:
    """Summarize Python test results."""
    summary = results.get("summary", {})
    return {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "error": summary.get("error", 0),
        "skipped": summary.get("skipped", 0),
    }


def summarize_typescript_results(results: dict) -> dict:
    """Summarize TypeScript test results."""
    test_results = results.get("testResults", [])
    total = 0
    passed = 0
    failed = 0

    for tr in test_results:
        for assertion in tr.get("assertionResults", []):
            total += 1
            if assertion.get("status") == "passed":
                passed += 1
            else:
                failed += 1

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
    }


def summarize_mcp_results(results: dict) -> dict:
    """Summarize MCP test results."""
    return {
        "total": results.get("total", 0),
        "passed": results.get("passed", 0),
        "failed": results.get("failed", 0),
    }


def generate_markdown_report(
    python_results: dict,
    typescript_results: dict,
    mcp_results: dict,
    uat_coverage: dict[str, list[dict]],
) -> str:
    """Generate combined markdown report."""
    py_summary = summarize_python_results(python_results)
    ts_summary = summarize_typescript_results(typescript_results)
    mcp_summary = summarize_mcp_results(mcp_results)

    lines = [
        "# AIorgianization Test Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "### Python Tests (pytest)",
        "",
        f"- Total: {py_summary['total']}",
        f"- Passed: {py_summary['passed']}",
        f"- Failed: {py_summary['failed']}",
        f"- Errors: {py_summary['error']}",
        f"- Skipped: {py_summary['skipped']}",
        "",
        "### TypeScript Tests (vitest)",
        "",
        f"- Total: {ts_summary['total']}",
        f"- Passed: {ts_summary['passed']}",
        f"- Failed: {ts_summary['failed']}",
        "",
        "### MCP Server Tests",
        "",
        f"- Total: {mcp_summary['total']}",
        f"- Passed: {mcp_summary['passed']}",
        f"- Failed: {mcp_summary['failed']}",
        "",
        "---",
        "",
        "## UAT Coverage",
        "",
        "Tests marked with `@pytest.mark.uat('UAT-XXX')` are mapped below.",
        "",
        "| UAT ID | Tests | Status |",
        "|--------|-------|--------|",
    ]

    # Sort UAT IDs
    for uat_id in sorted(uat_coverage.keys()):
        tests = uat_coverage[uat_id]
        all_passed = all(t["passed"] for t in tests)
        status = "PASS" if all_passed else "FAIL"
        test_count = len(tests)
        lines.append(f"| {uat_id} | {test_count} test(s) | {status} |")

    if not uat_coverage:
        lines.append("| (No UAT markers found) | - | - |")

    # Failed tests section
    failed_tests = []
    for test in python_results.get("tests", []):
        if test.get("outcome") != "passed":
            failed_tests.append(test)

    if failed_tests:
        lines.extend([
            "",
            "---",
            "",
            "## Failed Tests",
            "",
        ])
        for test in failed_tests:
            node_id = test.get("nodeid", "unknown")
            outcome = test.get("outcome", "unknown")
            lines.append(f"- `{node_id}` ({outcome})")

    # MCP test details
    if mcp_results.get("tests"):
        lines.extend([
            "",
            "---",
            "",
            "## MCP Test Details",
            "",
        ])
        for test in mcp_results["tests"]:
            name = test.get("name", "unknown")
            passed = test.get("passed", False)
            status = "PASS" if passed else "FAIL"
            lines.append(f"- [{status}] {name}")
            if test.get("error"):
                lines.append(f"  - Error: {test['error']}")

    return "\n".join(lines)


def generate_manual_checklist() -> str:
    """Generate manual test checklist for Obsidian plugin tests."""
    manual_tests = [
        {
            "id": "UAT-036",
            "name": "Plugin Installation",
            "steps": [
                "Copy plugin files to `.obsidian/plugins/obsidian-aio/`",
                "Restart Obsidian",
                "Enable plugin in Community Plugins list",
            ],
        },
        {
            "id": "UAT-037",
            "name": "Plugin Settings",
            "steps": [
                "Open Settings -> Community Plugins -> AIo",
                "Configure folder paths",
                "Restart Obsidian and verify settings persist",
            ],
        },
        {
            "id": "UAT-038",
            "name": "Task List View",
            "steps": [
                "Cmd+P -> 'AIo: Open task list'",
                "Verify task list pane opens",
                "Click 'Inbox (N)' filter",
                "Verify only inbox tasks are shown",
            ],
        },
        {
            "id": "UAT-039",
            "name": "Quick Add Modal",
            "steps": [
                "Cmd+P -> 'AIo: Add task'",
                "Type 'Test task -d tomorrow'",
                "Verify preview shows parsed date",
                "Press Enter to create task",
                "Press Esc on new modal to cancel",
            ],
        },
        {
            "id": "UAT-040",
            "name": "Add to Inbox Modal",
            "steps": [
                "Cmd+P -> 'AIo: Add to inbox'",
                "Type title and press Enter",
                "Verify task created in inbox",
            ],
        },
        {
            "id": "UAT-041",
            "name": "Task Edit Modal",
            "steps": [
                "Click a task in list view",
                "Verify all fields are visible",
                "Edit title and due date",
                "Press Cmd+Enter to save",
                "Verify changes persisted to file",
            ],
        },
        {
            "id": "UAT-042",
            "name": "Status Commands",
            "steps": [
                "Select task, Cmd+P -> 'AIo: Complete task'",
                "Verify task marked completed",
                "Select task, Cmd+P -> 'AIo: Start task'",
                "Verify task moved to Next",
                "Select task, Cmd+P -> 'AIo: Defer task'",
                "Verify task moved to Someday",
            ],
        },
        {
            "id": "UAT-043",
            "name": "Inbox Processing View",
            "steps": [
                "Create several inbox items",
                "Open Inbox view in plugin",
                "Click 'Next Action' on first item",
                "Verify item moves to Next, shows next inbox item",
                "Process all items",
                "Verify 'Inbox Zero!' message appears",
            ],
        },
    ]

    lines = [
        "# AIorgianization Manual Test Checklist",
        "",
        "Use this checklist for Obsidian plugin tests that cannot be automated.",
        "",
        "---",
        "",
    ]

    for test in manual_tests:
        lines.extend([
            f"## [ ] {test['id']}: {test['name']}",
            "",
            "**Steps:**",
        ])
        for i, step in enumerate(test["steps"], 1):
            lines.append(f"{i}. [ ] {step}")
        lines.extend([
            "",
            "**Result:** _________________",
            "",
            "**Notes:**",
            "",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate combined test report")
    parser.add_argument("--results-dir", default="test-results", help="Directory containing test results")
    parser.add_argument("--output-dir", default="test-results", help="Output directory for reports")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load results
    python_results = load_json_file(results_dir / "python-results.json")
    typescript_results = load_json_file(results_dir / "typescript-results.json")
    mcp_results = load_json_file(results_dir / "mcp-results.json")

    # Extract UAT markers (parse source files for UAT IDs)
    project_root = results_dir.parent if results_dir.name == "test-results" else results_dir.parent
    uat_coverage = extract_uat_markers(python_results, project_root)

    # Generate reports
    report = generate_markdown_report(
        python_results, typescript_results, mcp_results, uat_coverage
    )
    (output_dir / "combined-report.md").write_text(report)

    # Save UAT coverage
    (output_dir / "uat-coverage.json").write_text(json.dumps(uat_coverage, indent=2))

    # Generate manual checklist
    checklist = generate_manual_checklist()
    (output_dir / "manual-test-checklist.md").write_text(checklist)

    print(f"Reports generated in {output_dir}:")
    print(f"  - combined-report.md")
    print(f"  - uat-coverage.json")
    print(f"  - manual-test-checklist.md")


if __name__ == "__main__":
    main()
