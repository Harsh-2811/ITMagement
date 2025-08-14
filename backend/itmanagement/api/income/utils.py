import tempfile
from django.template.loader import render_to_string
from weasyprint import HTML
import os

def generate_invoice_pdf(invoice):
    """
    Generates PDF for the given invoice instance.
    Returns the path to the temporary PDF file.
    """
    # Render HTML from template
    html_string = render_to_string("invoice_template.html", {"invoice": invoice})

    # Create a temporary file
    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = pdf_file.name
    pdf_file.close()  # Close so WeasyPrint can write

    # Generate PDF
    HTML(string=html_string).write_pdf(pdf_path)

    return pdf_path