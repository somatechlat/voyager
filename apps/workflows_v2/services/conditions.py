"""Workflow condition expression engine.

Evaluates conditional expressions for branching logic including
comparisons, logical operators, method calls, and function calls.
"""

from __future__ import annotations

import ast
import logging
import operator
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ── Comparison operators ────────────────────────────────────────

_COMPARISON_OPS: dict[type, Callable[[Any, Any], bool]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

# ── Boolean operators ───────────────────────────────────────────

_BOOL_OPS: dict[type, Callable[[bool, bool], bool]] = {
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

# ── Unary operators ─────────────────────────────────────────────

_UNARY_OPS: dict[type, Callable[[Any], Any]] = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# ── Supported built-in functions ────────────────────────────────

_BUILTIN_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "LEN": len,
    "SUM": sum,
    "MIN": min,
    "MAX": max,
    "ABS": abs,
    "ROUND": round,
    "STR": str,
    "INT": int,
    "FLOAT": float,
    "BOOL": bool,
    "ANY": any,
    "ALL": all,
}


def evaluate_expression(expression: str, context: dict[str, Any]) -> Any:
    """Safely evaluate a condition expression against a context dict.

    Supports comparisons, logical operators, attribute access,
    method calls, and built-in functions (LEN, SUM, MIN, MAX, etc).

    Args:
        expression: The expression string (e.g. 'content.score >= 80').
        context: Variable bindings available during evaluation.

    Returns:
        The evaluated result (typically bool for conditions).

    Raises:
        ValueError: If the expression contains unsafe constructs.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression syntax: {exc}") from exc

    return _eval_node(tree.body, context)


def _eval_node(node: ast.AST, context: dict[str, Any]) -> Any:
    """Recursively evaluate an AST node."""
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, context) for v in node.values]
        op_func = _BOOL_OPS.get(type(node.op))
        if not op_func:
            raise ValueError(f"Unsupported boolean operator: {node.op}")
        result = values[0]
        for v in values[1:]:
            result = op_func(result, v)
        return result

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, context)
        op_func = _UNARY_OPS.get(type(node.op))
        if not op_func:
            raise ValueError(f"Unsupported unary operator: {node.op}")
        return op_func(operand)

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise ValueError(f"Unsupported binary operator: {node.op}")

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, context)
            op_func = _COMPARISON_OPS.get(type(op))
            if not op_func:
                raise ValueError(f"Unsupported comparison: {op}")
            result = result and op_func(left, right)
            left = right
        return result

    if isinstance(node, ast.Call):
        func_name = _get_call_name(node.func)
        if func_name and func_name.upper() in _BUILTIN_FUNCTIONS:
            args = [_eval_node(arg, context) for arg in node.args]
            kwargs = {kw.arg: _eval_node(kw.value, context) for kw in node.keywords}
            return _BUILTIN_FUNCTIONS[func_name.upper()](*args, **kwargs)

        # Method call on an object: obj.method(args)
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id
            method_name = node.func.attr
            obj = _resolve_name(obj_name, context)
            args = [_eval_node(arg, context) for arg in node.args]
            method = getattr(obj, method_name, None)
            if method and callable(method):
                return method(*args)
            raise ValueError(f"Method '{method_name}' not found on '{obj_name}'")

        raise ValueError(f"Unsupported function call: {func_name}")

    if isinstance(node, ast.Attribute):
        obj = _eval_node(node.value, context)
        if isinstance(obj, dict):
            return obj.get(node.attr)
        return getattr(obj, node.attr, None)

    if isinstance(node, ast.Subscript):
        obj = _eval_node(node.value, context)
        slice_val = _eval_node(node.slice, context)
        if isinstance(obj, (list, tuple, dict, str)):
            try:
                return obj[slice_val]
            except (IndexError, KeyError, TypeError):
                return None
        return None

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        return _resolve_name(node.id, context)

    if isinstance(node, ast.List):
        return [_eval_node(elt, context) for elt in node.elts]

    if isinstance(node, ast.Dict):
        return {
            _eval_node(k, context): _eval_node(v, context) for k, v in zip(node.keys, node.values)
        }

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def _get_call_name(node: ast.AST) -> str | None:
    """Extract a function name from an AST call node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _resolve_name(name: str, context: dict[str, Any]) -> Any:
    """Resolve a variable name from the context."""
    if name in context:
        return context[name]
    if name == "True":
        return True
    if name == "False":
        return False
    if name == "None":
        return None
    raise ValueError(f"Unknown variable: '{name}'")


def evaluate_condition_branch(
    condition_config: dict[str, Any],
    context: dict[str, Any],
) -> str:
    """Evaluate a condition node and return the branch to follow.

    The condition config contains an 'expression' and a list of
    'branches' with labels. Evaluates the expression and returns
    the matching branch label.

    Args:
        condition_config: Condition node configuration.
        context: Execution context.

    Returns:
        The branch label to follow (e.g. 'true' or 'false').
    """
    expression = condition_config.get("expression", "")
    branches = condition_config.get("branches", [])

    if not expression:
        # Default to first branch
        return branches[0]["label"] if branches else "default"

    try:
        result = evaluate_expression(expression, context)
        # Map result to branch label
        if isinstance(result, bool):
            label = "true" if result else "false"
        elif result is None:
            label = "null"
        else:
            label = str(result)

        # Check if label matches any branch
        branch_labels = {b.get("label", "") for b in branches}
        if label in branch_labels:
            return label
        # Default fallback
        return branches[0]["label"] if branches else "default"
    except Exception as exc:
        logger.error("Condition evaluation error: %s", exc)
        # On error, take the fallback branch (usually 'false')
        for branch in branches:
            if branch.get("is_default"):
                return branch["label"]
        return branches[0]["label"] if branches else "default"


def evaluate_loop_collection(
    loop_config: dict[str, Any],
    context: dict[str, Any],
) -> list[Any]:
    """Evaluate a loop node's collection expression.

    Args:
        loop_config: Loop node configuration.
        context: Execution context.

    Returns:
        The collection to iterate over.
    """
    collection_expr = loop_config.get("collection", "")
    if not collection_expr:
        return []

    try:
        result = evaluate_expression(collection_expr, context)
        if isinstance(result, (list, tuple)):
            return list(result)
        if isinstance(result, dict):
            return list(result.items())
        return [result]
    except Exception as exc:
        logger.error("Loop collection evaluation error: %s", exc)
        return []
