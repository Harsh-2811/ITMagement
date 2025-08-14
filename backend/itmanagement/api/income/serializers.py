from rest_framework import serializers
from .models import Invoice, InvoiceItem


class PaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = "__all__"

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        invoice = Invoice.objects.create(**validated_data)

        subtotal = 0
        for item_data in items_data:
            item = InvoiceItem.objects.create(invoice=invoice, **item_data)
            subtotal += item.total_price()

        invoice.subtotal_amount = subtotal
        invoice.calculate_tax_for_india()
        return invoice
