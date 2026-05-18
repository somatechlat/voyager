"""Content repurposing — transform content between formats.

Implements transformation rules from the spec CA-009:
blog -> thread, blog -> linkedin, blog -> carousel, video -> blog,
video -> clips, podcast -> newsletter, podcast -> blog, newsletter -> social.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform limits for repurposed content
# ---------------------------------------------------------------------------

PLATFORM_LIMITS: dict[str, int] = {
    "twitter": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "tiktok": 2200,
    "facebook": 63206,
    "email": 10000,
}

# ---------------------------------------------------------------------------
# Transformation engines
# ---------------------------------------------------------------------------


def _extract_headers(text: str) -> list[dict[str, Any]]:
    """Extract H2/H3 headers and their content sections from markdown/HTML.

    Args:
        text: Blog post text with headers.

    Returns:
        List of section dicts with header and body.
    """
    # Match ## or ### headers
    pattern = r"^(#{2,3})\s+(.+)$"
    lines = text.split("\n")
    sections = []
    current_header = "Introduction"
    current_body: list[str] = []

    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            if current_body:
                sections.append(
                    {
                        "header": current_header,
                        "body": "\n".join(current_body).strip(),
                    }
                )
            current_header = match.group(2)
            current_body = []
        else:
            current_body.append(line)

    if current_body or not sections:
        sections.append(
            {
                "header": current_header,
                "body": "\n".join(current_body).strip(),
            }
        )
    return sections


def _blog_to_twitter_thread(text: str) -> list[dict[str, Any]]:
    """Convert a blog post to a Twitter thread.

    Each H2/H3 section becomes a tweet.  Long sections are split at
    260 chars to leave room for thread numbering.

    Args:
        text: Blog post text.

    Returns:
        List of tweet dicts with text and character count.
    """
    sections = _extract_headers(text)
    tweets = []
    for i, section in enumerate(sections, start=1):
        header = section["header"]
        body = section["body"][:200]  # truncated body
        tweet_text = f"{header}\n\n{body}"[:260]
        tweets.append(
            {
                "tweet_number": i,
                "text": tweet_text,
                "character_count": len(tweet_text),
            }
        )
    return tweets


def _blog_to_linkedin(text: str) -> dict[str, Any]:
    """Convert a blog post to a LinkedIn post.

    Extracts key insights, adds a professional engagement hook.

    Args:
        text: Blog post text.

    Returns:
        Dict with transformed text and metadata.
    """
    sections = _extract_headers(text)
    key_points = []
    for s in sections[:5]:
        sentence = s["body"].split(".")[0][:120] if s["body"] else s["header"]
        key_points.append(f"• {sentence}")

    hook = "Here are my key insights on this topic:\n\n"
    body = "\n".join(key_points)
    cta = "\n\nWhat are your thoughts? Share in the comments below."
    transformed = (hook + body + cta)[: PLATFORM_LIMITS.get("linkedin", 3000)]

    return {
        "transformed_text": transformed,
        "character_count": len(transformed),
        "key_points": len(key_points),
    }


def _blog_to_instagram_carousel(text: str) -> list[dict[str, Any]]:
    """Convert a blog post to Instagram carousel slides.

    Each H2 section becomes a slide with a title and short body.

    Args:
        text: Blog post text.

    Returns:
        List of slide dicts.
    """
    sections = _extract_headers(text)
    slides = []
    for i, section in enumerate(sections[:10], start=1):
        body = section["body"][:150]
        slide_text = f"{section['header']}\n\n{body}"
        slides.append(
            {
                "slide_number": i,
                "title": section["header"],
                "body": body,
                "text": slide_text,
                "character_count": len(slide_text),
            }
        )
    return slides


def _video_to_blog(text: str) -> dict[str, Any]:
    """Convert a video transcript to a blog post.

    Cleans up transcript, adds structure with headers.

    Args:
        text: Video transcript.

    Returns:
        Dict with blog text and metadata.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    sections = []
    for i, para in enumerate(paragraphs):
        if i == 0:
            sections.append(f"# Introduction\n\n{para}")
        else:
            header = f"Section {i}"
            first_sentence = para.split(".")[0][:60]
            if first_sentence:
                header = first_sentence
            sections.append(f"## {header}\n\n{para}")

    blog_text = "\n\n".join(sections)
    return {
        "transformed_text": blog_text,
        "character_count": len(blog_text),
        "section_count": len(sections),
    }


