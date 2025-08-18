# invoices/serializers.py
from rest_framework import serializers
from decimal import Decimal
from .models import (
    Invoice, InvoiceItem, Payment, RevenueCategory,
    OrgPartnerShare, InvoicePartnerShare, PartnerAllocation, InvoiceAuditLog
)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "description", "quantity", "unit_price", "revenue_category"]
        read_only_fields = ["id"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "method", "reference", "received_at"]
        read_only_fields = ["id", "received_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


class InvoiceAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceAuditLog
        fields = ["id", "action", "details", "created_at"]
        read_only_fields = ["id", "created_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    audit_logs = InvoiceAuditLogSerializer(many=True, read_only=True)
    organization = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "owner", "organization", "client_name", "client_email", "client_country", "client_state",
            "due_date", "status", "currency", "exchange_rate",
            "subtotal_amount", "tax_amount", "total_amount", "paid_amount",
            "created_at", "updated_at", "sent_at", "paid_at",
            "items", "payments", "pdf_file", "audit_logs",
        ]
        read_only_fields = [
            "id", "invoice_number", "status", "subtotal_amount", "tax_amount", "total_amount",
            "paid_amount", "created_at", "updated_at", "sent_at", "paid_at", "pdf_file", "owner", "organization"
        ]

    def create(self, validated_data):
        request = self.context.get("request", None)
        items = validated_data.pop("items", [])
        owner = getattr(request, "user", None)
        org = getattr(owner, "organization", None) if owner else validated_data.get("organization")

        invoice = Invoice.objects.create(owner=owner, organization=org, **validated_data)
        for it in items:
            InvoiceItem.objects.create(invoice=invoice, **it)
        invoice.recalc_totals()
        return invoice

    def update(self, instance, validated_data):
        if instance.status == Invoice.Status.PAID:
            raise serializers.ValidationError("Paid invoice cannot be edited.")

        items = validated_data.pop("items", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if items is not None:
            instance.items.all().delete()
            for it in items:
                InvoiceItem.objects.create(invoice=instance, **it)

        instance.recalc_totals()
        return instance


class RevenueCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueCategory
        fields = "__all__"
        read_only_fields = ["id"]


class OrgPartnerShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgPartnerShare
        fields = "__all__"

    def validate_share_value(self, value):
        if value < 0:
            raise serializers.ValidationError("share_value must be >= 0")
        return value


class InvoicePartnerShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicePartnerShare
        fields = "__all__"


class PartnerAllocationSerializer(serializers.ModelSerializer):
    partner_display = serializers.SerializerMethodField()

    class Meta:
        model = PartnerAllocation
        fields = ["id", "payment", "partner", "partner_display", "amount", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_partner_display(self, obj):
        return getattr(obj.partner.user, "username", str(obj.partner_id))
