from __future__ import annotations

import ast

ALLOWED_IMPORTS = {"pygame", "pandas", "numpy", "math", "csv", "datetime", "sys", "os", "json", "pathlib", "time", "glob"}
BANNED_NAMES = {"requests", "urllib", "yfinance", "socket", "http", "subprocess", "importlib", "shutil",
                "__import__", "eval", "exec", "compile"}


def validate_script(source: str) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    errors.append(f"import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module not in ALLOWED_IMPORTS:
                errors.append(f"import from '{node.module}' is not allowed")
            for alias in node.names:
                if alias.name in BANNED_NAMES:
                    errors.append(f"imported name '{alias.name}' is banned")
        elif isinstance(node, ast.Name):
            if node.id in BANNED_NAMES:
                errors.append(f"use of banned name '{node.id}'")
        elif isinstance(node, ast.Attribute):
            if node.attr in BANNED_NAMES:
                errors.append(f"use of banned attribute '{node.attr}'")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name == "open" or (name == "open" and isinstance(func, ast.Name)):
                errors.append("open() is not allowed in chart scripts")
            elif isinstance(func, ast.Attribute) and func.attr == "open":
                errors.append("file open() is not allowed in chart scripts")
    return errors
