"""Email template builder and responsive rendering service.

Handles drag-drop block rendering, responsive CSS generation,
inline CSS for email client compatibility, and plain-text fallback.
"""

from __future__ import annotations

import html
import re
from typing import Any

# ---------------------------------------------------------------------------
# Responsive CSS
# ---------------------------------------------------------------------------

RESPONSIVE_BASE = """
body { margin: 0; padding: 0; background-color: #f4f4f4; }
.email-wrapper { width: 100%; max-width: 600px; margin: 0 auto; background: #ffffff; }
.email-wrapper img { max-width: 100%; height: auto; display: block; }
.email-wrapper a { color: #1a73e8; text-decoration: none; }
@media only screen and (max-width: 599px) {
  .email-wrapper { width: 100% !important; }
  .col { display: block !important; width: 100% !important; }
  .btn { width: 100% !important; display: block !important; text-align: center !important; }
  .mobile-hide { display: none !important; }
  .mobile-center { text-align: center !important; }
  .mobile-pad { padding: 16px !important; }
}
""".strip()


def generate_responsive_css(
    brand_kit: dict[str, Any] | None = None,
    extra_css: str = "",
) -> str:
    """Generate responsive CSS for email templates.

    Merges brand colors and fonts into the base responsive stylesheet.

    Args:
        brand_kit: Optional brand colors and fonts.
        extra_css: Additional CSS to append.

    Returns:
        Complete CSS string with media queries.
    """
    css_parts = [RESPONSIVE_BASE]
    if brand_kit:
        primary = brand_kit.get("primary_color", "#1a73e8")
        font = brand_kit.get("font_family", "Arial, Helvetica, sans-serif")
        css_parts.append(".brand-primary { color: " + primary + "; }")
        css_parts.append(".email-wrapper { font-family: " + font + "; }")
    if extra_css:
        css_parts.append(extra_css)
    return "\n".join(css_parts)


# ---------------------------------------------------------------------------
# Block renderers - helper for building html tags
# ---------------------------------------------------------------------------


def _tag(tag_name: str, content: str = "", **attrs: str) -> str:
    """Build an HTML tag with attributes."""
    attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items() if v)
    if attr_str:
        attr_str = " " + attr_str
    if content:
        return "<" + tag_name + attr_str + ">" + content + "</" + tag_name + ">"
    return "<" + tag_name + attr_str + " />"


def _div(content: str = "", **style: str) -> str:
    """Build a styled div."""
    style_str = ";".join("{}:{}".format(k.replace("_", "-"), v) for k, v in style.items())
    return _tag("div", content, style=style_str)


def _render_header(block: dict[str, Any]) -> str:
    """Render header block with preheader and logo."""
    preheader = html.escape(block.get("preheader", ""))
    logo_url = block.get("logo_url", "")
    logo_alt = html.escape(block.get("logo_alt", ""))
    alignment = block.get("alignment", "center")
    bg_color = block.get("bg_color", "#ffffff")
    style = block.get("style", {})
    padding = style.get("padding", "20px")
    parts = []
    if preheader:
        pre_tag = (
            '<div class="preheader" style="display:none;font-size:1px;color:#ffffff;'
            'line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">'
            + preheader
            + "</div>"
        )
        parts.append(pre_tag)
    inner = ""
    if logo_url:
        inner = (
            '<img src="'
            + html.escape(logo_url)
            + '" alt="'
            + logo_alt
            + '" style="max-width:200px;height:auto;display:inline-block;" />'
        )
    parts.append(
        '<div style="text-align:'
        + alignment
        + ";padding:"
        + padding
        + ";background-color:"
        + bg_color
        + ';">'
        + inner
        + "</div>"
    )
    return "\n".join(parts)


