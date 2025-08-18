# invoices/urls.py
from django.urls import path
from .views import (
    InvoiceListCreateView, InvoiceDetailView, InvoiceSendView, InvoiceMarkPaidView,
    InvoiceCheckOverdueView, InvoicePDFView, GenerateInvoicePDFView, RecordPaymentView,
    RevenueCategoryListCreateView, RevenueCategoryDetailView,
    OrgPartnerShareListCreateView, OrgPartnerShareDetailView,
    InvoicePartnerShareListCreateView, InvoicePartnerShareDetailView,
    PartnerAllocationListView
)

urlpatterns = [
    path("invoices/", InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<int:pk>/send/", InvoiceSendView.as_view(), name="invoice-send"),
    path("invoices/<int:pk>/paid/", InvoiceMarkPaidView.as_view(), name="invoice-mark-paid"),
    path("invoices/check-overdue/", InvoiceCheckOverdueView.as_view(), name="invoice-check-overdue"),
    path("invoices/<int:pk>/pdf/", InvoicePDFView.as_view(), name="invoice-pdf"),
    path("invoices/<int:pk>/generate-pdf/", GenerateInvoicePDFView.as_view(), name="generate-invoice-pdf"),
    path("invoices/<int:pk>/payment/", RecordPaymentView.as_view(), name="record-payment"),

    path("categories/", RevenueCategoryListCreateView.as_view(), name="revenue-categories"),
    path("categories/<uuid:pk>/", RevenueCategoryDetailView.as_view(), name="revenue-category-detail"),

    path("org-shares/", OrgPartnerShareListCreateView.as_view(), name="org-shares"),
    path("org-shares/<uuid:pk>/", OrgPartnerShareDetailView.as_view(), name="org-share-detail"),

    path("invoice-shares/", InvoicePartnerShareListCreateView.as_view(), name="invoice-shares"),
    path("invoice-shares/<uuid:pk>/", InvoicePartnerShareDetailView.as_view(), name="invoice-share-detail"),

    path("allocations/", PartnerAllocationListView.as_view(), name="partner-allocations"),
]
