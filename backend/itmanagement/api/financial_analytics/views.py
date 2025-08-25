from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.http import HttpResponse
from decimal import Decimal
from .models import *
from .serializers import *
from .utils import *


class FinancialPeriodListCreateView(generics.ListCreateAPIView):
    queryset = FinancialPeriod.objects.all()
    serializer_class = FinancialPeriodSerializer    
    permission_classes = [permissions.IsAuthenticated]


class FinancialPeriodDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FinancialPeriod.objects.all()
    serializer_class = FinancialPeriodSerializer
    permission_classes = [permissions.IsAuthenticated]



class ProfitLossReportGenerateView(generics.GenericAPIView):
    serializer_class = ProfitLossReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        period = get_period_or_404(request.data.get("period"))
        report = generate_profit_loss(period)
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        """Export P&L as CSV"""
        queryset = ProfitLossReport.objects.all()
        return export_to_csv(queryset, ["period", "total_income", "total_expense", "net_profit"], filename="profit_loss.csv")



class CashFlowReportGenerateView(generics.GenericAPIView):
    serializer_class = CashFlowReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        period = get_period_or_404(request.data.get("period"))
        report = generate_cash_flow(period)
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        queryset = CashFlowReport.objects.all()
        return export_to_csv(queryset, ["period", "total_inflow", "total_outflow", "net_cash"], filename="cash_flow.csv")



class PartnerFinancialBreakdownGenerateView(generics.GenericAPIView):
    serializer_class = PartnerFinancialBreakdownSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        period = get_period_or_404(request.data.get("period"))
        reports = generate_partner_breakdown(period)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        queryset = PartnerFinancialBreakdown.objects.all()
        return export_to_csv(queryset, ["partner", "period", "income", "expense", "net_profit"], filename="partner_breakdown.csv")


class TaxReportGenerateView(generics.GenericAPIView):
    serializer_class = TaxReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        period = get_period_or_404(request.data.get("period"))
        tax_rate = Decimal(str(request.data.get("tax_rate", "10")))
        report = generate_tax_report(period, tax_rate)
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        queryset = TaxReport.objects.all()
        return export_to_csv(queryset, ["period", "total_taxable_income", "total_deductions", "tax_due"], filename="tax_report.csv")


class ForecastReportView(generics.GenericAPIView):
    serializer_class = ForecastReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        period = get_period_or_404(request.data.get("period"))
        report = generate_forecast(period)
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        queryset = ForecastReport.objects.all()
        return export_to_csv(queryset, ["period", "forecasted_net_profit"], filename="forecast_report.csv")

class CostCenterAnalysisCreateView(generics.CreateAPIView):
    """
    Create new CostCenter records (so analysis has data).
    """
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Cost center created successfully",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class CostCenterAnalysisView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # CSV Export if requested
        if request.query_params.get("format") == "csv":
            queryset = CostCenter.objects.all()
            return export_to_csv(queryset, ["name", "description"], filename="cost_center.csv")

        # Otherwise return analysis JSON
        period = get_period_or_404(request.query_params.get("period"))
        data = generate_cost_center_analysis(period)
        return Response(data)