def _render_text(block: dict[str, Any]) -> str:
    """Render text block with rich formatting."""
    content = block.get("content", "")
    style = block.get("style", {})
    font_size = style.get("fontSize", 16)
    color = style.get("color", "#333333")
    alignment = style.get("alignment", "left")
    line_height = style.get("lineHeight", 1.5)
    font_family = style.get("fontFamily", "Arial, Helvetica, sans-serif")
    padding = style.get("padding", "16px 20px")
    return (
        '<div class="mobile-pad" style="padding:'
        + str(padding)
        + ";font-size:"
        + str(font_size)
        + "px;color:"
        + str(color)
        + ";text-align:"
        + str(alignment)
        + ";line-height:"
        + str(line_height)
        + ";font-family:"
        + str(font_family)
        + ';">'
        + str(content)
        + "</div>"
    )


def _render_image(block: dict[str, Any]) -> str:
    """Render image block."""
    src = html.escape(block.get("src", ""))
    alt = html.escape(block.get("alt", ""))
    width = block.get("width", "100%")
    link = block.get("link", "")
    border_radius = block.get("border_radius", 0)
    style = block.get("style", {})
    padding = style.get("padding", "0")
    img_html = (
        '<img src="'
        + src
        + '" alt="'
        + alt
        + '" style="width:'
        + str(width)
        + ";height:auto;display:block;border-radius:"
        + str(border_radius)
        + 'px;" />'
    )
    if link:
        img_html = '<a href="' + html.escape(link) + '">' + img_html + "</a>"
    return '<div style="padding:' + str(padding) + ';text-align:center;">' + img_html + "</div>"


def _render_button(block: dict[str, Any]) -> str:
    """Render CTA button block."""
    text = html.escape(block.get("text", "Click Here"))
    url = html.escape(block.get("url", "#"))
    btn_color = block.get("bg_color", "#1a73e8")
    text_color = block.get("color", "#ffffff")
    border_radius = block.get("border_radius", 4)
    size = block.get("size", "medium")
    style = block.get("style", {})
    padding = style.get("padding", "16px 20px")
    font_size = {"small": 14, "medium": 16, "large": 18}.get(size, 16)
    btn_html = (
        '<a href="' + url + '" class="btn" style="display:inline-block;padding:14px 32px;'
        "background-color:"
        + btn_color
        + ";color:"
        + text_color
        + ";text-decoration:none;border-radius:"
        + str(border_radius)
        + "px;font-size:"
        + str(font_size)
        + 'px;font-weight:600;font-family:Arial,Helvetica,sans-serif;">'
        + text
        + "</a>"
    )
    return (
        '<div class="mobile-pad" style="padding:'
        + str(padding)
        + ';text-align:center;">'
        + btn_html
        + "</div>"
    )


def _render_divider(block: dict[str, Any]) -> str:
    """Render divider block."""
    style = block.get("style", {})
    divider_style = block.get("divider_style", "solid")
    color = style.get("color", "#dddddd")
    width = style.get("width", "100%")
    margin = style.get("margin", "20px auto")
    return (
        '<div style="margin:'
        + str(margin)
        + ";width:"
        + str(width)
        + ';"><hr style="border:none;border-top:1px '
        + divider_style
        + " "
        + color
        + ';" /></div>'
    )


def _render_spacer(block: dict[str, Any]) -> str:
    """Render spacer block."""
    height = block.get("height", 20)
    return '<div style="height:' + str(height) + 'px;">&nbsp;</div>'


def _render_columns(block: dict[str, Any]) -> str:
    """Render multi-column layout block."""
    columns = block.get("columns", [])
    style = block.get("style", {})
    padding = style.get("padding", "0 20px")
    if not columns:
        return ""
    col_count = len(columns)
    col_width = 100 // col_count
    parts = ['<div style="padding:' + str(padding) + ';display:table;width:100%;">']
    for col in columns:
        parts.append('<div class="col" style="display:table-cell;width:' + str(col_width) + '%;">')
        for child in col.get("blocks", []):
            parts.append(render_block(child))
        parts.append("</div>")
    parts.append("</div>")
    return "\n".join(parts)


