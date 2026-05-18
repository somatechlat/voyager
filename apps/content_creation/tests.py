"""Content Creation Tests.

Tests for models, services, and API endpoints.
"""

from __future__ import annotations

from apps.content_creation.services.ab_testing import calculate_winner, create_test
from apps.content_creation.services.brand_enforcement import score_compliance
from apps.content_creation.services.generation import (
    _flesch_kincaid,
    _select_model,
    generate_text,
)
from apps.content_creation.services.revision import create_revision, diff_versions
from apps.content_creation.services.templates import render_template


class TestModelSelection:
    """Model routing logic."""

    def test_select_model_long_form(self):
        assert _select_model("blog", "en") == "claude-3.5-sonnet"

    def test_select_model_multilingual(self):
        assert _select_model("social_post", "es") == "gpt-4o"

    def test_select_model_video_script(self):
        assert _select_model("video_script", "en") == "gpt-4o"

    def test_select_model_default(self):
        assert _select_model("social_post", "en") == "claude-3.5-sonnet"


class TestFleschKincaid:
    """Readability scoring."""

    def test_simple_text(self):
        score = _flesch_kincaid("The cat sat on the mat.")
        assert 50 <= score <= 100

    def test_complex_text(self):
        text = (
            "The synergistic optimization of paradigmatic "
            "methodologies necessitates a comprehensive "
            "reconceptualization of heuristic frameworks."
        )
        score = _flesch_kincaid(text)
        assert 0 <= score <= 30


class TestTextGeneration:
    """Text generation service."""

    def test_generate_text_fallback(self):
        result = generate_text(
            brief="Write a compelling social media post about our new product",
            content_type="social_post",
            platforms=["twitter"],
            tone="professional",
        )
        assert "text" in result
        assert result["model_used"] != ""
        assert "scores" in result
        assert "readability" in result["scores"]

    def test_generate_text_with_seo(self):
        result = generate_text(
            brief="Launch our new SaaS product for startups",
            content_type="social_post",
            platforms=["linkedin"],
            seo_keywords=["saas", "startup"],
        )
        assert result["scores"]["seo_score"] >= 0


class TestBrandEnforcement:
    """Brand compliance scoring."""

    def test_no_brand_kit(self):
        result = score_compliance("Hello world", None, None)
        assert result["score"] == 100.0
        assert result["compliant"] is True

    def test_forbidden_word(self):
        brand = {
            "voice": "professional",
            "forbidden_words": ["badword"],
            "competitor_list": [],
            "min_readability": 60.0,
            "min_compliance_score": 75,
        }
        result = score_compliance("This contains badword here", None, brand)
        assert result["score"] < 100
        assert any(v["type"] == "forbidden_word" for v in result["violations"])

    def test_competitor_mention(self):
        brand = {
            "voice": "professional",
            "forbidden_words": [],
            "competitor_list": ["Acme Corp"],
            "min_readability": 60.0,
            "min_compliance_score": 75,
        }
        result = score_compliance("We are better than Acme Corp", None, brand)
        assert result["score"] < 100
        assert any(v["type"] == "competitor_mention" for v in result["violations"])


class TestABTesting:
    """A/B test engine."""

    def test_create_test_insufficient_variants(self):
        result = create_test(name="Test", content_generation_id="abc", variants=[])
        assert result["valid"] is False

    def test_create_test_success(self):
        result = create_test(
            name="Headline Test",
            content_generation_id="abc",
            variants=[
                {"name": "A", "content_text": "Buy now"},
                {"name": "B", "content_text": "Learn more"},
            ],
        )
        assert result["valid"] is True
        assert result["variant_count"] == 2

    def test_calculate_winner(self):
        variants = [
            {
                "variant_id": "A",
                "name": "Control",
                "impressions": 1000,
                "clicks": 100,
                "conversions": 20,
            },
            {
                "variant_id": "B",
                "name": "Variant",
                "impressions": 1000,
                "clicks": 150,
                "conversions": 40,
            },
        ]
        result = calculate_winner(variants)
        assert "significant" in result
        assert "variant_metrics" in result


class TestDiffEngine:
    """Revision diff engine."""

    def test_no_changes(self):
        diff = diff_versions("hello world", "hello world")
        assert diff["summary"]["words_added"] == 0
        assert diff["summary"]["words_deleted"] == 0

    def test_word_added(self):
        diff = diff_versions("hello world", "hello beautiful world")
        assert diff["summary"]["words_added"] == 1

    def test_word_deleted(self):
        diff = diff_versions("hello beautiful world", "hello world")
        assert diff["summary"]["words_deleted"] == 1


class TestRevisionCreation:
    """Revision history."""

    def test_create_revision(self):
        result = create_revision(
            content_generation_id="abc",
            version_number=2,
            old_text="Hello world",
            new_text="Hello beautiful world",
            changed_by="user-1",
        )
        assert result["version_number"] == 2
        assert result["body_text"] == "Hello beautiful world"


class TestTemplateRendering:
    """Jinja2 template rendering."""

    def test_simple_render(self):
        result = render_template(
            template_body="Hello {{ name }}!",
            variables={"name": "World"},
        )
        assert result["rendered"] == "Hello World!"
        assert result["warnings"] == []

    def test_missing_variable(self):
        result = render_template(
            template_body="Hello {{ name }}!",
            variables={},
        )
        assert "name" in str(result["rendered"])
        assert any("undefined" in w.lower() or "missing" in w.lower() for w in result["warnings"])

    def test_conditional_render(self):
        result = render_template(
            template_body="{% if premium %}Welcome back!{% else %}Hello!{% endif %}",
            variables={"premium": True},
        )
        assert "Welcome back" in result["rendered"]
