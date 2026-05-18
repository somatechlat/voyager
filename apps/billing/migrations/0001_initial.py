"""Initial migration for the Billing & Financial module.

Creates TimeEntry, ProjectBudget, Invoice, LineItem, Expense,
ProfitabilityReport, Retainer, and Payment models with indexes
and constraints.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration for billing app."""

    initial = True

    dependencies: list[tuple[str, str]] = [
        ("clients", "0002_add_remaining"),
    ]

    operations = [
        # -------------------------------------------------------------------
        # TimeEntry
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="TimeEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("user_id", models.CharField(db_index=True, max_length=128)),
                ("task_name", models.CharField(blank=True, max_length=500)),
                ("description", models.TextField(blank=True)),
                ("tracking_mode", models.CharField(choices=[("timer", "Timer"), ("manual", "Manual"), ("automatic", "Automatic"), ("calendar", "Calendar")], db_index=True, default="manual", max_length=20)),
                ("started_at", models.DateTimeField(db_index=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("duration_minutes", models.PositiveIntegerField()),
                ("rounded_minutes", models.PositiveIntegerField()),
                ("rounding_mode", models.CharField(choices=[("nearest", "Nearest"), ("up", "Up"), ("down", "Down")], default="nearest", max_length=20)),
                ("rounding_increment", models.PositiveIntegerField(default=15)),
                ("billing_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("billable_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("is_billable", models.BooleanField(default=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected"), ("invoiced", "Invoiced")], db_index=True, default="draft", max_length=20)),
                ("timesheet_week", models.DateField(blank=True, db_index=True, null=True)),
                ("approver_id", models.CharField(blank=True, default="", max_length=128)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("source_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="time_entries", to="clients.client")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="time_entries", to="clients.project")),
            ],
            options={
                "db_table": "voyager_time_entry",
                "verbose_name": "Time Entry",
                "verbose_name_plural": "Time Entries",
                "ordering": ["-started_at"],
            },
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["tenant_id", "user_id", "-started_at"], name="voy_te_tenant_user_started_idx"),
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["tenant_id", "client", "-started_at"], name="voy_te_tenant_client_started_idx"),
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["tenant_id", "project", "status"], name="voy_te_tenant_project_status_idx"),
        ),
        # -------------------------------------------------------------------
        # ProjectBudget
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ProjectBudget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("budget_type", models.CharField(choices=[("fixed", "Fixed Price"), ("hourly", "Hourly"), ("retainer", "Retainer"), ("hybrid", "Hybrid")], db_index=True, default="fixed", max_length=20)),
                ("total_budget", models.DecimalField(decimal_places=2, max_digits=14)),
                ("hours_allocated", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("hourly_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("monthly_retainer", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("base_retainer", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("overage_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("budget_consumed", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("hours_consumed", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("alert_level", models.CharField(choices=[("none", "None"), ("low", "50%"), ("medium", "75%"), ("high", "90%"), ("critical", "100%")], db_index=True, default="none", max_length=20)),
                ("alert_thresholds", models.JSONField(default=dict)),
                ("last_alert_sent_at", models.DateTimeField(blank=True, null=True)),
                ("forecast_data", models.JSONField(blank=True, default=dict)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="budget_detail", to="clients.project")),
            ],
            options={
                "db_table": "voyager_project_budget",
                "verbose_name": "Project Budget",
                "verbose_name_plural": "Project Budgets",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectbudget",
            index=models.Index(fields=["tenant_id", "budget_type", "alert_level"], name="voy_pb_tenant_type_alert_idx"),
        ),
        # -------------------------------------------------------------------
        # Invoice
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("invoice_number", models.CharField(db_index=True, max_length=50, unique=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent"), ("viewed", "Viewed"), ("partial", "Partially Paid"), ("paid", "Paid"), ("overdue", "Overdue"), ("void", "Void"), ("written_off", "Written Off")], db_index=True, default="draft", max_length=20)),
                ("invoice_type", models.CharField(db_index=True, default="standard", max_length=20)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total", models.DecimalField(decimal_places=2, max_digits=14)),
                ("amount_paid", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("amount_due", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("exchange_rate", models.DecimalField(decimal_places=6, default=1, max_digits=14)),
                ("invoice_date", models.DateField(db_index=True)),
                ("due_date", models.DateField(db_index=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("payment_terms", models.CharField(choices=[("net_15", "Net 15"), ("net_30", "Net 30"), ("net_60", "Net 60"), ("due_on_receipt", "Due on Receipt"), ("custom", "Custom")], default="net_30", max_length=20)),
                ("payment_terms_days", models.PositiveIntegerField(default=30)),
                ("payment_method", models.CharField(blank=True, default="", max_length=50)),
                ("stripe_payment_intent_id", models.CharField(blank=True, db_index=True, default="", max_length=255)),
                ("stripe_invoice_id", models.CharField(blank=True, default="", max_length=255)),
                ("template", models.CharField(default="default", max_length=50)),
                ("notes", models.TextField(blank=True)),
                ("internal_notes", models.TextField(blank=True)),
                ("dunning_log", models.JSONField(default=list)),
                ("date_from", models.DateField(blank=True, null=True)),
                ("date_to", models.DateField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("sent_to", models.JSONField(blank=True, default=list)),
                ("auto_send", models.BooleanField(default=False)),
                ("reminder_schedule", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invoices", to="clients.client")),
            ],
            options={
                "db_table": "voyager_invoice",
                "verbose_name": "Invoice",
                "verbose_name_plural": "Invoices",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["tenant_id", "client", "-created_at"], name="voy_inv_tenant_client_created_idx"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["tenant_id", "status", "due_date"], name="voy_inv_tenant_status_due_idx"),
        ),
        # -------------------------------------------------------------------
        # Expense
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("user_id", models.CharField(db_index=True, max_length=128)),
                ("category", models.CharField(choices=[("travel", "Travel"), ("meals", "Meals"), ("software", "Software"), ("advertising", "Advertising"), ("supplies", "Supplies"), ("professional_services", "Professional Services"), ("other", "Other")], db_index=True, default="other", max_length=50)),
                ("description", models.TextField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("receipt_url", models.URLField(blank=True, default="")),
                ("receipt_ocr_data", models.JSONField(blank=True, default=dict)),
                ("ocr_confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("is_billable", models.BooleanField(default=False)),
                ("markup_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("reimbursed", "Reimbursed"), ("invoiced", "Invoiced"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=20)),
                ("expense_date", models.DateField(db_index=True)),
                ("approver_id", models.CharField(blank=True, default="", max_length=128)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("vendor", models.CharField(blank=True, default="", max_length=255)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("client", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="clients.client")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expenses", to="clients.project")),
            ],
            options={
                "db_table": "voyager_expense",
                "verbose_name": "Expense",
                "verbose_name_plural": "Expenses",
                "ordering": ["-expense_date"],
            },
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["tenant_id", "user_id", "-expense_date"], name="voy_exp_tenant_user_date_idx"),
        ),
        # -------------------------------------------------------------------
        # LineItem (depends on Invoice, Expense, Retainer, TimeEntry)
        # Retainer is defined after this, so we add FK later
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="LineItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("item_type", models.CharField(choices=[("time", "Time"), ("expense", "Expense"), ("retainer", "Retainer"), ("custom", "Custom"), ("discount", "Discount")], db_index=True, default="time", max_length=20)),
                ("description", models.TextField()),
                ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ("unit", models.CharField(default="hours", max_length=20)),
                ("rate", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("tax_applicable", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("expense", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="line_items", to="billing.expense")),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="line_items_set", to="billing.invoice")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="line_items", to="clients.project")),
                ("time_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="line_items", to="billing.timeentry")),
            ],
            options={
                "db_table": "voyager_line_item",
                "verbose_name": "Line Item",
                "verbose_name_plural": "Line Items",
                "ordering": ["invoice", "sort_order", "created_at"],
            },
        ),
        # -------------------------------------------------------------------
        # Retainer
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="Retainer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=255)),
                ("monthly_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("monthly_hours", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("renewal_type", models.CharField(choices=[("auto", "Auto-Renew"), ("manual", "Manual"), ("fixed_term", "Fixed Term")], default="auto", max_length=20)),
                ("renewal_term_months", models.PositiveIntegerField(default=12)),
                ("auto_invoice", models.BooleanField(default=True)),
                ("invoice_day", models.PositiveIntegerField(default=1)),
                ("rollover_policy", models.JSONField(default=dict)),
                ("overage_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("overage_billing_threshold", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("status", models.CharField(choices=[("active", "Active"), ("expired", "Expired"), ("cancelled", "Cancelled"), ("paused", "Paused"), ("pending", "Pending")], db_index=True, default="active", max_length=20)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("consumption_alert_thresholds", models.JSONField(default=list)),
                ("last_invoiced_month", models.DateField(blank=True, null=True)),
                ("total_hours_consumed", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("total_amount_invoiced", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("contract_url", models.URLField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="retainers", to="clients.client")),
            ],
            options={
                "db_table": "voyager_retainer",
                "verbose_name": "Retainer",
                "verbose_name_plural": "Retainers",
                "ordering": ["-created_at"],
            },
        ),
        # Add Retainer FK to LineItem
        migrations.AddField(
            model_name="lineitem",
            name="retainer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="line_items", to="billing.retainer"),
        ),
        migrations.AddIndex(
            model_name="retainer",
            index=models.Index(fields=["tenant_id", "client", "status"], name="voy_ret_tenant_client_status_idx"),
        ),
        # -------------------------------------------------------------------
        # TimeEntry FK to Invoice (add after Invoice exists)
        # -------------------------------------------------------------------
        migrations.AddField(
            model_name="timeentry",
            name="invoice",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="time_entries", to="billing.invoice"),
        ),
        # -------------------------------------------------------------------
        # Expense FK to Invoice
        # -------------------------------------------------------------------
        migrations.AddField(
            model_name="expense",
            name="invoice",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expenses", to="billing.invoice"),
        ),
        # -------------------------------------------------------------------
        # ProfitabilityReport
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ProfitabilityReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("dimension", models.CharField(choices=[("client", "Client"), ("project", "Project"), ("service", "Service"), ("team_member", "Team Member"), ("channel", "Channel"), ("month", "Month"), ("quarter", "Quarter")], db_index=True, max_length=20)),
                ("dimension_id", models.CharField(db_index=True, max_length=128)),
                ("dimension_name", models.CharField(max_length=255)),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("revenue", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("labor_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("tool_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("expense_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("overhead_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("gross_profit", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("gross_margin_pct", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("benchmark_margin_pct", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("margin_vs_benchmark", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("breakdown", models.JSONField(blank=True, default=dict)),
                ("trend_data", models.JSONField(blank=True, default=dict)),
                ("hours_billed", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("hours_logged", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("effective_hourly_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("final", "Final"), ("archived", "Archived")], db_index=True, default="draft", max_length=20)),
                ("is_current", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_profitability_report",
                "verbose_name": "Profitability Report",
                "verbose_name_plural": "Profitability Reports",
                "ordering": ["-period_end", "dimension", "-gross_margin_pct"],
            },
        ),
        migrations.AddConstraint(
            model_name="profitabilityreport",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "dimension", "dimension_id", "period_start", "period_end"],
                name="voyager_pr_unique_period",
            ),
        ),
        # -------------------------------------------------------------------
        # Payment
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("refunded", "Refunded"), ("partially_refunded", "Partially Refunded"), ("disputed", "Disputed"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=20)),
                ("payment_method_type", models.CharField(choices=[("card", "Card"), ("bank_transfer", "Bank Transfer"), ("ach", "ACH"), ("wire", "Wire"), ("check", "Check"), ("cash", "Cash"), ("other", "Other")], default="card", max_length=20)),
                ("stripe_payment_intent_id", models.CharField(blank=True, db_index=True, default="", max_length=255)),
                ("stripe_charge_id", models.CharField(blank=True, default="", max_length=255)),
                ("stripe_customer_id", models.CharField(blank=True, default="", max_length=255)),
                ("stripe_payment_method_id", models.CharField(blank=True, default="", max_length=255)),
                ("stripe_receipt_url", models.URLField(blank=True, default="")),
                ("stripe_refund_id", models.CharField(blank=True, default="", max_length=255)),
                ("refund_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("refund_reason", models.TextField(blank=True)),
                ("failure_message", models.TextField(blank=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="clients.client")),
                ("invoice", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="billing.invoice")),
            ],
            options={
                "db_table": "voyager_payment",
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["tenant_id", "client", "-created_at"], name="voy_pay_tenant_client_created_idx"),
        ),
    ]
