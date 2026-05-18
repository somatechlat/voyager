"""Initial migration for the Team Collaboration module."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration for Team Collaboration."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128, help_text="Tenant identifier")),
                ("title", models.CharField(max_length=500, help_text="Short task title")),
                ("description", models.TextField(blank=True, help_text="Detailed task description")),
                ("project_id", models.CharField(blank=True, db_index=True, max_length=128, default="")),
                ("client_id", models.CharField(blank=True, db_index=True, max_length=128, default="")),
                ("campaign_id", models.CharField(blank=True, db_index=True, max_length=128, default="")),
                ("assignee_id", models.CharField(blank=True, db_index=True, max_length=128, default="")),
                ("reporter_id", models.CharField(blank=True, db_index=True, max_length=128, default="")),
                ("priority", models.CharField(max_length=5, choices=[("P0","Critical"),("P1","High"),("P2","Medium"),("P3","Low")], default="P2", db_index=True)),
                ("status", models.CharField(max_length=30, choices=[("todo","To Do"),("in_progress","In Progress"),("done","Done"),("cancelled","Cancelled")], default="todo", db_index=True)),
                ("task_type", models.CharField(blank=True, db_index=True, max_length=50, default="")),
                ("tags", models.JSONField(default=list, blank=True)),
                ("due_date", models.DateField(null=True, blank=True, db_index=True)),
                ("estimated_hours", models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)),
                ("actual_hours", models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)),
                ("dependencies", models.JSONField(default=list, blank=True)),
                ("subtasks", models.JSONField(default=list, blank=True)),
                ("custom_fields", models.JSONField(default=dict, blank=True)),
                ("attachments", models.JSONField(default=list, blank=True)),
                ("position", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "voyager_task", "verbose_name": "Task", "verbose_name_plural": "Tasks", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["tenant_id", "status", "priority"], name="voy_task_tsp_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["tenant_id", "assignee_id", "status"], name="voy_task_tas_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["tenant_id", "project_id", "status"], name="voy_task_tps_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["tenant_id", "due_date"], name="voy_task_td_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["tenant_id", "task_type"], name="voy_task_tt_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["assignee_id", "due_date"], name="voy_task_ad_idx")),
        migrations.CreateModel(
            name="TaskComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="team.task")),
                ("author_id", models.CharField(db_index=True, max_length=128)),
                ("content", models.TextField()),
                ("mentions", models.JSONField(default=list, blank=True)),
                ("attachments", models.JSONField(default=list, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "voyager_task_comment", "verbose_name": "Task Comment", "verbose_name_plural": "Task Comments", "ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="taskcomment", index=models.Index(fields=["task", "created_at"], name="voy_tc_task_created_idx")),
        migrations.AddIndex(model_name="taskcomment", index=models.Index(fields=["author_id", "created_at"], name="voy_tc_author_created_idx")),
        migrations.CreateModel(
            name="TaskTimeEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="time_entries", to="team.task")),
                ("user_id", models.CharField(db_index=True, max_length=128)),
                ("started_at", models.DateTimeField(db_index=True)),
                ("ended_at", models.DateTimeField(null=True, blank=True)),
                ("duration_seconds", models.IntegerField(null=True, blank=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"db_table": "voyager_task_time_entry", "verbose_name": "Task Time Entry", "verbose_name_plural": "Task Time Entries", "ordering": ["-started_at"]},
        ),
        migrations.AddIndex(model_name="tasktimeentry", index=models.Index(fields=["task", "user_id"], name="voy_te_task_user_idx")),
        migrations.AddIndex(model_name="tasktimeentry", index=models.Index(fields=["user_id", "started_at"], name="voy_te_user_started_idx")),
        migrations.AddIndex(model_name="tasktimeentry", index=models.Index(fields=["task", "started_at"], name="voy_te_task_started_idx")),
    ]
