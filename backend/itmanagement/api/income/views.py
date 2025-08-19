# invoices/views.py
from decimal import Decimal
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, Http404
from django.utils.encoding import smart_str
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
import logging
from datetime import datetime
from .models import Invoice, PartnerAllocation, InvoicePartnerShare, OrgPartnerShare, Payment , RevenueCategory, OrgPartnerShare, InvoicePartnerShare , TaxRule, TaxRecord
from .serializers import (
    InvoiceSerializer, PaymentSerializer, RevenueCategorySerializer,
    OrgPartnerShareSerializer, InvoicePartnerShareSerializer, PartnerAllocationSerializer,TaxRuleSerializer, TaxRecordSerializer
)
# from .tasks import send_invoice_email_with_attachment
from .tasks import allocate_payment_task
from .utils import reporting_aggregate
from .permissions import IsOwnerOrStaff
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
import weasyprint


logger = logging.getLogger(__name__)


class InvoiceListCreateView(generics.ListCreateAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        org = getattr(user, "organization", None)
        qs = Invoice.objects.all().select_related("organization", "owner").prefetch_related("items", "payments")
        if org:
            qs = qs.filter(organization=org)
        else:
            qs = qs.filter(owner=user)
        return qs
    # def perform_create(self, serializer):
    #     serializer.save()
    def perform_create(self, serializer):
        org = getattr(self.request.user, "organization", None)
        serializer.save(owner=self.request.user, organization=org)


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all().prefetch_related("items", "payments")
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]


class InvoiceSendView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    # def post(self, request, pk):
    #     invoice = get_object_or_404(Invoice, pk=pk)
    #     # schedule or call immediate
    #     try:
    #         if getattr(settings, "USE_CELERY", False):
    #             send_invoice_email_with_attachment.delay(invoice.id)
    #         else:
    #             send_invoice_email_with_attachment(invoice.id)
    #         return Response({"detail": "Invoice email queued."}, status=status.HTTP_202_ACCEPTED)
    #     except Exception:
    #         logger.exception("Failed to queue invoice send %s", invoice.id)
    #         return Response({"detail": "Failed to queue invoice send."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class InvoicePDFView(View):
    template_name = "invoice.html"  
    filename = "invoice.pdf"

    def get_invoice_context(self, invoice_id):
        """Build invoice data dynamically from the database"""
        invoice = Invoice.objects.prefetch_related("items", "payments", "partner_shares__partner__allocations").get(id=invoice_id)

        items = [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total_price(),
                "revenue_category": item.revenue_category.name if item.revenue_category else "",
            }
            for item in invoice.items.all()
        ]

        payments = [
            {
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference,
                "date": p.received_at.strftime("%d-%b-%Y"),
            }
            for p in invoice.payments.all()
        ]

        partners = [
            {
                "name": ps.partner.user.username,
                "share_type": ps.share_type,
                "share_value": ps.share_value,
                "allocated_amount": sum(a.amount for a in ps.partner.allocations.filter(payment__invoice=invoice)),
            }
            for ps in invoice.partner_shares.all()
        ]

        context = {
            "invoice_number": invoice.invoice_number,
            "date": invoice.created_at.strftime("%d-%b-%Y"),
            "due_date": invoice.due_date.strftime("%d-%b-%Y") if invoice.due_date else "",
            "status": invoice.status,
            "currency": invoice.currency,
            "client": {
                "name": invoice.client_name,
                "email": invoice.client_email,
                "country": invoice.client_country,
                "state": invoice.client_state,
            },
            "items": items,
            "subtotal": invoice.subtotal_amount,
            "tax": invoice.tax_amount,
            "total": invoice.total_amount,
            "payments": payments,
            "partners": partners,
            "organization": {
                "name": invoice.organization.name
            }
        }

        return context

    def get(self, request, invoice_id, *args, **kwargs):
        """Generate PDF and return as response"""
        context = self.get_invoice_context(invoice_id)
        html = render_to_string(self.template_name, context)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{self.filename}"'
        weasyprint.HTML(string=html).write_pdf(response)

        return response


class InvoiceMarkPaidView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status == Invoice.Status.PAID:
            return Response({"detail": "Invoice already paid."}, status=status.HTTP_200_OK)

        with transaction.atomic():
            remaining = (invoice.total_amount - invoice.paid_amount).quantize(Decimal("0.01"))
            if remaining <= Decimal("0.00"):
                invoice.status = Invoice.Status.PAID
                invoice.paid_at = timezone.now()
                invoice.save(update_fields=["status", "paid_at", "updated_at"])
            else:
                invoice.record_payment(amount=remaining, method="manual_settlement")
        return Response({"detail": "Invoice marked as paid."}, status=status.HTTP_200_OK)

