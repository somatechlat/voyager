# Generated initial migration for assets

import uuid

from django.db import migrations, models


class LicenseType(models.TextChoices):
    ROYALTY_FREE = "royalty_free", "Royalty-Free"
    RIGHTS_MANAGED = "rights_managed", "Rights-Managed"
    EDITORIAL = "editorial", "Editorial"
    CREATIVE_COMMONS = "creative_commons", "Creative Commons"
    CUSTOM = "custom", "Custom"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("assets", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AssetVersion",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "asset",
                    models.ForeignKey(
                        "assets.Asset", on_delete=models.CASCADE, related_name="versions"
                    ),
                ),
                ("file_key", models.TextField()),
                ("file_size", models.BigIntegerField(default=0)),
                ("version_number", models.PositiveIntegerField()),
                ("change_notes", models.TextField(blank=True, default="")),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "asset_versions",
                "ordering": ["-version_number"],
                "indexes": [models.Index(fields=["asset", "-version_number"])],
                "unique_together": [["asset", "version_number"]],
            },
        ),
        migrations.CreateModel(
            name="AssetLicense",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "asset",
                    models.ForeignKey(
                        "assets.Asset", on_delete=models.CASCADE, related_name="licenses"
                    ),
                ),
                (
                    "license_type",
                    models.CharField(
                        max_length=30,
                        choices=LicenseType.choices,
                        default=LicenseType.ROYALTY_FREE,
                    ),
                ),
                ("holder", models.CharField(max_length=255, blank=True, default="")),
                ("valid_from", models.DateField(null=True, blank=True)),
                ("valid_until", models.DateField(null=True, blank=True)),
                ("usage_rights", models.JSONField(default=dict, blank=True)),
                ("restrictions", models.JSONField(default=dict, blank=True)),
                ("attribution_required", models.BooleanField(default=False)),
                ("attribution_text", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "asset_licenses",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["asset", "valid_until"])],
            },
        ),
        migrations.CreateModel(
            name="AssetUsageLog",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "asset",
                    models.ForeignKey(
                        Asset,
                        on_delete=models.CASCADE,
                        related_name="usage_logs",
                    ),
                ),
                ("used_by_module", models.CharField(max_length=50, blank=True, default="")),
                ("used_by_record_id", models.CharField(max_length=128, blank=True, default="")),
                ("usage_type", models.CharField(max_length=50, blank=True, default="")),
                ("has_attribution", models.BooleanField(default=False)),
                ("platform", models.CharField(max_length=50, blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "asset_usage_logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["asset", "-created_at"]),
                    models.Index(fields=["used_by_module", "used_by_record_id"]),
                ],
            },
        ),
    ]
