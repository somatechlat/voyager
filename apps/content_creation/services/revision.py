"""Revision history with word-level diffs and rollback.

Uses a simple diff algorithm to track changes between content versions.
Supports creating revisions, computing diffs, and rolling back.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _myers_diff(old: list[str], new: list[str]) -> list[dict[str, Any]]:
    """Compute the shortest edit script between two sequences.

    Implements Myers' diff algorithm (O(ND)) to find additions,
    deletions, and modifications between word lists.

    Args:
        old: Original word list.
        new: New word list.

    Returns:
        List of edit operations: {type, old_value, new_value, position}.
    """
    n, m = len(old), len(new)
    max_d = n + m
    if max_d == 0:
        return []

    # Store furthest-reaching paths for each diagonal
    v: dict[int, int] = {1: 0}
    trace: list[dict[int, int]] = []

    for d in range(max_d + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k
            while x < n and y < m and old[x] == new[y]:
                x += 1
                y += 1
            v[k] = x
            if x >= n and y >= m:
                return _backtrack(trace, old, new, d, k)
    return []


def _backtrack(
    trace: list[dict[int, int]],
    old: list[str],
    new: list[str],
    d_end: int,
    k_end: int,
) -> list[dict[str, Any]]:
    """Reconstruct the edit script from trace data."""
    edits: list[dict[str, Any]] = []
    x, y = len(old), len(new)

    for d in range(d_end, -1, -1):
        v = trace[d]
        k = k_end
        if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
            prev_k = k + 1
        else:
            prev_k = k - 1

        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k

        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1

        if d > 0:
            if x == prev_x:
                edits.append({
                    "type": "add",
                    "old_value": "",
                    "new_value": new[y - 1] if y > 0 else "",
                    "position": max(y - 1, 0),
                })
                y -= 1
            else:
                edits.append({
                    "type": "delete",
                    "old_value": old[x - 1] if x > 0 else "",
                    "new_value": "",
                    "position": max(x - 1, 0),
                })
                x -= 1

        k_end = prev_k

    edits.reverse()
    return edits


def diff_versions(old_text: str, new_text: str) -> dict[str, Any]:
    """Generate word-level diff between two text versions.

    Args:
        old_text: Previous version text.
        new_text: Current version text.

    Returns:
        Dict with additions, deletions, modifications, and summary.
    """
    old_words = old_text.split()
    new_words = new_text.split()

    diff = _myers_diff(old_words, new_words)

    additions = [d for d in diff if d["type"] == "add"]
    deletions = [d for d in diff if d["type"] == "delete"]
    modifications = [d for d in diff if d["type"] == "modify"]

    max_words = max(len(old_words), len(new_words), 1)
    change_count = len(additions) + len(deletions) + len(modifications)
    change_pct = (change_count / max_words) * 100

    return {
        "additions": additions,
        "deletions": deletions,
        "modifications": modifications,
        "summary": {
            "words_added": len(additions),
            "words_deleted": len(deletions),
            "words_modified": len(modifications),
            "change_percentage": round(change_pct, 2),
            "old_word_count": len(old_words),
            "new_word_count": len(new_words),
        },
    }


def create_revision(
    content_generation_id: str,
    version_number: int,
    old_text: str,
    new_text: str,
    changed_by: str,
    change_summary: str = "",
) -> dict[str, Any]:
    """Create a new revision entry with diff.

    Args:
        content_generation_id: UUID of the content generation.
        version_number: Sequential version number.
        old_text: Previous version body text.
        new_text: New version body text.
        changed_by: UUID of the user who made the change.
        change_summary: Human-readable change summary.

    Returns:
        Dict with revision data ready for DB insertion.
    """
    diff = diff_versions(old_text, new_text)

    return {
        "content_generation_id": content_generation_id,
        "version_number": version_number,
        "diff_json": diff,
        "body_text": new_text,
        "changed_by": changed_by,
        "change_summary": change_summary
        or f"v{version_number}: {diff['summary']['words_added']} added, "
           f"{diff['summary']['words_deleted']} deleted, "
           f"{diff['summary']['change_percentage']}% changed",
    }


def rollback_to_revision(
    revisions: list[dict[str, Any]],
    target_version: int,
) -> dict[str, Any]:
    """Determine the body text at a specific historical version.

    Walks forward from the earliest revision to reconstruct the text
    at the target version.  Does not modify the database.

    Args:
        revisions: Ordered list of revision dicts (body_text, version_number, ...).
        target_version: Version to roll back to.

    Returns:
        Dict with body_text at target version and metadata.
    """
    sorted_revs = sorted(revisions, key=lambda r: r.get("version_number", 0))

    # Find the revision with the target version or the closest prior one
    body = ""
    for rev in sorted_revs:
        if rev.get("version_number", 0) <= target_version:
            body = rev.get("body_text", "")
        else:
            break

    return {
        "body_text": body,
        "target_version": target_version,
        "available_versions": [r.get("version_number") for r in sorted_revs],
    }
