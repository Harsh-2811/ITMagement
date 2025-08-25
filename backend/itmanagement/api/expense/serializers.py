from rest_framework import serializers
from .models import *

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = "__all__"


class ExpenseBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseBudget
        fields = "__all__"


class PartnerExpenseAllocationSerializer(serializers.ModelSerializer):
    partner_username = serializers.ReadOnlyField(source="partner.username")

    class Meta:
        model = PartnerExpenseAllocation
        fields = ["id", "partner", "partner_username", "amount"]


class ExpenseSerializer(serializers.ModelSerializer):
    allocations = PartnerExpenseAllocationSerializer(many=True, read_only=True)
    submitted_by_username = serializers.ReadOnlyField(source="submitted_by.username")
    approved_by_username = serializers.ReadOnlyField(source="approved_by.username")
    over_budget = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ["status", "submitted_by", "approved_by", "created_at", "updated_at", "allocations"]

    def get_over_budget(self, obj):
        from .utils import validate_expense_budget
        return validate_expense_budget(obj)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Expense amount must be positive.")
        return value


class ExpenseReportSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = ExpenseReport
        fields = "__all__"
