"""
HTML -> PDF exporter using Playwright (headless Chromium).

Why Playwright: it's the same engine that renders the HTML in your browser,
so the PDF output matches what you'd get from Ctrl+P -> Save as PDF -- but
runs automatically with no manual steps.

Margin is set to 0.4in to match the @page rule in report_renderer's print CSS.
This gives reliable single-page output for the standard report.

Usage:
    from tools.pdf_exporter import html_to_pdf
    html_to_pdf("outputs/report.html", "outputs/report.pdf")

First-time setup:
    pip install playwright
    playwright install chromium
"""
from __future__ import annotations
import os
from typing import Optional


def html_to_pdf(
    html_path: str,
    pdf_path: str,
    paper_format: str = "Letter",
    margin: str = "0.4in",
) -> Optional[str]:
    """
    Render the HTML file at `html_path` to a PDF at `pdf_path`.

    Returns the absolute PDF path on success, or None on failure.
    Failure modes (Playwright not installed, Chromium not installed) are
    handled gracefully so the rest of the pipeline still works.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[PDF EXPORT] Playwright not installed. Skipping PDF generation.")
        print("             To enable: pip install playwright && playwright install chromium")
        return None

    abs_html = os.path.abspath(html_path)
    abs_pdf = os.path.abspath(pdf_path)
    file_url = "file:///" + abs_html.replace(os.sep, "/")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(file_url, wait_until="networkidle")
            page.pdf(
                path=abs_pdf,
                format=paper_format,
                print_background=True,
                margin={
                    "top": margin,
                    "bottom": margin,
                    "left": margin,
                    "right": margin,
                },
                prefer_css_page_size=False,
            )
            browser.close()
        return abs_pdf
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "browserType.launch" in msg:
            print("[PDF EXPORT] Chromium not installed. Skipping PDF generation.")
            print("             To enable: playwright install chromium")
        else:
            print(f"[PDF EXPORT] Failed: {e}")
        return None
