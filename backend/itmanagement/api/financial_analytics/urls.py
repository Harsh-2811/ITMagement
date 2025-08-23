from django.urls import path
from .views import *

urlpatterns = [
    path("periods/", FinancialPeriodListCreateView.as_view(), name="financial-period-list-create"),
    path("periods/<uuid:pk>/", FinancialPeriodDetailView.as_view(), name="financial-period-detail"),
    
    path("pl-report/", ProfitLossReportGenerateView.as_view(), name="pl-report-generate"),
    path("cashflow-report/", CashFlowReportGenerateView.as_view(), name="cashflow-report-generate"),
    path("partner-breakdown/", PartnerFinancialBreakdownGenerateView.as_view(), name="partner-breakdown-generate"),
    path("tax-report/", TaxReportGenerateView.as_view(), name="tax-report-generate"),
    
    path("forecast-report/", ForecastReportView.as_view(), name="forecast-report-generate"),
    path("cost-centers/create/", CostCenterAnalysisCreateView.as_view(), name="costcenter-create"),

    path("costcenter-analysis/", CostCenterAnalysisView.as_view(), name="costcenter-analysis-generate"),
]
