from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ExpenseCategory, Expense, PartnerExpenseAllocation, ExpenseBudget, ExpenseReport
from .serializers import ExpenseCategorySerializer, ExpenseSerializer, PartnerExpenseAllocationSerializer, ExpenseBudgetSerializer, ExpenseReportSerializer
from .utils import compute_partner_allocations, generate_expense_report , notify_managers_new_expense , create_audit_log
from django.contrib.auth import get_user_model
import csv
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal
User = get_user_model()

class ExpenseCategoryListCreateView(generics.ListCreateAPIView):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]

class ExpenseCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]


class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(submitted_by=self.request.user)

    def perform_create(self, serializer):
        expense = serializer.save(submitted_by=self.request.user)
        ratios = self.request.data.get("partner_ratios")
        # Partner allocation
        if ratios:
            allocations = compute_partner_allocations(expense, ratios)
            for alloc in allocations:
                PartnerExpenseAllocation.objects.update_or_create(
                    expense=expense,
                    partner_id=alloc["partner_id"],
                    defaults={"amount": alloc["amount"]}
                )
        # Notify managers
        notify_managers_new_expense(expense)
        # Generate/Update report
        from .utils import generate_expense_report
        generate_expense_report(expense.created_at.date(), expense.created_at.date())


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        expense = serializer.instance
        old_status = expense.status
        status_val = self.request.data.get("status")
        # Only staff can approve/reject
        if status_val in ["Approved", "Rejected"] and self.request.user.is_staff:
            serializer.save(status=status_val, approved_by=self.request.user)
            create_audit_log(expense, old_status, status_val, self.request.user)
            # Auto-update expense report when approved
            if status_val == "Approved":
                from .utils import generate_expense_report
                generate_expense_report(expense.created_at.date(), expense.created_at.date())
        else:
            # Check for edits other than status
            serializer.save()
            # Log changes
            create_audit_log(expense, old_status, expense.status, self.request.user, notes="Edited fields other than status")


class ExpenseBudgetListCreateView(generics.ListCreateAPIView):
    queryset = ExpenseBudget.objects.all()
    serializer_class = ExpenseBudgetSerializer
    permission_classes = [IsAuthenticated]


class ExpenseBudgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExpenseBudget.objects.all()
    serializer_class = ExpenseBudgetSerializer
    permission_classes = [IsAuthenticated]


class ExpenseReportView(generics.ListAPIView):
    serializer_class = ExpenseReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        category_id = self.request.query_params.get("category")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        # current month
        if not start_date or not end_date:
            today = datetime.today().date()
            from calendar import monthrange
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Generate/update reports for the period
        generate_expense_report(start_date, end_date)

        queryset = ExpenseReport.objects.filter(period_start=start_date, period_end=end_date)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        include_partner = request.query_params.get("include_partner", "false").lower() == "true"
        export_csv = request.query_params.get("export_csv", "false").lower() == "true"

        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Partner breakdown
        if include_partner:
            for report in data:
                cat_id = report["category"]
                approved_expenses = Expense.objects.filter(
                    category_id=cat_id, status="Approved",
                    created_at__gte=report["period_start"],
                    created_at__lte=report["period_end"]
                )
                partner_allocations = PartnerExpenseAllocation.objects.filter(expense__in=approved_expenses)
                partners_data = partner_allocations.values("partner__username").annotate(total=Sum("amount"))
                report["partners"] = list(partners_data)

        # CSV Export
        if export_csv:
            response = HttpResponse(content_type='text/csv')
            filename = f"expense_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            writer = csv.writer(response)
            # Header
            headers = ["Category", "Total Budget", "Total Expense", "Percentage Used", "Over Budget", "Period Start", "Period End"]
            if include_partner:
                headers.append("Partner Allocations")
            writer.writerow(headers)

            for row in data:
                row_list = [
                    row["category_name"],
                    row["total_budget"],
                    row["total_expense"],
                    row["percentage_used"],
                    row["over_budget"],
                    row["period_start"],
                    row["period_end"]
                ]
                if include_partner:
                    partners_str = "; ".join([f"{p['partner__username']}:{p['total']}" for p in row.get("partners", [])])
                    row_list.append(partners_str)
                writer.writerow(row_list)

            return response

        return Response(data)
