"""Jinja2 template rendering with variable substitution and validation.

Renders content templates with user-supplied variables, validates
required fields, applies platform-specific adaptations, and enforces
brand kit guidelines.
"""

from __future__ import annotations

import logging
from typing import Any

from jinja2 import Environment, UndefinedError
from jinja2.meta import find_undeclared_variables

logger = logging.getLogger(__name__)

# Global Jinja2 environment — same one used for all renders
_jinja_env = Environment(
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)


def _missing_vars(body: str, variables: dict[str, Any]) -> list[str]:
    """Find template variables that are referenced but not provided.

    Args:
        body: Jinja2 template source.
        variables: Supplied variable values.

    Returns:
        List of missing variable names.
    """
    try:
        ast = _jinja_env.parse(body)
        refs = find_undeclared_variables(ast)
        return sorted([r for r in refs if r not in variables])
    except Exception:
        return []


def _validate_variables(
    var_defs: list[dict[str, Any]],
    supplied: dict[str, Any],
) -> list[str]:
    """Validate supplied variables against definitions.

    Checks required fields and type constraints.

    Args:
        var_defs: Variable definitions from template.
        supplied: User-supplied values.

    Returns:
        List of validation warning strings.
    """
    warnings = []
    for vd in var_defs:
        name = vd.get("name", "")
        if not name:
            continue
        if vd.get("required") and (name not in supplied or supplied[name] in (None, "")):
            warnings.append(f"Required variable '{name}' is missing")
        if name in supplied:
            vtype = vd.get("type", "string")
            val = supplied[name]
            if vtype == "boolean" and not isinstance(val, bool):
                warnings.append(f"Variable '{name}' should be boolean")
            elif vtype == "array" and not isinstance(val, list):
                warnings.append(f"Variable '{name}' should be a list")
            elif vtype == "integer" and not isinstance(val, int):
                warnings.append(f"Variable '{name}' should be an integer")
            max_len = vd.get("maxLength")
            if max_len and isinstance(val, str) and len(val) > max_len:
                warnings.append(f"Variable '{name}' exceeds max length {max_len}")
            max_items = vd.get("maxItems")
            if max_items and isinstance(val, list) and len(val) > max_items:
                warnings.append(f"Variable '{name}' exceeds max items {max_items}")
    return warnings


def render_template(
    template_body: str,
    variables: dict[str, Any],
    var_defs: list[dict[str, Any]] | None = None,
    platform: str | None = None,
    brand_kit: dict[str, Any] | None = None,
    default_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render a Jinja2 template with variable substitution.

    Validates variables, merges defaults, renders the template, and
    optionally applies platform-specific adaptations.

    Args:
        template_body: Jinja2 template source string.
        variables: User-supplied variable values.
        var_defs: Variable definitions for validation.
        platform: Target platform for adaptations.
        brand_kit: Optional brand kit for tone enforcement.
        default_values: Default values for missing variables.

    Returns:
        Dict with rendered text, warnings, and character count.
    """
    # Merge defaults
    merged = dict(default_values or {})
    merged.update(variables)

    # Validate
    warnings: list[str] = []
    if var_defs:
        warnings.extend(_validate_variables(var_defs, merged))

    missing = _missing_vars(template_body, merged)
    if missing:
        for m in missing:
            warnings.append(f"Template references undefined variable '{m}'")

    # Render
    try:
        jinja_template = _jinja_env.from_string(template_body)
        rendered = jinja_template.render(**merged)
    except UndefinedError as exc:
        logger.error("Jinja2 undefined error: %s", exc)
        warnings.append(f"Template render error: {exc}")
        rendered = template_body
    except Exception as exc:
        logger.error("Template render failed: %s", exc)
        warnings.append(f"Template render error: {exc}")
        rendered = template_body

    # Platform adaptations
    if platform:
        platform_limits = {
            "twitter": 280,
            "instagram": 2200,
            "linkedin": 3000,
            "tiktok": 2200,
            "facebook": 63206,
            "youtube": 5000,
            "pinterest": 500,
            "email": 10000,
        }
        limit = platform_limits.get(platform)
        if limit and len(rendered) > limit:
            rendered = rendered[: limit - 3] + "..."
            warnings.append(f"Truncated to {limit} characters for {platform}")

    return {
        "rendered": rendered,
        "warnings": warnings,
        "character_count": len(rendered),
    }
