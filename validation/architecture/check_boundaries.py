"""Validate a small set of dependency rules using Python's AST."""

import ast
from pathlib import Path

SOURCE_ROOTS = (
    Path("DataCollector/src"),
    Path("PaperTrading/src"),
    Path("AiTrainer/src"),
    Path("Dashboard/src"),
    Path("shared/src"),
)


def imported_modules(path: Path) -> set[str]:
    """Return absolute import targets without importing application code."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def boundary_violations() -> list[str]:
    """Return human-readable dependency violations."""
    violations: list[str] = []
    for root in SOURCE_ROOTS:
        for path in root.rglob("*.py"):
            imports = imported_modules(path)
            normalized = path.as_posix()

            if "/domain/" in normalized:
                forbidden = {
                    name
                    for name in imports
                    if name.startswith(("fastapi", "pydantic", "sqlalchemy"))
                }
                forbidden.update(name for name in imports if ".infrastructure" in name)
                if forbidden:
                    violations.append(f"{normalized}: domain imports {sorted(forbidden)}")

            if normalized.startswith("shared/src/shared/contracts/"):
                forbidden = {
                    name
                    for name in imports
                    if name.startswith(("fastapi", "pydantic", "sqlalchemy"))
                }
                if forbidden:
                    violations.append(f"{normalized}: shared contract imports {sorted(forbidden)}")

            if "/application/" in normalized:
                forbidden = {name for name in imports if ".infrastructure" in name}
                if forbidden:
                    violations.append(f"{normalized}: application imports {sorted(forbidden)}")

            if normalized.startswith("AiTrainer/"):
                forbidden = {
                    name for name in imports if name.startswith("paper_trading.infrastructure")
                }
                if forbidden:
                    violations.append(f"{normalized}: AiTrainer imports {sorted(forbidden)}")

            if normalized.startswith("DataCollector/"):
                forbidden = {name for name in imports if name.startswith("ai_trainer")}
                if forbidden:
                    violations.append(f"{normalized}: DataCollector imports {sorted(forbidden)}")

            if normalized.startswith("Dashboard/") and "/infrastructure/" not in normalized:
                forbidden = {
                    name
                    for name in imports
                    if name.startswith(("paper_trading.", "ai_trainer.", "data_collector."))
                }
                if forbidden:
                    violations.append(
                        f"{normalized}: Dashboard inner layer imports internals {sorted(forbidden)}"
                    )

            if "/bots/" in normalized:
                forbidden = {name for name in imports if "bitvavo" in name.lower()}
                if forbidden:
                    violations.append(f"{normalized}: bot imports {sorted(forbidden)}")
    return violations


if __name__ == "__main__":
    found = boundary_violations()
    if found:
        raise SystemExit("\n".join(found))
    print("Architecture boundaries are valid.")
