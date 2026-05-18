# Generated initial migration for assets

import uuid

from django.db import migrations, models


class FileType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    DOCUMENT = "document", "Document"
    AUDIO = "audio", "Audio"
    FONT = "font", "Font"
    ARCHIVE = "archive", "Archive"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AssetFolder",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("name", models.CharField(max_length=255)),
                (
                    "parent",
                    models.ForeignKey(
                        to="self",
                        on_delete=models.CASCADE,
                        null=True,
                        blank=True,
                        related_name="children",
                    ),
                ),
                ("path", models.TextField(default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "asset_folders",
                "ordering": ["path", "name"],
                "indexes": [
                    models.Index(fields=["tenant_id", "path"]),
                    models.Index(fields=["tenant_id", "name"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AssetCollection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("asset_ids", models.JSONField(default=list, blank=True)),
                ("smart_filter", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "asset_collections",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["tenant_id", "name"])],
            },
        ),
        migrations.CreateModel(
            name="Asset",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("name", models.CharField(max_length=500)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "folder",
                    models.ForeignKey(
                        AssetFolder,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="assets",
                    ),
                ),
                ("file_key", models.TextField()),
                (
                    "file_type",
                    models.CharField(max_length=20, choices=FileType.choices, db_index=True),
                ),
                ("file_size", models.BigIntegerField(default=0)),
                ("mime_type", models.CharField(max_length=100, blank=True, default="")),
                ("width", models.PositiveIntegerField(null=True, blank=True)),
                ("height", models.PositiveIntegerField(null=True, blank=True)),
                ("duration", models.FloatField(null=True, blank=True)),
                ("thumbnail_key", models.TextField(blank=True, default="")),
                ("tags", models.JSONField(default=list, blank=True)),
                ("metadata", models.JSONField(default=dict, blank=True)),
                ("dominant_colors", models.JSONField(default=list, blank=True)),
                ("version_number", models.PositiveIntegerField(default=1)),
                ("usage_count", models.PositiveIntegerField(default=0)),
                ("last_used_at", models.DateTimeField(null=True, blank=True)),
                ("uploaded_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "assets",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "file_type"]),
                    models.Index(fields=["tenant_id", "created_at"]),
                    models.Index(fields=["tenant_id", "uploaded_by"]),
                    models.Index(fields=["folder", "tenant_id"]),
                ],
            },
        ),
    ]
