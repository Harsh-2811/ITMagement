from django.urls import path
from .views import (
    MainPartnerRegistrationView,
    PartnerInviteView,
    PartnerListView,
    PartnerDetailView,
    PartnerUpdateView,
    deactivate_partner
)

urlpatterns = [
    path('register/', MainPartnerRegistrationView.as_view(), name='main-partner-register'),
    path('invite/', PartnerInviteView.as_view(), name='partner-invite'),
    path('list/', PartnerListView.as_view(), name='partner-list'),
    path('<uuid:pk>/', PartnerDetailView.as_view(), name='partner-detail'),
    path('<uuid:pk>/update/', PartnerUpdateView.as_view(), name='partner-update'),
    path('<uuid:pk>/deactivate/', deactivate_partner, name='partner-deactivate'),
]