"""
PDF Generation Utility using WeasyPrint
Replaces xhtml2pdf with production-grade PDF generation
"""
import os
import logging
from io import BytesIO
from flask import current_app

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not installed - PDF generation will be unavailable")


def generate_resume_pdf(html_content, filename="resume.pdf"):
    """
    Generate a PDF from HTML content using WeasyPrint
    
    Args:
        html_content (str): HTML string to convert
        filename (str): Output filename
        
    Returns:
        tuple: (pdf_bytes, success, error_message)
    """
    if not WEASYPRINT_AVAILABLE:
        return None, False, "WeasyPrint is not installed. PDF generation unavailable."
    
    try:
        # Create HTML object from string
        html_doc = HTML(string=html_content, base_url=current_app.root_path)
        
        # Generate PDF to BytesIO
        pdf_bytes = BytesIO()
        html_doc.write_pdf(pdf_bytes)
        pdf_bytes.seek(0)
        
        logger.info(f"PDF generated successfully: {filename}")
        return pdf_bytes.getvalue(), True, None
        
    except Exception as e:
        error_msg = f"PDF generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, False, error_msg


def generate_resume_pdf_with_css(html_content, css_content=None, filename="resume.pdf"):
    """
    Generate PDF with custom CSS styling
    
    Args:
        html_content (str): HTML string
        css_content (str): Custom CSS rules
        filename (str): Output filename
        
    Returns:
        tuple: (pdf_bytes, success, error_message)
    """
    if not WEASYPRINT_AVAILABLE:
        return None, False, "WeasyPrint is not installed. PDF generation unavailable."
    
    try:
        # Enhanced HTML with proper structure for PDF
        enhanced_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                @page {{
                    size: A4;
                    margin: 12mm;
                }}
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', 'Outfit', 'Helvetica', 'Arial', sans-serif;
                    color: #1e293b;
                    line-height: 1.5;
                    background: #ffffff;
                }}
                .resume-sheet {{
                    width: 100%;
                    height: auto;
                    background: transparent;
                    page-break-inside: avoid;
                }}
                /* Hide non-print elements */
                .resume-canvas-toolbar,
                .resume-zoom-slider,
                .btn-canvas-ctrl,
                i {{
                    display: none;
                }}
                /* Ensure content is visible */
                a {{
                    color: #0066cc;
                    text-decoration: none;
                }}
                a:visited {{
                    color: #0052a3;
                }}
                {css_content if css_content else ''}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Create HTML from string with base URL
        try:
            html_doc = HTML(string=enhanced_html, base_url=current_app.root_path)
        except:
            # Fallback without base_url
            html_doc = HTML(string=enhanced_html)
        
        # Generate PDF
        pdf_bytes = BytesIO()
        html_doc.write_pdf(pdf_bytes)
        pdf_bytes.seek(0)
        
        logger.info(f"PDF with custom CSS generated successfully: {filename}")
        return pdf_bytes.getvalue(), True, None
        
    except Exception as e:
        error_msg = f"PDF generation with CSS failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, False, error_msg


def sanitize_pdf_content(html_content):
    """
    Sanitize HTML content to ensure proper PDF rendering
    
    Args:
        html_content (str): Raw HTML content
        
    Returns:
        str: Sanitized HTML content
    """
    try:
        # Remove problematic elements for PDF
        sanitized = html_content
        
        # Remove script tags
        import re
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL)
        
        # Remove style attributes that might break PDF
        sanitized = re.sub(r'(float|position|z-index|overflow|scroll)\s*:\s*[^;]+;?', '', sanitized)
        
        return sanitized
    except Exception as e:
        logger.warning(f"Error sanitizing HTML: {e}")
        return html_content


def validate_pdf_generation():
    """
    Validate that PDF generation is available and functional
    
    Returns:
        dict: Status information
    """
    return {
        "available": WEASYPRINT_AVAILABLE,
        "library": "WeasyPrint",
        "version": "62.0+",
        "status": "ready" if WEASYPRINT_AVAILABLE else "unavailable"
    }
