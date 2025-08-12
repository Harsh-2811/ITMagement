from django.urls import path
from .views import EmployeeInviteView

urlpatterns = [
    path('invite/', EmployeeInviteView.as_view(), name='employee-invite'),
]
