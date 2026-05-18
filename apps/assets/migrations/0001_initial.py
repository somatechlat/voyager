"""Initial migration for the assets (DAM) app."""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create AssetFolder, AssetCollection, Asset, AssetVersion, AssetLicense,
    and AssetUsageLog tables with indexes and constraints."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AssetFolder",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=models.UUIDDefault(),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=255)),
                ("path", models.TextField(default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "asset_folders",
                "ordering": ["path", "name"],
            },
        ),
        migrations.CreateModel(
            name="AssetCollection",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=models.UUIDDefault(),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("asset_ids", models.JSONField(blank=True, default=list)),
                ("smart_filter", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "asset_collections",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Asset",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=models.UUIDDefault(),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=500)),
                ("description", models.TextField(blank=True, default="")),
                ("file_key", models.TextField()),
                (
                    "file_type",
                    models.CharField(
                        choices=[
                            ("image", "Image"),
                            ("video", "Video"),
                            ("document", "Document"),
                            ("audio", "Audio"),
                            ("font", "Font"),
                            ("archive", "Archive"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("file_size", models.BigIntegerField(default=0)),
                ("mime_type", models.CharField(blank=True, default="", max_length=100)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("duration", models.FloatField(blank=True, null=True)),
                ("thumbnail_key", models.TextField(blank=True, default="")),
                ("tags", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("dominant_colors", models.JSONField(blank=True, default=list)),
                ("version_number", models.PositiveIntegerField(default=1)),
                ("usage_count", models.PositiveIntegerField(default=0)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("uploaded_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "assets",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AssetVersion",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=models.UUIDDefault(),
                        editable=False,
                        primary_key=True,
                        serialize=False,
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
            },
        ),
        migrations.CreateModel(
            name="AssetLicense",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=models.UUIDDefault(),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "license_type",
                    models.CharField(
                        choices=[
                            ("royalty_free", "Royalty-Free"),
                            ("rights_managed", "Rights-Managed"),
                            ("editorial", "Editorial"),
                            ("creative_commons", "Creative Commons"),
                            ("custom", "Custom"),
                        ],
                        default="royalty_free",
                        max_length=30,
                    ),
                ),
                ("holder", models.CharField(blank=True, default="", max_length=255)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("usage_rights", models.JSONField(blank=True, default=dict)),
                ("restrictions", models.JSONField(blank=True, default=dict)),
                ("attribution_required", models.BooleanField(default=False)),
                ("attribution_text", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "asset_licenses",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AssetUsageLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=models.UUIDDefault(),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("used_by_module", models.CharField(blank=True, default="", max_length=50)),
                ("used_by_record_id", models.CharField(blank=True, default="", max_length=128)),
                ("usage_type", models.CharField(blank=True, default="", max_length=50)),
                ("has_attribution", models.BooleanField(default=False)),
                ("platform", models.CharField(blank=True, default="", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "asset_usage_logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="assetfolder",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="assets.assetfolder",
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="folder",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assets",
                to="assets.assetfolder",
            ),
        ),
        migrations.AddField(
            model_name="assetversion",
            name="asset",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="versions",
                to="assets.asset",
            ),
        ),
        migrations.AddField(
            model_name="assetlicense",
            name="asset",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="licenses",
                to="assets.asset",
            ),
        ),
        migrations.AddField(
            model_name="assetusagelog",
            name="asset",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="usage_logs",
                to="assets.asset",
            ),
        ),
        migrations.AddIndex(
            model_name="assetfolder",
            index=models.Index(fields=["tenant_id", "path"], name="asset_fldr_tenant_path_idx"),
        ),
        migrations.AddIndex(
            model_name="assetfolder",
            index=models.Index(fields=["tenant_id", "name"], name="asset_fldr_tenant_name_idx"),
        ),
        migrations.AddIndex(
            model_name="assetcollection",
            index=models.Index(fields=["tenant_id", "name"], name="asset_coll_tenant_name_idx"),
        ),
        migrations.AddIndex(
            model_name="asset",
            index=models.Index(fields=["tenant_id", "file_type"], name="asset_tenant_type_idx"),
        ),
        migrations.AddIndex(
            model_name="asset",
            index=models.Index(fields=["tenant_id", "created_at"], name="asset_tenant_created_idx"),
        ),
        migrations.AddIndex(
            model_name="asset",
            index=models.Index(
                fields=["tenant_id", "uploaded_by"], name="asset_tenant_uploader_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="asset",
            index=models.Index(fields=["folder", "tenant_id"], name="asset_folder_tenant_idx"),
        ),
        migrations.AddIndex(
            model_name="assetversion",
            index=models.Index(
                fields=["asset", "-version_number"], name="asset_ver_asset_vnum_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="assetlicense",
            index=models.Index(fields=["asset", "valid_until"], name="asset_lic_asset_valid_idx"),
        ),
        migrations.AddIndex(
            model_name="assetusagelog",
            index=models.Index(fields=["asset", "-created_at"], name="asset_use_asset_created_idx"),
        ),
        migrations.AddIndex(
            model_name="assetusagelog",
            index=models.Index(
                fields=["used_by_module", "used_by_record_id"],
                name="asset_use_mod_rec_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="assetversion",
            unique_together={("asset", "version_number")},
        ),
    ]
