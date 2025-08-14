from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from .models import Invoice
from .serializers import InvoiceSerializer , PaymentSerializer
from .tasks import send_invoice_email_with_attachment
from .utils import generate_invoice_pdf
import os

class InvoiceListCreateView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().prefetch_related("items")
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

class InvoiceMarkPaidView(generics.UpdateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        invoice = self.get_object()
        invoice.mark_paid()
        return Response({
            "detail": f"Invoice #{invoice.id} marked as paid.",
            "status": invoice.status
        })

class InvoiceSendView(generics.UpdateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        invoice = self.get_object()

        # Trigger email sending in background
        send_invoice_email_with_attachment(invoice.id, repeat=0)  # repeat=0 ensures single run

        return Response({
            "detail": "Invoice email scheduled. Status will update after sending."
        })

class InvoiceCheckOverdueView(generics.UpdateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        invoice = self.get_object()
        invoice.check_overdue()
        return Response({"detail": f"Invoice status updated to {invoice.status}"})


class InvoicePDFView(generics.RetrieveAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()

        # Generate PDF
        pdf_path = generate_invoice_pdf(invoice)

        # Read PDF and return as response
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.id}.pdf"'

        # Cleanup temporary file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        return response

class RecordPaymentView(generics.UpdateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        invoice = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        invoice.mark_paid(amount)

        return Response({
            "message": "Payment recorded successfully",
            "invoice": InvoiceSerializer(invoice).data
        }, status=status.HTTP_200_OK)