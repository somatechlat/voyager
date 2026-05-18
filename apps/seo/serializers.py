"""SEO API serializers.

Pydantic schemas for request/response validation across all SEO endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Keyword Research
# ---------------------------------------------------------------------------


class KeywordFilters(Schema):
    """Filter criteria for keyword research."""

    volumeMin: int | None = None
    volumeMax: int | None = None
    difficultyMax: float | None = None
    cpcMin: float | None = None
    excludeKeywords: list[str] | None = None
    includeSERPFeatures: list[str] | None = None
    trendDirection: str | None = None


class KeywordResearchRequest(Schema):
    """Request body for keyword research endpoint."""

    seedKeywords: list[str]
    location: str = "US"
    language: str = "en"
    limit: int = 100
    filters: KeywordFilters | None = None


class KeywordResponse(Schema):
    """Keyword data in responses."""

    id: str
    keyword: str
    location: str
    language: str
    monthlyVolume: int | None = None
    difficulty: float | None = None
    cpc: float | None = None
    trendDirection: str = ""
    trendGrowth: float = 0.0
    currentPosition: int | None = None
    previousPosition: int | None = None
    opportunityScore: float = 0.0
    commercialIntent: str = ""
    targetUrl: str = ""
    isTracked: bool = False
    createdAt: datetime | None = None


class KeywordClusterResponse(Schema):
    """Keyword cluster data in responses."""

    label: str
    keywordCount: int
    totalVolume: int
    avgDifficulty: float
    priorityScore: float


class KeywordResearchResponse(Schema):
    """Response for keyword research endpoint."""

    keywords: list[KeywordResponse]
    clusters: list[KeywordClusterResponse]
    totalFound: int
    afterFiltering: int
    location: str
    language: str


# ---------------------------------------------------------------------------
# On-Page Audit
# ---------------------------------------------------------------------------


class OnPageAuditRequest(Schema):
    """Request body for on-page audit endpoint."""

    url: str
    title: str = ""
    metaDescription: str = ""
    h1Tags: list[str] | None = None
    headings: list[dict[str, Any]] | None = None
    bodyText: str = ""
    images: list[dict[str, Any]] | None = None
    internalLinks: int = 0
    externalLinks: int = 0
    canonical: str = ""
    ogTags: list[str] | None = None
    schemas: list[dict[str, Any]] | None = None
    targetKeywords: list[str] | None = None


class OnPageIssue(Schema):
    """Individual audit issue."""

    type: str
    severity: str = "medium"
    details: dict[str, Any] | None = None


class OnPageRecommendation(Schema):
    """Fix recommendation for an issue."""

    issueType: str
    description: str
    priority: str = "medium"
    details: dict[str, Any] | None = None


class OnPageTechnicalDetails(Schema):
    """Technical metrics from audit."""

    wordCount: int
    readability: float
    internalLinks: int
    externalLinks: int
    images: int
    imagesWithAlt: int
    schemas: int


class OnPageAuditResponse(Schema):
    """Response for on-page audit endpoint."""

    id: str
    url: str
    score: float
    grade: str
    issues: list[OnPageIssue]
    recommendations: list[OnPageRecommendation]
    technicalDetails: OnPageTechnicalDetails
    title: str = ""
    metaDescription: str = ""
    h1Count: int = 0
    auditedAt: datetime | None = None


# ---------------------------------------------------------------------------
# Backlink Analysis
# ---------------------------------------------------------------------------


class BacklinkResponse(Schema):
    """Backlink data in responses."""

    id: str
    sourceUrl: str
    targetUrl: str
    anchorText: str
    referringDomain: str
    domainAuthority: float | None = None
    pageAuthority: float | None = None
    spamScore: float | None = None
    isToxic: bool = False
    toxicityScore: float = 0.0
    toxicityReasons: list[str] = []
    recommendedAction: str = "none"
    linkType: str = "dofollow"
    status: str = "active"
    firstSeen: datetime | None = None
    lastSeen: datetime | None = None
    createdAt: datetime | None = None


class AnchorDistribution(Schema):
    """Anchor text distribution entry."""

    anchor: str
    count: int


class BacklinkProfileResponse(Schema):
    """Response for backlink profile analysis."""

    totalBacklinks: int
    referringDomains: int
    dofollowCount: int
    nofollowCount: int
    ugcCount: int
    sponsoredCount: int
    toxicCount: int
    toxicPercentage: float
    avgDomainAuthority: float
    avgPageAuthority: float
    avgToxicityScore: float
    anchorDistribution: dict[str, int]
    domainDistribution: list[dict[str, Any]]
    toxicLinks: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Technical Crawl
# ---------------------------------------------------------------------------


class TechnicalCrawlRequest(Schema):
    """Request body for technical crawl endpoint."""

    url: str
    crawlJobId: str = ""
    statusCode: int | None = 200
    title: str = ""
    metaDescription: str = ""
    h1: str = ""
    h1Count: int = 0
    canonical: str = ""
    hreflangs: list[dict[str, Any]] | None = None
    structuredData: list[dict[str, Any]] | None = None
    lcpMs: int | None = None
    fidMs: int | None = None
    clsScore: float | None = None
    ttfbMs: int | None = None
    pageSizeKb: int | None = None
    loadTimeMs: int | None = None
    robotsMeta: str = ""
    isMobileFriendly: bool | None = None
    isIndexable: bool = True
    wordCount: int = 0
    internalLinks: list[dict[str, Any]] | None = None
    externalLinks: list[dict[str, Any]] | None = None
    brokenLinks: list[dict[str, Any]] | None = None


class TechnicalIssue(Schema):
    """Technical issue detected during crawl."""

    type: str
    severity: str
    details: dict[str, Any] | None = None


class TechnicalCrawlResponse(Schema):
    """Response for technical crawl endpoint."""

    id: str
    url: str
    statusCode: int | None = None
    isIndexable: bool = True
    seoScore: float | None = None
    issues: list[TechnicalIssue]
    coreWebVitals: dict[str, str]
    lcpMs: int | None = None
    fidMs: int | None = None
    clsScore: float | None = None
    ttfbMs: int | None = None
    loadTimeMs: int | None = None
    pageSizeKb: int | None = None
    isMobileFriendly: bool | None = None
    crawledAt: datetime | None = None


class CrawlSummaryResponse(Schema):
    """Summary for a crawl job."""

    pagesCrawled: int
    criticalIssues: int
    warningIssues: int
    avgLoadTimeMs: float
    brokenLinks: int
    avgSeoScore: float


# ---------------------------------------------------------------------------
# Content Optimization
# ---------------------------------------------------------------------------


class ContentOptimizeRequest(Schema):
    """Request body for content optimization endpoint."""

    content: str
    url: str = ""
    targetKeywords: list[str] | None = None
    competitorContent: list[str] | None = None


class ContentRecommendation(Schema):
    """Content optimization recommendation."""

    type: str
    priority: str
    description: str = ""
    details: dict[str, Any] | None = None


class ContentOptimizationResponse(Schema):
    """Response for content optimization endpoint."""

    id: str
    url: str
    wordCount: int
    fleschReadingEase: float | None = None
    fleschKincaidGrade: float | None = None
    smogIndex: float | None = None
    keywordDensity: dict[str, float]
    lsiKeywords: list[dict[str, Any]]
    contentScore: float | None = None
    readabilityScore: float | None = None
    seoScore: float | None = None
    missingTopics: list[dict[str, Any]]
    recommendations: list[ContentRecommendation]
    suggestedTitle: str = ""
    suggestedMetaDescription: str = ""
    analyzedAt: datetime | None = None


# ---------------------------------------------------------------------------
# Rank Tracking
# ---------------------------------------------------------------------------


class RankTrackingCreateRequest(Schema):
    """Request to start tracking a keyword."""

    keywordId: str
    targetUrl: str = ""
    locations: list[str] | None = None
    device: str = "both"
    alertThreshold: str = "medium"


class RankTrackingUpdateRequest(Schema):
    """Request to update a ranking."""

    position: int | None = None
    url: str = ""
    serpFeatures: list[dict[str, Any]] | None = None
    competitors: list[dict[str, Any]] | None = None
    pageTitle: str = ""
    pageDescription: str = ""
    location: str = "US"
    device: str = "desktop"


class RankTrackingResponse(Schema):
    """Response for rank tracking endpoint."""

    id: str
    keywordId: str
    keyword: str
    targetUrl: str = ""
    device: str
    alertThreshold: str
    isActive: bool
    currentPosition: int | None = None
    previousPosition: int | None = None
    positionChange: int = 0
    currentUrl: str = ""
    serpFeatures: list[str] = []
    lastCheckedAt: datetime | None = None
    checkCount: int = 0
    bestPosition: int | None = None
    worstPosition: int | None = None
    createdAt: datetime | None = None


class RankTrendResponse(Schema):
    """Rank trend data point."""

    position: int | None = None
    trackedAt: str | None = None
    url: str = ""
    serpFeatures: list[str] = []


class RankDistributionResponse(Schema):
    """Ranking distribution summary."""

    top3: int
    top10: int
    top50: int
    top100: int
    notRanked: int
    totalTracked: int


# ---------------------------------------------------------------------------
# SEO Reports
# ---------------------------------------------------------------------------


class ReportCreateRequest(Schema):
    """Request to create an SEO report."""

    name: str
    reportType: str = "comprehensive"
    dateFrom: date
    dateTo: date
    sections: list[str] | None = None
    compareWithPrevious: bool = True
    brandName: str = ""
    brandPrimaryColor: str = ""
    brandLogoUrl: str = ""
    customHeader: str = ""
    customFooter: str = ""
    recipients: list[str] | None = None


class ReportScheduleRequest(Schema):
    """Request to schedule a recurring report."""

    frequency: str = "monthly"
    isScheduled: bool = True
    recipients: list[str] | None = None


class ReportResponse(Schema):
    """Response for report endpoints."""

    id: str
    name: str
    reportType: str
    frequency: str
    status: str
    sections: list[str] = []
    dateFrom: date | None = None
    dateTo: date | None = None
    brandName: str = ""
    generatedAt: datetime | None = None
    isScheduled: bool = False
    nextRunAt: datetime | None = None
    createdAt: datetime | None = None


class ReportDetailResponse(Schema):
    """Detailed report with all sections."""

    id: str
    name: str
    reportType: str
    status: str
    sections: list[str] = []
    dateFrom: date | None = None
    dateTo: date | None = None
    executiveSummary: dict[str, Any] | None = None
    keywordRankings: dict[str, Any] | None = None
    backlinkProfile: dict[str, Any] | None = None
    technicalHealth: dict[str, Any] | None = None
    contentScore: dict[str, Any] | None = None
    previousPeriod: dict[str, Any] | None = None
    generatedAt: datetime | None = None
