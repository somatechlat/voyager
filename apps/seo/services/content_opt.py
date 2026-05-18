"""Content optimization service.

Implements readability scoring, keyword density analysis,
LSI keyword extraction, topic gap detection, and
content optimization recommendations.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any

from django.utils import timezone

from apps.seo.models.content import ContentOptimization

logger = logging.getLogger(__name__)

# Common stop words to exclude from LSI analysis
_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "and", "but", "if", "or", "because", "until", "while", "this", "that",
    "these", "those", "i", "me", "my", "we", "our", "you", "your", "he",
    "him", "his", "she", "her", "it", "its", "they", "them", "their",
}


def count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Input text.

    Returns:
        Word count.
    """
    return len(re.findall(r"\b\w+\b", text))


def count_sentences(text: str) -> int:
    """Count sentences in text.

    Args:
        text: Input text.

    Returns:
        Sentence count (minimum 1).
    """
    return max(len(re.findall(r"[.!?]+", text)), 1)


def count_syllables(word: str) -> int:
    """Estimate syllable count for a word.

    Args:
        word: The word to analyze.

    Returns:
        Estimated syllable count (minimum 1).
    """
    word = word.lower()
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    matches = re.findall(r"[aeiouy]{1,2}", word)
    return max(len(matches), 1)


def flesch_reading_ease(text: str) -> float:
    """Calculate Flesch Reading Ease score.

    Args:
        text: Input text.

    Returns:
        Score from 0-100 (higher = easier to read).
    """
    words = count_words(text)
    if words == 0:
        return 0.0
    sentences = count_sentences(text)
    syllables = sum(count_syllables(w) for w in re.findall(r"\b\w+\b", text))
    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    return max(0.0, min(100.0, score))


def flesch_kincaid_grade(text: str) -> float:
    """Calculate Flesch-Kincaid Grade Level.

    Args:
        text: Input text.

    Returns:
        US school grade level.
    """
    words = count_words(text)
    if words == 0:
        return 0.0
    sentences = count_sentences(text)
    syllables = sum(count_syllables(w) for w in re.findall(r"\b\w+\b", text))
    return max(0.0, 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59)


def smog_index(text: str) -> float:
    """Calculate SMOG readability index.

    Args:
        text: Input text.

    Returns:
        SMOG index score.
    """
    sentences = count_sentences(text)
    if sentences < 3:
        return 0.0
    words = re.findall(r"\b\w+\b", text)
    polysyllables = sum(1 for w in words if count_syllables(w) >= 3)
    return max(0.0, 1.043 * math.sqrt(polysyllables * (30.0 / sentences)) + 3.1291)


def calculate_keyword_density(text: str, keywords: list[str]) -> dict[str, float]:
    """Calculate keyword density for target keywords.

    Args:
        text: Content text.
        keywords: Target keywords.

    Returns:
        Dict mapping keyword to density percentage.
    """
    words = count_words(text)
    if words == 0:
        return {kw: 0.0 for kw in keywords}
    text_lower = text.lower()
    return {
        kw: round(len(re.findall(rf"\b{re.escape(kw.lower())}\b", text_lower)) / words * 100, 2)
        for kw in keywords
    }


def extract_lsi_keywords(text: str, top_n: int = 30) -> list[dict[str, Any]]:
    """Extract LSI (Latent Semantic Indexing) keywords.

    Uses co-occurrence frequency of significant bigrams and trigrams.

    Args:
        text: Content text.
        top_n: Number of LSI keywords to return.

    Returns:
        List of dicts with term and frequency.
    """
    text_lower = text.lower()
    words = re.findall(r"\b[a-z]{3,}\b", text_lower)
    words = [w for w in words if w not in _STOP_WORDS]

    # Bigrams
    bigrams = Counter(f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1))

    # Trigrams
    trigrams = Counter(
        f"{words[i]} {words[i + 1]} {words[i + 2]}"
        for i in range(len(words) - 2)
    )

    # Combine and filter
    combined = bigrams + trigrams
    return [
        {"term": term, "frequency": freq}
        for term, freq in combined.most_common(top_n)
    ]