def _render_social(block: dict[str, Any]) -> str:
    """Render social icons block."""
    platforms = block.get("platforms", [])
    icon_style = block.get("icon_style", "circle")
    alignment = block.get("alignment", "center")
    style = block.get("style", {})
    padding = style.get("padding", "16px 20px")
    if not platforms:
        return ""
    separator = " | "
    parts = [
        '<div style="padding:'
        + str(padding)
        + ";text-align:"
        + str(alignment)
        + ';font-family:Arial,Helvetica,sans-serif;">'
    ]
    links = []
    for p in platforms:
        name = p.get("name", "")
        url = html.escape(p.get("url", "#"))
        icon_url = html.escape(p.get("icon_url", ""))
        if icon_url:
            border_radius = "50%" if icon_style == "circle" else "4px"
            link_html = (
                '<a href="' + url + '" style="display:inline-block;margin:0 6px;">'
                '<img src="' + icon_url + '" alt="' + html.escape(name) + '" '
                'style="width:32px;height:32px;border-radius:' + border_radius + ';" />' + "</a>"
            )
            links.append(link_html)
        else:
            links.append(
                '<a href="'
                + url
                + '" style="display:inline-block;margin:0 8px;font-family:Arial,Helvetica,sans-serif;color:#333;">'
                + html.escape(name)
                + "</a>",
            )
    parts.append(separator.join(links))
    parts.append("</div>")
    return "\n".join(parts)


def _render_video(block: dict[str, Any]) -> str:
    """Render video thumbnail block."""
    thumbnail = html.escape(block.get("thumbnail", ""))
    link = html.escape(block.get("link", "#"))
    alt = html.escape(block.get("alt", "Video"))
    style = block.get("style", {})
    padding = style.get("padding", "0")
    img_html = (
        '<img src="'
        + thumbnail
        + '" alt="'
        + alt
        + '" style="width:100%;max-width:560px;height:auto;display:block;margin:0 auto;" />'
    )
    return (
        '<div style="padding:'
        + str(padding)
        + ';text-align:center;"><a href="'
        + link
        + '">'
        + img_html
        + "</a></div>"
    )


def _render_product(block: dict[str, Any]) -> str:
    """Render product card block."""
    image = html.escape(block.get("image", ""))
    title = html.escape(block.get("title", ""))
    price = block.get("price", "")
    cta = block.get("cta", "Buy Now")
    cta_url = html.escape(block.get("cta_url", "#"))
    description = block.get("description", "")
    style = block.get("style", {})
    padding = style.get("padding", "16px")
    bg_color = style.get("bg_color", "#ffffff")
    border = style.get("border", "1px solid #eeeeee")
    border_radius = style.get("border_radius", 8)
    parts = [
        '<div style="padding:'
        + str(padding)
        + ";background-color:"
        + str(bg_color)
        + ";border:"
        + str(border)
        + ";border-radius:"
        + str(border_radius)
        + 'px;text-align:center;">',
    ]
    if image:
        parts.append(
            '<img src="'
            + image
            + '" alt="'
            + title
            + '" '
            + 'style="width:100%;max-width:280px;height:auto;display:block;margin:0 auto 12px;" />',
        )
    if title:
        parts.append(
            '<h3 style="margin:0 0 8px;font-size:18px;color:#333;font-family:Arial,Helvetica,sans-serif;">'
            + title
            + "</h3>"
        )
    if description:
        parts.append(
            '<p style="margin:0 0 12px;font-size:14px;color:#666;font-family:Arial,Helvetica,sans-serif;">'
            + description
            + "</p>"
        )
    if price:
        parts.append(
            '<p style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1a73e8;">'
            + html.escape(str(price))
            + "</p>",
        )
    parts.append(
        '<a href="'
        + cta_url
        + '" class="btn" style="display:inline-block;padding:12px 24px;'
        + 'background-color:#1a73e8;color:#ffffff;text-decoration:none;border-radius:4px;font-size:14px;font-weight:600;">'
        + html.escape(str(cta))
        + "</a>",
    )
    parts.append("</div>")
    return "\n".join(parts)