def _newsletter_to_social(text: str) -> dict[str, Any]:
    """Convert a newsletter to a social post.

    Extracts the top 3 insights and creates an engagement hook.

    Args:
        text: Newsletter text.

    Returns:
        Dict with social post text and metadata.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    top_insights = paragraphs[:3]
    lines = ["Here are 3 key takeaways:\n"]
    for i, insight in enumerate(top_insights, 1):
        summary = insight.split(".")[0][:100]
        lines.append(f"{i}. {summary}")
    lines.append("\nWhich one resonates most with you?")
    transformed = "\n\n".join(lines)[: PLATFORM_LIMITS.get("instagram", 2200)]
    return {
        "transformed_text": transformed,
        "character_count": len(transformed),
        "insights": len(top_insights),
    }


def _podcast_to_newsletter(text: str) -> dict[str, Any]:
    """Convert a podcast transcript to a newsletter.

    Extracts key points and formats as an email.

    Args:
        text: Podcast transcript.

    Returns:
        Dict with newsletter text and metadata.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    lines = ["# This Week's Episode Highlights\n"]
    for para in paragraphs[:8]:
        first = para.split(".")[0][:80]
        if first:
            lines.append(f"• {first}")
    lines.append("\n---\nListen to the full episode for more insights.")
    transformed = "\n\n".join(lines)[: PLATFORM_LIMITS.get("email", 10000)]
    return {
        "transformed_text": transformed,
        "character_count": len(transformed),
        "highlights": len(lines) - 3,
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_TRANSFORMATION_MAP: dict[tuple[str, str], Any] = {
    ("blog", "twitter"): _blog_to_twitter_thread,
    ("blog", "linkedin"): _blog_to_linkedin,
    ("blog", "instagram"): _blog_to_instagram_carousel,
    ("video", "blog"): _video_to_blog,
    ("newsletter", "social"): _newsletter_to_social,
    ("newsletter", "instagram"): _newsletter_to_social,
    ("podcast", "newsletter"): _podcast_to_newsletter,
    ("podcast", "blog"): _video_to_blog,
}


def repurpose_content(
    source_text: str,
    source_format: str,
    target_format: str,
    transformation_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform content from one format to another.

    Routes to the appropriate transformation function based on source
    and target format pair.  Falls back to a generic truncation approach
    when no specific rule exists.

    Args:
        source_text: Original content text.
        source_format: Input format (blog, video, podcast, newsletter, social).
        target_format: Desired output format.
        transformation_rules: Optional override rules.

    Returns:
        Dict with transformed_text, warnings, and metadata.
    """
    warnings: list[str] = []
    key = (source_format.lower(), target_format.lower())
    handler = _TRANSFORMATION_MAP.get(key)

    if handler:
        result = handler(source_text)
        if isinstance(result, list):
            # e.g. thread or carousel
            transformed = "\n\n---\n\n".join(item.get("text", str(item)) for item in result)
            return {
                "source_format": source_format,
                "target_format": target_format,
                "transformed_text": transformed,
                "character_count": len(transformed),
                "warnings": warnings,
                "items": result,
            }
        return {
            "source_format": source_format,
            "target_format": target_format,
            "transformed_text": result.get("transformed_text", ""),
            "character_count": result.get("character_count", 0),
            "warnings": warnings,
            **{k: v for k, v in result.items() if k not in ("transformed_text", "character_count")},
        }

    # Generic fallback: apply platform limit truncation
    limit = PLATFORM_LIMITS.get(target_format.lower())
    transformed = source_text
    if limit and len(transformed) > limit:
        transformed = transformed[: limit - 3] + "..."
        warnings.append(
            f"No specific rule for {source_format} -> {target_format}; "
            f"applied generic truncation to {limit} chars"
        )
    else:
        warnings.append(
            f"No specific transformation rule for "
            f"{source_format} -> {target_format}; passthrough"
        )

    return {
        "source_format": source_format,
        "target_format": target_format,
        "transformed_text": transformed,
        "character_count": len(transformed),
        "warnings": warnings,
    }
