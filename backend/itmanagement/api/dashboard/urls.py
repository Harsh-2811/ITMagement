from django.urls import path
from .views import CommonEmployeesAPI, ExpenseListAPI

urlpatterns = [
    path("employees/common/", CommonEmployeesAPI.as_view(), name="common-employees"),
    path("expenses/", ExpenseListAPI.as_view(), name="expense-list"),
]