def extract_entities(text: str) -> list[dict[str, Any]]:
    """Extract named entities using simple pattern matching.

    Args:
        text: Content text.

    Returns:
        List of entity dicts with name and type.
    """
    entities: list[dict[str, Any]] = []

    # Capitalized word sequences (potential proper nouns)
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    for match in re.finditer(pattern, text):
        name = match.group()
        if len(name) > 3 and name.lower() not in _STOP_WORDS:
            entities.append({"name": name, "type": "proper_noun"})

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for e in entities:
        key = e["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:50]


def keyword_position(text: str, keyword: str) -> int:
    """Get the character position of first keyword occurrence.

    Args:
        text: Content text.
        keyword: Keyword to find.

    Returns:
        Character position, or -1 if not found.
    """
    match = re.search(rf"\b{re.escape(keyword.lower())}\b", text.lower())
    return match.start() if match else -1


def find_missing_topics(
    current_topics: list[str],
    competitor_topics: list[str],
    min_frequency: int = 2,
) -> list[dict[str, Any]]:
    """Find topics covered by competitors but not current content.

    Args:
        current_topics: Topics in current content.
        competitor_topics: All topics from competitor content.
        min_frequency: Minimum frequency to consider significant.

    Returns:
        List of missing topic dicts.
    """
    current_set = set(t.lower() for t in current_topics)
    topic_freq = Counter(t.lower() for t in competitor_topics)
    missing: list[dict[str, Any]] = []
    for topic, count in topic_freq.most_common():
        if count >= min_frequency and topic not in current_set:
            missing.append({"topic": topic, "competitor_frequency": count})
    return missing


def optimize_content(
    tenant_id: str,
    content: str,
    url: str = "",
    target_keywords: list[str] | None = None,
    competitor_content: list[str] | None = None,
) -> ContentOptimization:
    """Analyze and optimize content for SEO.

    Args:
        tenant_id: Tenant scope identifier.
        content: The content to analyze.
        url: Optional URL of the content.
        target_keywords: Keywords to optimize for.
        competitor_content: Competitor content texts for benchmarking.

    Returns:
        Created ContentOptimization instance.
    """
    target_keywords = target_keywords or []
    competitor_content = competitor_content or []

    # Basic metrics
    word_count = count_words(content)
    sentence_count = count_sentences(content)
    paragraphs = max(len([p for p in content.split("\n\n") if p.strip()]), 1)

    # Readability
    fre = flesch_reading_ease(content)
    fkg = flesch_kincaid_grade(content)
    smog = smog_index(content)

    # Keyword analysis
    density = calculate_keyword_density(content, target_keywords)
    lsi = extract_lsi_keywords(content)

    # Keyword placement
    placement: dict[str, Any] = {}
    for kw in target_keywords:
        pos = keyword_position(content, kw)
        total_len = len(content)
        placement[kw] = {
            "found": pos >= 0,
            "position": pos,
            "in_first_100": pos >= 0 and pos < min(total_len, 500),
            "relative_position": round(pos / total_len, 4) if total_len > 0 else 0,
        }

    # Entities and topics
    entities = extract_entities(content)
    topics = list({e["name"] for e in entities})

    # Competitor analysis
    comp_word_counts = [count_words(cc) for cc in competitor_content]
    comp_avg_words = round(sum(comp_word_counts) / len(comp_word_counts), 2) if comp_word_counts else None
    comp_readability = (
        round(sum(flesch_reading_ease(cc) for cc in competitor_content) / len(competitor_content), 2)
        if competitor_content else None
    )

    # Competitor topics
    all_comp_topics: list[str] = []
    for cc in competitor_content:
        all_comp_topics.extend(t["name"] for t in extract_entities(cc))
    common_comp_topics = [
        {"topic": t, "frequency": c}
        for t, c in Counter(all_comp_topics).most_common(20)
    ]
    missing_topics = find_missing_topics(topics, all_comp_topics)

    # Heading extraction
    headings: list[dict[str, Any]] = []
    for match in re.finditer(r"<(h[1-6])[^>]*>(.*?)</\1>", content, re.IGNORECASE | re.DOTALL):
        level = int(match.group(1)[1])
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if text:
            headings.append({"level": level, "text": text})

    # Scoring
    readability_score = min(100.0, max(0.0, fre))
    density_score = 100.0 - abs(1.5 - (sum(density.values()) / max(len(density), 1))) * 20
    density_score = max(0.0, min(100.0, density_score))
    length_score = min(100.0, (word_count / 1500.0) * 100.0) if word_count < 1500 else 100.0
    content_score = round((readability_score * 0.25 + density_score * 0.30 + length_score * 0.25 + 20.0), 2)
    content_score = min(100.0, content_score)

    # Generate recommendations
    recommendations: list[dict[str, Any]] = []
    if comp_avg_words and word_count < comp_avg_words * 0.8:
        recommendations.append({
            "type": "increase_length",
            "current": word_count,
            "target": math.ceil(comp_avg_words * 1.1),
            "priority": "high",
        })
    for mt in missing_topics[:10]:
        recommendations.append({
            "type": "add_topic",
            "topic": mt["topic"],
            "frequency": mt["competitor_frequency"],
            "priority": "high" if mt["competitor_frequency"] >= 4 else "medium",
        })
    for kw in target_keywords:
        kp = placement.get(kw, {})
        if not kp.get("found"):
            recommendations.append({
                "type": "add_keyword",
                "keyword": kw,
                "suggestion": f'Include "{kw}" in the first 100 words',
                "priority": "high",
            })
        elif kp.get("relative_position", 0) > 0.5:
            recommendations.append({
                "type": "move_keyword_earlier",
                "keyword": kw,
                "priority": "medium",
            })
    if fre < 60:
        recommendations.append({
            "type": "improve_readability",
            "current": round(fre, 2),
            "target": 60,
            "tips": ["Shorter sentences", "Simpler words", "More subheadings"],
            "priority": "medium",
        })

    # Sort recommendations by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 3))

    # Generate meta suggestions
    suggested_title = ""
    suggested_meta = ""
    if target_keywords:
        main_kw = target_keywords[0]
        suggested_title = f"{main_kw.title()} - Comprehensive Guide | Your Brand"
        suggested_meta = f"Learn everything about {main_kw}. Discover tips, strategies, and best practices to improve your results."

    content_hash = f"{hash(content) & 0xFFFFFFFF:08x}"

    opt = ContentOptimization.objects.create(
        tenant_id=tenant_id,
        url=url,
        content_hash=content_hash,
        target_keywords_json=target_keywords,
        word_count=word_count,
        sentence_count=sentence_count,
        paragraph_count=paragraphs,
        flesch_reading_ease=round(fre, 2),
        flesch_kincaid_grade=round(fkg, 2),
        smog_index=round(smog, 2),
        keyword_density_json=density,
        lsi_keywords_json=lsi,
        keyword_placement_json=placement,
        entities_json=entities,
        topics_covered_json=topics,
        missing_topics_json=missing_topics,
        competitor_avg_word_count=comp_avg_words if comp_avg_words else None,
        competitor_avg_readability=comp_readability,
        competitor_common_topics_json=common_comp_topics,
        heading_structure_json=headings,
        content_score=round(content_score, 2),
        readability_score=round(readability_score, 2),
        seo_score=round(density_score, 2),
        uniqueness_score=round(length_score, 2),
        recommendations_json=recommendations,
        suggested_title=suggested_title,
        suggested_meta_description=suggested_meta,
        analyzed_at=timezone.now(),
    )
    return opt
