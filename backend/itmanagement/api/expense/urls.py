from django.urls import path
from .views import *

urlpatterns = [
    path("categories/", ExpenseCategoryListCreateView.as_view(), name="expense-category-list-create"),
    path("categories/<uuid:pk>/", ExpenseCategoryDetailView.as_view(), name="expense-category-detail"),
    path("expenses/", ExpenseListCreateView.as_view(), name="expense-list-create"),
    path("expenses/<uuid:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
    path("budgets/", ExpenseBudgetListCreateView.as_view(), name="expense-budget-list-create"),
    path("budgets/<uuid:pk>/", ExpenseBudgetDetailView.as_view(), name="expense-budget-detail"),
    path("reports/", ExpenseReportView.as_view(), name="expense-report"),
]