class RecordPaymentView(APIView):
    """
    Accept Payment payload and records it against invoice.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        method = serializer.validated_data.get("method", "")
        reference = serializer.validated_data.get("reference", "")

        with transaction.atomic():
            payment = invoice.record_payment(amount=amount, method=method, reference=reference)

        allocate_async = getattr(settings, "INVOICE_ALLOCATE_ASYNC", False)
        try:
            if allocate_async and getattr(settings, "USE_CELERY", False):
                allocate_payment_task.delay(payment.id)
            elif allocate_async:
                allocate_payment_task(payment.id)
            else:
                from .utils import allocate_payment
                allocate_payment(payment)
        except Exception:
            logger.exception("Allocation failed for payment %s", payment.id)

        return Response({"detail": "Payment recorded.", "invoice": InvoiceSerializer(invoice).data}, status=status.HTTP_200_OK)


class InvoiceCheckOverdueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        today = timezone.now().date()
        overdue_invoices = Invoice.objects.filter(due_date__lt=today).exclude(status=Invoice.Status.PAID)
        updated = []
        for invoice in overdue_invoices:
            if invoice.status != Invoice.Status.OVERDUE:
                invoice.status = Invoice.Status.OVERDUE
                invoice.save(update_fields=["status", "updated_at"])
                updated.append(invoice)
        serializer = InvoiceSerializer(updated, many=True)
        return Response({"message": f"{len(updated)} invoice(s) marked as overdue.", "overdue_invoices": serializer.data})




class RevenueCategoryListCreateView(generics.ListCreateAPIView):
    queryset = RevenueCategory.objects.all()
    serializer_class = RevenueCategorySerializer
    permission_classes = [IsAuthenticated]


class RevenueCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RevenueCategory.objects.all()
    serializer_class = RevenueCategorySerializer
    permission_classes = [IsAuthenticated]


class OrgPartnerShareListCreateView(generics.ListCreateAPIView):
    queryset = OrgPartnerShare.objects.all()
    serializer_class = OrgPartnerShareSerializer
    permission_classes = [IsAuthenticated]


class OrgPartnerShareDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrgPartnerShare.objects.all()
    serializer_class = OrgPartnerShareSerializer
    permission_classes = [IsAuthenticated]


class InvoicePartnerShareListCreateView(generics.ListCreateAPIView):
    queryset = InvoicePartnerShare.objects.all()
    serializer_class = InvoicePartnerShareSerializer
    permission_classes = [IsAuthenticated]


class InvoicePartnerShareDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoicePartnerShare.objects.all()
    serializer_class = InvoicePartnerShareSerializer
    permission_classes = [IsAuthenticated]


class PartnerAllocationListView(generics.ListAPIView):
    queryset = PartnerAllocation.objects.all().select_related("partner", "payment")
    serializer_class = PartnerAllocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        invoice_id = self.request.query_params.get("invoice")
        partner_id = self.request.query_params.get("partner")
        qs = super().get_queryset()
        if invoice_id:
            qs = qs.filter(payment__invoice_id=invoice_id)
        if partner_id:
            qs = qs.filter(partner_id=partner_id)
        return qs.order_by("-created_at")


class TaxRuleListCreateView(generics.ListCreateAPIView):
    queryset = TaxRule.objects.all().order_by("-updated_at")
    serializer_class = TaxRuleSerializer
    permission_classes = [IsAuthenticated]

class TaxRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TaxRule.objects.all()
    serializer_class = TaxRuleSerializer
    permission_classes = [IsAuthenticated]

class ApplyTaxToInvoiceView(generics.UpdateAPIView):
    """
    PATCH /invoices/<uuid:pk>/apply-tax/
    body: {"tax_rule_id": "<uuid optional>"}
    """
    queryset = Invoice.objects.all()
    serializer_class = TaxRecordSerializer  # response only

    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        invoice = self.get_object()
        rule_id = request.data.get("tax_rule_id")
        rule = TaxRule.objects.filter(pk=rule_id).first() if rule_id else None
        tr = compute_and_store_tax(invoice, rule=rule)
        return Response(TaxRecordSerializer(tr).data, status=status.HTTP_200_OK)

class TaxRecordListView(generics.ListAPIView):
    queryset = TaxRecord.objects.select_related("invoice", "tax_rule").all().order_by("-created_at")
    serializer_class = TaxRecordSerializer
    permission_classes = [IsAuthenticated]

class FinancialReportView(APIView):
    """
    GET /income/reports?start=2025-01-01&end=2025-03-31&organization=1
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        org = request.query_params.get("organization")

        start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else None
        end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else None
        org_id = int(org) if org else None

        data = reporting_aggregate(start=start_d, end=end_d, organization_id=org_id)
        return Response(data, status=status.HTTP_200_OK)
