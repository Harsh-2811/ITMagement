from rest_framework import serializers
from .models import ProfitLossReport, CashFlowReport, PartnerFinancialBreakdown, TaxReport, FinancialPeriod, CostCenter , ForecastReport

class FinancialPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialPeriod
        fields = "__all__"


class ProfitLossReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitLossReport
        fields = "__all__"


class CashFlowReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlowReport
        fields = "__all__"


class PartnerFinancialBreakdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerFinancialBreakdown
        fields = "__all__"


class TaxReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxReport
        fields = "__all__"


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = "__all__"

class ForecastReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastReport
        fields = "__all__"

