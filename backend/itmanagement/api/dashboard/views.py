from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.employees.models import Employee
from api.expense.models import Expense
from api.partners.models import Partner
from api.users.models import User
from django.db.models import Sum, Count


class CommonEmployeesAPI(APIView):
    """
    API to list out common employees across multiple partners/organizations.
    Now includes partner-wise mapping.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employees = Employee.objects.select_related("organization").prefetch_related("organization__partners")

        employee_data = []
        for emp in employees:
            employee_data.append({
                "id": emp.id,
                "name": emp.get_full_name(),  
                "designation": emp.designation,
                "organization": emp.organization.name,
                "partners": [
                    {
                        "id": p.id,
                        "user": p.user.username,
                        "organization": p.organization.name,
                        "role": p.role,
                    }
                    for p in emp.organization.partners.all()
                ]
            })

        return Response({"employees": employee_data})


class ExpenseListAPI(APIView):
    """
    API to list out office + other expenses.
    Includes partner-wise expense allocation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category_summary = Expense.objects.values("category__name").annotate(
            total=Sum("amount"), count=Count("id")
        )

        # Expense details with partner-wise split
        expenses = Expense.objects.prefetch_related("partners").all()
        expense_data = []
        for exp in expenses:
            expense_data.append({
                "id": exp.id,
                "category": exp.category.name if exp.category else None,
                "description": exp.description,
                "amount": exp.amount,
                # "date": exp.date,
                "status": exp.status,
                "partners": [
                    {
                        "id": p.id,
                        "user": p.user.username,
                        "organization": p.organization.name,
                        "share_percentage": getattr(p, "share_percentage", None) 
                    }
                    for p in exp.partners.all()
                ]
            })

        return Response({
            "summary": list(category_summary),
            "expenses": expense_data,
        })
