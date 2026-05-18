# Generated initial migration for billing


from django.db import migrations, models


class ItemType(models.TextChoices):
    TIME = "time", "Time"
    EXPENSE = "expense", "Expense"
    RETAINER = "retainer", "Retainer"
    CUSTOM = "custom", "Custom"
    DISCOUNT = "discount", "Discount"


class PaymentMethodType(models.TextChoices):
    CARD = "card", "Card"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    ACH = "ach", "ACH"
    WIRE = "wire", "Wire"
    CHECK = "check", "Check"
    CASH = "cash", "Cash"
    OTHER = "other", "Other"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
    DISPUTED = "disputed", "Disputed"
    CANCELLED = "cancelled", "Cancelled"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("billing", "0003_remaining_models")]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        to="billing.Invoice",
                        on_delete=models.CASCADE,
                        related_name="payments",
                        blank=True,
                        null=True,
                        help_text="Invoice this payment is for",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        to="clients.Client",
                        on_delete=models.CASCADE,
                        related_name="payments",
                        help_text="The client making the payment",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        help_text="Payment amount",
                    ),
                ),
                (
                    "currency",
                    models.CharField(max_length=3, default="USD", help_text="Currency code"),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                        help_text="Payment status",
                    ),
                ),
                (
                    "payment_method_type",
                    models.CharField(
                        max_length=20,
                        choices=PaymentMethodType.choices,
                        default=PaymentMethodType.CARD,
                        help_text="Type of payment method",
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        default="",
                        db_index=True,
                        help_text="Stripe PaymentIntent ID",
                    ),
                ),
                (
                    "stripe_charge_id",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        default="",
                        help_text="Stripe Charge ID",
                    ),
                ),
                (
                    "stripe_customer_id",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        default="",
                        help_text="Stripe Customer ID",
                    ),
                ),
                (
                    "stripe_payment_method_id",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        default="",
                        help_text="Stripe PaymentMethod ID",
                    ),
                ),
                (
                    "stripe_receipt_url",
                    models.URLField(
                        blank=True,
                        default="",
                        help_text="Stripe receipt URL",
                    ),
                ),
                (
                    "stripe_refund_id",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        default="",
                        help_text="Stripe Refund ID (if refunded)",
                    ),
                ),
                (
                    "refund_amount",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Amount refunded",
                    ),
                ),
                ("refund_reason", models.TextField(blank=True, help_text="Reason for refund")),
                (
                    "failure_message",
                    models.TextField(
                        blank=True,
                        help_text="Failure reason if payment failed",
                    ),
                ),
                (
                    "paid_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When payment succeeded",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Extra payment metadata",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_payment",
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "client", "-created_at"],
                        name="voy_pay_tenant_client_created_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "status", "-created_at"],
                        name="voy_pay_tenant_status_created_idx",
                    ),
                    models.Index(fields=["stripe_payment_intent_id"], name="voy_pay_stripe_pi_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LineItem",
            fields=[
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        to="billing.Invoice",
                        on_delete=models.CASCADE,
                        related_name="line_items_set",
                        help_text="The invoice this line item belongs to",
                    ),
                ),
                (
                    "item_type",
                    models.CharField(
                        max_length=20,
                        choices=ItemType.choices,
                        default=ItemType.TIME,
                        db_index=True,
                        help_text="Type of line item",
                    ),
                ),
                ("description", models.TextField(help_text="Description shown on invoice")),
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        default=1,
                        help_text="Quantity",
                    ),
                ),
                (
                    "unit",
                    models.CharField(max_length=20, default="hours", help_text="Unit of measure"),
                ),
                (
                    "rate",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Rate per unit",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        help_text="Total amount (quantity * rate)",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        to="clients.Project",
                        on_delete=models.SET_NULL,
                        related_name="line_items",
                        blank=True,
                        null=True,
                        help_text="Project this line item relates to",
                    ),
                ),
                (
                    "time_entry",
                    models.ForeignKey(
                        to="billing.TimeEntry",
                        on_delete=models.SET_NULL,
                        related_name="line_items",
                        blank=True,
                        null=True,
                        help_text="Linked time entry",
                    ),
                ),
                (
                    "expense",
                    models.ForeignKey(
                        to="billing.Expense",
                        on_delete=models.SET_NULL,
                        related_name="line_items",
                        blank=True,
                        null=True,
                        help_text="Linked expense",
                    ),
                ),
                (
                    "retainer",
                    models.ForeignKey(
                        to="billing.Retainer",
                        on_delete=models.SET_NULL,
                        related_name="line_items",
                        blank=True,
                        null=True,
                        help_text="Linked retainer",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Display order on invoice",
                    ),
                ),
                (
                    "tax_applicable",
                    models.BooleanField(
                        default=True,
                        help_text="Whether tax applies to this line",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Extra data (task name, dates, etc.)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_line_item",
                "verbose_name": "Line Item",
                "verbose_name_plural": "Line Items",
                "ordering": ["invoice", "sort_order", "created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "invoice", "sort_order"],
                        name="voy_li_tenant_invoice_sort_idx",
                    ),
                    models.Index(fields=["tenant_id", "item_type"], name="voy_li_tenant_type_idx"),
                    models.Index(fields=["tenant_id", "project"], name="voy_li_tenant_project_idx"),
                ],
            },
        ),
    ]