def _render_navigation(block: dict[str, Any]) -> str:
    """Render navigation menu block."""
    items = block.get("items", [])
    alignment = block.get("alignment", "center")
    style = block.get("style", {})
    padding = style.get("padding", "12px 20px")
    bg_color = style.get("bg_color", "#ffffff")
    if not items:
        return ""
    parts = [
        '<div style="padding:'
        + str(padding)
        + ";background-color:"
        + str(bg_color)
        + ";text-align:"
        + str(alignment)
        + ';font-family:Arial,Helvetica,sans-serif;">',
    ]
    links = []
    for item in items:
        label = html.escape(item.get("label", ""))
        url = html.escape(item.get("url", "#"))
        links.append(
            '<a href="'
            + url
            + '" style="color:#333;text-decoration:none;font-size:14px;">'
            + label
            + "</a>",
        )
    parts.append(" | ".join(links))
    parts.append("</div>")
    return "\n".join(parts)


def _render_footer(block: dict[str, Any]) -> str:
    """Render footer block with unsubscribe and address."""
    company = html.escape(block.get("company", ""))
    address = html.escape(block.get("address", ""))
    unsubscribe_url = html.escape(block.get("unsubscribe_url", "#"))
    style = block.get("style", {})
    padding = style.get("padding", "20px")
    bg_color = style.get("bg_color", "#f4f4f4")
    color = style.get("color", "#666666")
    font_size = style.get("fontSize", 12)
    parts = [
        '<div style="padding:'
        + str(padding)
        + ";background-color:"
        + str(bg_color)
        + ";text-align:center;font-size:"
        + str(font_size)
        + "px;color:"
        + str(color)
        + ';font-family:Arial,Helvetica,sans-serif;">',
    ]
    if company:
        parts.append('<p style="margin:0 0 4px;">' + company + "</p>")
    if address:
        parts.append('<p style="margin:0 0 12px;">' + address + "</p>")
    parts.append(
        '<p style="margin:0;"><a href="'
        + unsubscribe_url
        + '" '
        + 'style="color:'
        + str(color)
        + ';text-decoration:underline;">Unsubscribe</a></p>',
    )
    parts.append("</div>")
    return "\n".join(parts)


_BLOCK_RENDERERS: dict[str, Any] = {
    "header": _render_header,
    "text": _render_text,
    "image": _render_image,
    "button": _render_button,
    "divider": _render_divider,
    "spacer": _render_spacer,
    "columns": _render_columns,
    "social": _render_social,
    "video": _render_video,
    "product": _render_product,
    "navigation": _render_navigation,
    "footer": _render_footer,
}


def render_block(block: dict[str, Any]) -> str:
    """Render a single block to HTML.

    Args:
        block: Block dict with ``type`` key and type-specific fields.

    Returns:
        HTML string for the block.
    """
    block_type = block.get("type", "text")
    renderer = _BLOCK_RENDERERS.get(block_type, _render_text)
    try:
        return renderer(block)
    except Exception:
        return "<!-- Error rendering " + block_type + " block -->"


def render_template_html(
    blocks: list[dict[str, Any]],
    brand_kit: dict[str, Any] | None = None,
    preheader: str = "",
    title: str = "",
) -> str:
    """Render a full template from blocks to HTML email.

    Wraps blocks in a responsive table-based layout with inline CSS
    for maximum email client compatibility.

    Args:
        blocks: List of block dicts.
        brand_kit: Optional brand configuration.
        preheader: Preheader text.
        title: Email title for <title> tag.

    Returns:
        Complete HTML email document.
    """
    css = generate_responsive_css(brand_kit)
    body_blocks = [render_block(b) for b in blocks]
    body_html = "\n".join(body_blocks)
    preheader_html = ""
    if preheader:
        preheader_html = (
            '<div class="preheader" style="display:none;font-size:1px;'
            + 'color:#ffffff;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">'
            + html.escape(preheader)
            + "</div>"
        )
    escaped_title = html.escape(title)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        + '<meta charset="UTF-8" />\n'
        + '<meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        + "<title>"
        + escaped_title
        + "</title>\n"
        + "<style>"
        + css
        + "</style>\n"
        + "</head>\n"
        + '<body style="margin:0;padding:0;background-color:#f4f4f4;">\n'
        + preheader_html
        + "\n"
        + '<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">\n'
        + '<tr><td align="center" style="padding:20px 0;">\n'
        + '<div class="email-wrapper" style="width:100%;max-width:600px;margin:0 auto;">\n'
        + body_html
        + "\n"
        + "</div>\n</td></tr>\n</table>\n</body>\n</html>"
    )


