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

from .models import Invoice, PartnerAllocation, InvoicePartnerShare, OrgPartnerShare, Payment
from .serializers import (
    InvoiceSerializer, PaymentSerializer, RevenueCategorySerializer,
    OrgPartnerShareSerializer, InvoicePartnerShareSerializer, PartnerAllocationSerializer
)
from .tasks import send_invoice_email_with_attachment, allocate_payment_task
from .utils import generate_and_attach_pdf

from .permissions import IsOwnerOrStaff

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

    def perform_create(self, serializer):
        org = getattr(self.request.user, "organization", None)
        serializer.save(owner=self.request.user, organization=org)


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all().prefetch_related("items", "payments")
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]


class InvoiceSendView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        # schedule or call immediate
        try:
            if getattr(settings, "USE_CELERY", False):
                send_invoice_email_with_attachment.delay(invoice.id)
            else:
                send_invoice_email_with_attachment(invoice.id)
            return Response({"detail": "Invoice email queued."}, status=status.HTTP_202_ACCEPTED)
        except Exception:
            logger.exception("Failed to queue invoice send %s", invoice.id)
            return Response({"detail": "Failed to queue invoice send."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvoicePDFView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.pdf_file:
            generate_and_attach_pdf(invoice)
        if not invoice.pdf_file:
            raise Http404("PDF not available.")
        try:
            return FileResponse(open(invoice.pdf_file.path, "rb"), content_type="application/pdf",
                                headers={"Content-Disposition": f'attachment; filename="{smart_str(invoice.pdf_file.name.split("/")[-1])}"'})
        except Exception as exc:
            logger.exception("Unable to open PDF for invoice %s: %s", pk, exc)
            raise Http404("Unable to open PDF.")


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


class GenerateInvoicePDFView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        path = generate_and_attach_pdf(invoice)
        if not path:
            return Response({"message": "Failed to generate PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"message": "PDF generated and attached successfully", "pdf_url": invoice.pdf_file.url}, status=status.HTTP_200_OK)


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


# Revenue & Partner endpoints (CRUD)
from rest_framework import generics
from .serializers import RevenueCategorySerializer, OrgPartnerShareSerializer, InvoicePartnerShareSerializer, PartnerAllocationSerializer
from .models import RevenueCategory, OrgPartnerShare, InvoicePartnerShare, PartnerAllocation


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
