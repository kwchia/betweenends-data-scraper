from io import BytesIO

from flask import flash, make_response, redirect, render_template, request, url_for
from xhtml2pdf import pisa


def html_to_pdf(html: str) -> bytes:
    buffer = BytesIO()
    status = pisa.CreatePDF(html, dest=buffer)
    if status.err:
        raise RuntimeError("PDF generation failed")
    return buffer.getvalue()


def pdf_filename(tournament_name: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in tournament_name)
    safe = safe.strip().replace(" ", "_")[:80] or "tournament"
    return f"{safe}_results.pdf"


def pdf_response(tournament, club_name, events, summary, filename: str):
    html = render_template(
        "library/pdf.html",
        tournament=tournament,
        club_name=club_name,
        events=events,
        summary=summary,
    )
    try:
        pdf_bytes = html_to_pdf(html)
    except RuntimeError:
        flash("Could not generate PDF.", "error")
        return redirect(request.referrer or url_for("library.index"))

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