def generate_plain_text(html_content: str) -> str:
    """Generate plain text fallback from HTML.

    Strips tags, decodes entities, and normalizes whitespace.

    Args:
        html_content: HTML email content.

    Returns:
        Plain text version.
    """
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Compatibility testing
# ---------------------------------------------------------------------------

EMAIL_CLIENTS = [
    "gmail_web",
    "gmail_app",
    "outlook_365",
    "outlook_desktop",
    "apple_mail",
    "yahoo_mail",
    "thunderbird",
    "samsung_mail",
]

_CLIENT_SCORES: dict[str, dict[str, Any]] = {
    "gmail_web": {"style_block": False, "inline_css": True, "flex": False, "max_score": 40},
    "gmail_app": {"style_block": False, "inline_css": True, "flex": False, "max_score": 40},
    "outlook_365": {
        "style_block": True,
        "inline_css": True,
        "flex": False,
        "border_radius": False,
        "max_score": 50,
    },
    "outlook_desktop": {
        "style_block": True,
        "inline_css": True,
        "flex": False,
        "border_radius": False,
        "max_score": 35,
    },
    "apple_mail": {"style_block": True, "inline_css": True, "flex": True, "max_score": 100},
    "yahoo_mail": {"style_block": False, "inline_css": True, "flex": False, "max_score": 45},
    "thunderbird": {"style_block": True, "inline_css": True, "flex": True, "max_score": 90},
    "samsung_mail": {"style_block": False, "inline_css": True, "flex": False, "max_score": 40},
}


def test_compatibility(html_content: str) -> dict[str, Any]:
    """Test email compatibility across major clients.

    Analyzes the HTML for features that may not be supported
    and generates a per-client compatibility report.

    Args:
        html_content: Rendered HTML email.

    Returns:
        Dict with overall score and per-client results.
    """
    results = []
    for client in EMAIL_CLIENTS:
        profile = _CLIENT_SCORES.get(client, {})
        issues = []
        score = profile.get("max_score", 50)
        if "<style" in html_content and not profile.get("style_block", False):
            issues.append(
                {
                    "type": "unsupported_css",
                    "severity": "warning",
                    "detail": "<style> block ignored",
                }
            )
            score -= 10
        if profile.get("inline_css", True) and 'style="' not in html_content:
            issues.append(
                {"type": "missing_inline_css", "severity": "critical", "detail": "No inline styles"}
            )
            score -= 30
        if "display:flex" in html_content and not profile.get("flex", False):
            issues.append(
                {
                    "type": "unsupported_css",
                    "severity": "critical",
                    "detail": "Flexbox not supported",
                }
            )
            score -= 20
        if "border-radius" in html_content and not profile.get("border_radius", True):
            issues.append(
                {
                    "type": "unsupported_css",
                    "severity": "warning",
                    "detail": "border-radius ignored",
                }
            )
            score -= 5
        if "background-image" in html_content:
            issues.append(
                {
                    "type": "unsupported_feature",
                    "severity": "warning",
                    "detail": "Background images unreliable",
                }
            )
            score -= 5
        results.append({"client": client, "score": max(0, score), "issues": issues})
    overall = round(sum(r["score"] for r in results) / len(results), 2) if results else 0
    return {"overall_score": overall, "clients": results}
