# Generated initial migration for strategy


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AudiencePersona",
            fields=[
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Persona name (e.g. 'Marketing Mary')",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed persona narrative and background",
                    ),
                ),
                (
                    "demographics",
                    models.JSONField(
                        default=dict,
                        help_text="Demographic data: ageRange, gender, locations, incomeRange, education, occupation, familyStatus, languages",
                    ),
                ),
                (
                    "psychographics",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Psychographic data: values, interests, lifestyle, personality, motivations, frustrations",
                    ),
                ),
                (
                    "pain_points",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Array of pain point strings (max 20)",
                    ),
                ),
                (
                    "content_preferences",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Content preference matrix: formats, topics, tonePreference, contentLength, visualPreference",
                    ),
                ),
                (
                    "channel_preferences",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Channel ranking array with platform, rank, engagementRate, timeSpent",
                    ),
                ),
                (
                    "data_sources",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Sources used to derive this persona: surveys, analytics, interviews, etc.",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        db_index=True,
                        help_text="Whether the persona is currently active",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_audience_persona",
                "verbose_name": "Audience Persona",
                "verbose_name_plural": "Audience Personas",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "is_active"]),
                    models.Index(fields=["tenant_id", "name"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_persona_tenant_name_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PersonaCampaignLink",
            fields=[
                (
                    "persona",
                    models.ForeignKey(
                        AudiencePersona,
                        on_delete=models.CASCADE,
                        related_name="campaign_links",
                        help_text="The linked persona",
                    ),
                ),
                (
                    "campaign_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="UUID of the linked campaign",
                    ),
                ),
                (
                    "weight",
                    models.DecimalField(
                        max_digits=3,
                        decimal_places=2,
                        default=0.5,
                        help_text="Influence weight: 0.0 = reference, 1.0 = primary target",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_persona_campaign_link",
                "verbose_name": "Persona Campaign Link",
                "verbose_name_plural": "Persona Campaign Links",
                "indexes": [
                    models.Index(fields=["campaign_id", "weight"]),
                    models.Index(fields=["persona", "weight"]),
                ],
                "unique_together": [["persona", "campaign_id"]],
            },
        ),
        migrations.CreateModel(
            name="CompetitorProfile",
            fields=[
                ("name", models.CharField(max_length=255, help_text="Competitor company name")),
                ("website", models.URLField(blank=True, help_text="Competitor website URL")),
                (
                    "social_profiles",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Social presence: instagram, linkedin, twitter, tiktok, youtube handles and followers",
                    ),
                ),
                (
                    "scraping_config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Scraping config: frequency, sources, settings",
                    ),
                ),
                (
                    "last_scraped_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timestamp of last successful data scrape",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        db_index=True,
                        help_text="Whether this competitor is actively tracked",
                    ),
                ),
                (
                    "swot_analysis",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Auto-generated SWOT: strengths, weaknesses, opportunities, threats",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_competitor_profile",
                "verbose_name": "Competitor Profile",
                "verbose_name_plural": "Competitor Profiles",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "is_active"]),
                    models.Index(fields=["tenant_id", "name"]),
                    models.Index(fields=["tenant_id", "-last_scraped_at"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"],
                        name="%(app_label)s_competitor_tenant_name_uniq",
                    )
                ],
            },
        ),
    ]
