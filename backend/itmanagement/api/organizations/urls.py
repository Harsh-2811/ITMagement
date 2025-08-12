from django.urls import path
from .views import (
    OrganizationRegisterView, 
    OrganizationApproveView,
    OrganizationListView,
    PendingOrganizationListView,
    reject_organization
)

urlpatterns = [
    path('register/', OrganizationRegisterView.as_view(), name='organization-register'),
    path('list/', OrganizationListView.as_view(), name='organization-list'),
    path('pending/', PendingOrganizationListView.as_view(), name='pending-organizations'),
    path('<uuid:pk>/approve/', OrganizationApproveView.as_view(), name='organization-approve'),
    path('<uuid:pk>/reject/', reject_organization, name='organization-reject'),
]