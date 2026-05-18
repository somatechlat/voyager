"""Web Scraping v2 API views.

Registers all endpoint functions from submodules for the Ninja router.
"""

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..serializers import (
    CompetitorChangeSchema,
    CompetitorDetectResponse,
    CompetitorMonitorListResponse,
    CompetitorMonitorSchema,
    CompetitorSnapshotSchema,
    OCRJobListResponse,
    OCRJobSchema,
    OCRProcessResponse,
    PriceNormalizeResponse,
    PriceTrackListResponse,
    PriceTrackSchema,
    ScrapeJobListResponse,
    ScrapeJobSchema,
    SentimentResultSchema,
    SentimentScoreListResponse,
    SERPTrackResultSchema,
    SERPTrackingListResponse,
    ShareOfVoiceResponse,
    SocialMentionListResponse,
    SocialMentionSchema,
    TrendDetectionListResponse,
    TrendDetectionSchema,
)

from .competitors import (
    create_competitor_monitor,
    detect_changes,
    list_changes,
    list_competitors,
    list_snapshots,
)
from .jobs import create_scrape_job, get_scrape_job, list_scrape_jobs
from .ocr import create_ocr_job, get_ocr_job, list_ocr_jobs, process_image_ocr
from .prices import list_price_tracks, normalize_price, track_price
from .sentiment import analyze_sentiment_text, list_sentiment_scores
from .serp import batch_track_serp, list_serp_trackings, track_serp
from .social import collect_mention, list_social_mentions, share_of_voice
from .trends import create_trend_detection, list_trend_detections

router = Router(auth=VoyagerKeycloakBearer())

# Scrape job endpoints
router.post("/scrape-jobs", response=ScrapeJobSchema)(create_scrape_job)
router.get("/scrape-jobs", response=ScrapeJobListResponse)(list_scrape_jobs)
router.get("/scrape-jobs/{job_id}", response=ScrapeJobSchema)(get_scrape_job)

# Competitor monitor endpoints
router.post("/competitors", response=CompetitorMonitorSchema)(create_competitor_monitor)
router.get("/competitors", response=CompetitorMonitorListResponse)(list_competitors)
router.post("/competitors/{monitor_id}/detect", response=CompetitorDetectResponse)(detect_changes)
router.get("/competitors/{monitor_id}/snapshots", response=list[CompetitorSnapshotSchema])(list_snapshots)
router.get("/competitors/{monitor_id}/changes", response=list[CompetitorChangeSchema])(list_changes)

# Price track endpoints
router.post("/prices/track", response=PriceTrackSchema)(track_price)
router.get("/prices", response=PriceTrackListResponse)(list_price_tracks)
router.post("/prices/normalize", response=PriceNormalizeResponse)(normalize_price)

# Trend detection endpoints
router.post("/trends/detect", response=TrendDetectionSchema)(create_trend_detection)
router.get("/trends", response=TrendDetectionListResponse)(list_trend_detections)

# Social mention endpoints
router.post("/social/mentions", response=SocialMentionSchema)(collect_mention)
router.get("/social/mentions", response=SocialMentionListResponse)(list_social_mentions)
router.post("/social/share-of-voice", response=ShareOfVoiceResponse)(share_of_voice)

# Sentiment analysis endpoints
router.post("/sentiment/analyze", response=SentimentResultSchema)(analyze_sentiment_text)
router.get("/sentiment/scores", response=SentimentScoreListResponse)(list_sentiment_scores)

# SERP tracking endpoints
router.post("/serp/track", response=SERPTrackResultSchema)(track_serp)
router.post("/serp/track/batch", response=list[SERPTrackResultSchema])(batch_track_serp)
router.get("/serp/trackings", response=SERPTrackingListResponse)(list_serp_trackings)

# OCR endpoints
router.post("/ocr/jobs", response=OCRJobSchema)(create_ocr_job)
router.get("/ocr/jobs", response=OCRJobListResponse)(list_ocr_jobs)
router.get("/ocr/jobs/{job_id}", response=OCRJobSchema)(get_ocr_job)
router.post("/ocr/process", response=OCRProcessResponse)(process_image_ocr)
