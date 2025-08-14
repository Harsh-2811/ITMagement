from django.urls import path
from .views import *

urlpatterns = [
    path("invoices/", InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("invoices/<int:pk>/send/", InvoiceSendView.as_view(), name="invoice-send"),
    path("invoices/<int:pk>/paid/", InvoiceMarkPaidView.as_view(), name="invoice-mark-paid"),  
    path("invoices/<int:pk>/overdue/", InvoiceCheckOverdueView.as_view(), name="invoice-check-overdue"),
    path("invoices/<int:pk>/pdf/", InvoicePDFView.as_view(), name="invoice-pdf"),
     path("invoices/<int:pk>/payment/", RecordPaymentView.as_view(), name="record-payment"),
]
