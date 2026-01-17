#!/usr/bin/env python3
"""
THALIA - Creative Fleet Designer Agent
Port: 8032

Visual design, layouts, and presentations for LeverEdge.
Part of the Creative Fleet alongside CALLIOPE (Writer), ERATO (Multimedia),
CLIO (Research Writer), and MUSE (Orchestrator).

CAPABILITIES:
- Presentation design (PowerPoint/slides)
- Document formatting (Word/PDF)
- Chart/graph creation
- Brand template application
- Layout optimization
- Thumbnail design

NOT primarily LLM-powered - focuses on programmatic generation.
"""

import os
import sys
import json
import uuid
import httpx
import tempfile
import base64
from pathlib import Path
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal, Union
from io import BytesIO

# Image and document libraries
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RgbColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from docx import Document
from docx.shared import Inches as DocxInches, Pt as DocxPt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
try:
    from cost_tracker import CostTracker
except ImportError:
    # Fallback if shared module not available
    class CostTracker:
        def __init__(self, name): self.name = name
        async def log_usage(self, **kwargs): pass

app = FastAPI(
    title="THALIA",
    description="Creative Fleet Designer - Visual design, layouts, presentations",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
OUTPUT_DIR = os.getenv("THALIA_OUTPUT_DIR", "/tmp/thalia_output")
ASSETS_DIR = os.getenv("THALIA_ASSETS_DIR", "/opt/leveredge/assets")

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# Agent endpoints
AGENT_ENDPOINTS = {
    "MUSE": "http://muse:8030",
    "CALLIOPE": "http://calliope:8031",
    "ERATO": "http://erato:8033",
    "CLIO": "http://clio:8034",
    "HEPHAESTUS": "http://hephaestus:8011",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize cost tracker
cost_tracker = CostTracker("THALIA")

# =============================================================================
# DESIGN SYSTEM
# =============================================================================

COLOR_PALETTES = {
    "leveredge": {
        "primary": "#1B2951",      # Deep navy blue
        "secondary": "#B8860B",    # Dark goldenrod
        "accent": "#36454F",       # Charcoal
        "background": "#FFFFFF",   # White
        "text": "#1A1A1A",         # Near black
        "light": "#F5F7FA",        # Light gray
        "success": "#28A745",      # Green
        "warning": "#FFC107",      # Amber
        "error": "#DC3545",        # Red
    },
    "professional": {
        "primary": "#2C3E50",
        "secondary": "#3498DB",
        "accent": "#E74C3C",
        "background": "#FFFFFF",
        "text": "#2C3E50",
        "light": "#ECF0F1",
        "success": "#27AE60",
        "warning": "#F39C12",
        "error": "#E74C3C",
    },
    "modern": {
        "primary": "#6C63FF",
        "secondary": "#FF6584",
        "accent": "#43D9AD",
        "background": "#FFFFFF",
        "text": "#2D3748",
        "light": "#F7FAFC",
        "success": "#48BB78",
        "warning": "#ECC94B",
        "error": "#F56565",
    },
    "minimal": {
        "primary": "#000000",
        "secondary": "#666666",
        "accent": "#FF4444",
        "background": "#FFFFFF",
        "text": "#333333",
        "light": "#F9F9F9",
        "success": "#00C853",
        "warning": "#FFD600",
        "error": "#FF1744",
    },
    "dark": {
        "primary": "#BB86FC",
        "secondary": "#03DAC6",
        "accent": "#CF6679",
        "background": "#121212",
        "text": "#FFFFFF",
        "light": "#1E1E1E",
        "success": "#00E676",
        "warning": "#FFEA00",
        "error": "#FF5252",
    }
}

TYPOGRAPHY = {
    "headings": "Inter, Arial, sans-serif",
    "body": "Inter, Arial, sans-serif",
    "code": "JetBrains Mono, Consolas, monospace",
    "sizes": {
        "h1": 44,
        "h2": 32,
        "h3": 24,
        "h4": 20,
        "body": 16,
        "small": 14,
        "caption": 12
    }
}

SLIDE_LAYOUTS = {
    "title": "title_slide",
    "content": "content_slide",
    "two_column": "two_column",
    "image_left": "image_left",
    "image_right": "image_right",
    "quote": "quote_slide",
    "section": "section_header",
    "comparison": "comparison_slide",
    "timeline": "timeline_slide",
    "bullet_points": "bullet_points"
}

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch"
    }

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def hex_to_pptx_rgb(hex_color: str) -> RgbColor:
    """Convert hex color to pptx RgbColor"""
    r, g, b = hex_to_rgb(hex_color)
    return RgbColor(r, g, b)

def hex_to_docx_rgb(hex_color: str) -> RGBColor:
    """Convert hex color to docx RGBColor"""
    r, g, b = hex_to_rgb(hex_color)
    return RGBColor(r, g, b)

def get_palette(brand_id: Optional[str] = None) -> dict:
    """Get color palette by brand ID"""
    if brand_id and brand_id in COLOR_PALETTES:
        return COLOR_PALETTES[brand_id]
    return COLOR_PALETTES["leveredge"]

def generate_file_id() -> str:
    """Generate unique file ID"""
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "THALIA",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx["current_datetime"],
                    "days_to_launch": time_ctx["days_to_launch"]
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[THALIA] Event bus notification failed: {e}")

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SlideContent(BaseModel):
    """Content for a single slide"""
    layout: str = "content"  # title, content, two_column, image_left, etc.
    title: Optional[str] = None
    subtitle: Optional[str] = None
    body: Optional[str] = None
    bullets: Optional[List[str]] = None
    image_path: Optional[str] = None
    notes: Optional[str] = None
    left_content: Optional[str] = None
    right_content: Optional[str] = None

class PresentationRequest(BaseModel):
    """Request to create a presentation"""
    content: Dict[str, Any]  # {slides: [...], title?, author?}
    brand_id: Optional[str] = "leveredge"
    template: Optional[str] = None
    style: Optional[str] = "professional"

class DocumentRequest(BaseModel):
    """Request to format a document"""
    content: str
    format: Literal["docx", "pdf"] = "docx"
    brand_id: Optional[str] = "leveredge"
    template: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    headers: Optional[Dict[str, str]] = None  # {header: "text", footer: "text"}

class ChartRequest(BaseModel):
    """Request to generate a chart"""
    type: Literal["bar", "line", "pie", "donut", "scatter", "area", "hbar"]
    data: Dict[str, Any]  # {labels: [...], values: [...], series?: [...]}
    style: Optional[str] = "leveredge"
    animated: Optional[bool] = False
    title: Optional[str] = None
    width: Optional[int] = 800
    height: Optional[int] = 600

class ThumbnailRequest(BaseModel):
    """Request to create a thumbnail"""
    title: str
    style: Optional[str] = "gradient"  # gradient, solid, pattern, image
    brand_id: Optional[str] = "leveredge"
    background_image: Optional[str] = None
    subtitle: Optional[str] = None
    icon: Optional[str] = None

class LayoutRequest(BaseModel):
    """Request for layout optimization"""
    content_type: Literal["email", "document", "slide", "social"]
    content: str
    brand_id: Optional[str] = "leveredge"
    constraints: Optional[Dict[str, Any]] = None

# =============================================================================
# PRESENTATION GENERATION
# =============================================================================

def create_title_slide(prs: Presentation, slide_data: dict, palette: dict):
    """Create a title slide"""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Background
    background = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        prs.slide_width, prs.slide_height
    )
    background.fill.solid()
    background.fill.fore_color.rgb = hex_to_pptx_rgb(palette["primary"])
    background.line.fill.background()

    # Title
    title = slide_data.get("title", "Untitled Presentation")
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(2),
        Inches(9), Inches(1.5)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(44)
    title_para.font.bold = True
    title_para.font.color.rgb = hex_to_pptx_rgb(palette["background"])
    title_para.alignment = PP_ALIGN.CENTER

    # Subtitle
    subtitle = slide_data.get("subtitle", "")
    if subtitle:
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(3.7),
            Inches(9), Inches(0.8)
        )
        subtitle_frame = subtitle_box.text_frame
        subtitle_para = subtitle_frame.paragraphs[0]
        subtitle_para.text = subtitle
        subtitle_para.font.size = Pt(24)
        subtitle_para.font.color.rgb = hex_to_pptx_rgb(palette["secondary"])
        subtitle_para.alignment = PP_ALIGN.CENTER

    return slide

def create_content_slide(prs: Presentation, slide_data: dict, palette: dict):
    """Create a content slide with title and body/bullets"""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Header bar
    header_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        prs.slide_width, Inches(1.2)
    )
    header_bar.fill.solid()
    header_bar.fill.fore_color.rgb = hex_to_pptx_rgb(palette["primary"])
    header_bar.line.fill.background()

    # Title
    title = slide_data.get("title", "")
    if title:
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3),
            Inches(9), Inches(0.7)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(32)
        title_para.font.bold = True
        title_para.font.color.rgb = hex_to_pptx_rgb(palette["background"])

    # Body content or bullets
    content_top = Inches(1.5)
    bullets = slide_data.get("bullets", [])
    body = slide_data.get("body", "")

    if bullets:
        content_box = slide.shapes.add_textbox(
            Inches(0.75), content_top,
            Inches(8.5), Inches(5)
        )
        text_frame = content_box.text_frame
        text_frame.word_wrap = True

        for i, bullet in enumerate(bullets):
            if i == 0:
                para = text_frame.paragraphs[0]
            else:
                para = text_frame.add_paragraph()
            para.text = f"  {bullet}"
            para.font.size = Pt(20)
            para.font.color.rgb = hex_to_pptx_rgb(palette["text"])
            para.space_before = Pt(12)
            para.level = 0

    elif body:
        content_box = slide.shapes.add_textbox(
            Inches(0.75), content_top,
            Inches(8.5), Inches(5)
        )
        text_frame = content_box.text_frame
        text_frame.word_wrap = True
        text_frame.paragraphs[0].text = body
        text_frame.paragraphs[0].font.size = Pt(18)
        text_frame.paragraphs[0].font.color.rgb = hex_to_pptx_rgb(palette["text"])

    return slide

def create_two_column_slide(prs: Presentation, slide_data: dict, palette: dict):
    """Create a two-column slide"""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Header bar
    header_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        prs.slide_width, Inches(1.2)
    )
    header_bar.fill.solid()
    header_bar.fill.fore_color.rgb = hex_to_pptx_rgb(palette["primary"])
    header_bar.line.fill.background()

    # Title
    title = slide_data.get("title", "")
    if title:
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3),
            Inches(9), Inches(0.7)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(32)
        title_para.font.bold = True
        title_para.font.color.rgb = hex_to_pptx_rgb(palette["background"])

    # Left column
    left_content = slide_data.get("left_content", "")
    left_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(1.5),
        Inches(4.25), Inches(5)
    )
    left_frame = left_box.text_frame
    left_frame.word_wrap = True
    left_frame.paragraphs[0].text = left_content
    left_frame.paragraphs[0].font.size = Pt(16)
    left_frame.paragraphs[0].font.color.rgb = hex_to_pptx_rgb(palette["text"])

    # Right column
    right_content = slide_data.get("right_content", "")
    right_box = slide.shapes.add_textbox(
        Inches(5.25), Inches(1.5),
        Inches(4.25), Inches(5)
    )
    right_frame = right_box.text_frame
    right_frame.word_wrap = True
    right_frame.paragraphs[0].text = right_content
    right_frame.paragraphs[0].font.size = Pt(16)
    right_frame.paragraphs[0].font.color.rgb = hex_to_pptx_rgb(palette["text"])

    # Divider line
    divider = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(4.875), Inches(1.5),
        Inches(0.02), Inches(5)
    )
    divider.fill.solid()
    divider.fill.fore_color.rgb = hex_to_pptx_rgb(palette["accent"])
    divider.line.fill.background()

    return slide

def create_section_slide(prs: Presentation, slide_data: dict, palette: dict):
    """Create a section header slide"""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Left accent bar
    accent_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        Inches(0.3), prs.slide_height
    )
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = hex_to_pptx_rgb(palette["secondary"])
    accent_bar.line.fill.background()

    # Title
    title = slide_data.get("title", "Section")
    title_box = slide.shapes.add_textbox(
        Inches(0.75), Inches(2.5),
        Inches(8.5), Inches(1.5)
    )
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(44)
    title_para.font.bold = True
    title_para.font.color.rgb = hex_to_pptx_rgb(palette["primary"])

    # Subtitle
    subtitle = slide_data.get("subtitle", "")
    if subtitle:
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(4.2),
            Inches(8.5), Inches(0.8)
        )
        subtitle_frame = subtitle_box.text_frame
        subtitle_para = subtitle_frame.paragraphs[0]
        subtitle_para.text = subtitle
        subtitle_para.font.size = Pt(20)
        subtitle_para.font.color.rgb = hex_to_pptx_rgb(palette["accent"])

    return slide

def create_quote_slide(prs: Presentation, slide_data: dict, palette: dict):
    """Create a quote slide"""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Background with subtle color
    background = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        prs.slide_width, prs.slide_height
    )
    background.fill.solid()
    background.fill.fore_color.rgb = hex_to_pptx_rgb(palette["light"])
    background.line.fill.background()

    # Quote mark decoration
    quote_mark = slide.shapes.add_textbox(
        Inches(0.5), Inches(1.5),
        Inches(1), Inches(1)
    )
    quote_frame = quote_mark.text_frame
    quote_para = quote_frame.paragraphs[0]
    quote_para.text = '"'
    quote_para.font.size = Pt(120)
    quote_para.font.color.rgb = hex_to_pptx_rgb(palette["secondary"])

    # Quote text
    quote = slide_data.get("body", slide_data.get("title", ""))
    quote_box = slide.shapes.add_textbox(
        Inches(1), Inches(2.5),
        Inches(8), Inches(3)
    )
    quote_text_frame = quote_box.text_frame
    quote_text_frame.word_wrap = True
    quote_text_para = quote_text_frame.paragraphs[0]
    quote_text_para.text = quote
    quote_text_para.font.size = Pt(28)
    quote_text_para.font.italic = True
    quote_text_para.font.color.rgb = hex_to_pptx_rgb(palette["primary"])
    quote_text_para.alignment = PP_ALIGN.CENTER

    # Attribution
    attribution = slide_data.get("subtitle", "")
    if attribution:
        attr_box = slide.shapes.add_textbox(
            Inches(1), Inches(5.5),
            Inches(8), Inches(0.5)
        )
        attr_frame = attr_box.text_frame
        attr_para = attr_frame.paragraphs[0]
        attr_para.text = f"- {attribution}"
        attr_para.font.size = Pt(18)
        attr_para.font.color.rgb = hex_to_pptx_rgb(palette["accent"])
        attr_para.alignment = PP_ALIGN.RIGHT

    return slide

def generate_presentation(content: Dict[str, Any], palette: dict) -> str:
    """Generate a PowerPoint presentation"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    slides_data = content.get("slides", [])

    for slide_data in slides_data:
        layout = slide_data.get("layout", "content")

        if layout == "title":
            create_title_slide(prs, slide_data, palette)
        elif layout == "content" or layout == "bullet_points":
            create_content_slide(prs, slide_data, palette)
        elif layout == "two_column":
            create_two_column_slide(prs, slide_data, palette)
        elif layout == "section":
            create_section_slide(prs, slide_data, palette)
        elif layout == "quote":
            create_quote_slide(prs, slide_data, palette)
        else:
            # Default to content slide
            create_content_slide(prs, slide_data, palette)

    # Save presentation
    file_id = generate_file_id()
    output_path = f"{OUTPUT_DIR}/presentation_{file_id}.pptx"
    prs.save(output_path)

    return output_path

# =============================================================================
# DOCUMENT GENERATION
# =============================================================================

def generate_document(content: str, format: str, palette: dict,
                     title: str = None, author: str = None,
                     headers: dict = None) -> str:
    """Generate a Word document with brand styling"""
    doc = Document()

    # Set document properties
    core_props = doc.core_properties
    if title:
        core_props.title = title
    if author:
        core_props.author = author

    # Add title if provided
    if title:
        title_para = doc.add_heading(title, level=0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in title_para.runs:
            run.font.color.rgb = hex_to_docx_rgb(palette["primary"])

    # Process content - split by headers (## or lines starting with headers)
    lines = content.split('\n')
    current_para = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for markdown-style headers
        if line.startswith('# '):
            heading = doc.add_heading(line[2:], level=1)
            for run in heading.runs:
                run.font.color.rgb = hex_to_docx_rgb(palette["primary"])
        elif line.startswith('## '):
            heading = doc.add_heading(line[3:], level=2)
            for run in heading.runs:
                run.font.color.rgb = hex_to_docx_rgb(palette["primary"])
        elif line.startswith('### '):
            heading = doc.add_heading(line[4:], level=3)
            for run in heading.runs:
                run.font.color.rgb = hex_to_docx_rgb(palette["accent"])
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            para = doc.add_paragraph(line[2:], style='List Bullet')
            for run in para.runs:
                run.font.color.rgb = hex_to_docx_rgb(palette["text"])
        elif line.startswith('1. ') or (len(line) > 2 and line[0].isdigit() and line[1] == '.'):
            # Numbered list
            para = doc.add_paragraph(line.split('. ', 1)[1] if '. ' in line else line,
                                    style='List Number')
            for run in para.runs:
                run.font.color.rgb = hex_to_docx_rgb(palette["text"])
        else:
            # Regular paragraph
            para = doc.add_paragraph(line)
            for run in para.runs:
                run.font.color.rgb = hex_to_docx_rgb(palette["text"])

    # Save document
    file_id = generate_file_id()

    if format == "docx":
        output_path = f"{OUTPUT_DIR}/document_{file_id}.docx"
        doc.save(output_path)
    else:
        # For PDF, we'll save as docx (PDF conversion would require additional libraries)
        # In production, use python-docx2pdf or similar
        output_path = f"{OUTPUT_DIR}/document_{file_id}.docx"
        doc.save(output_path)

    return output_path

# =============================================================================
# CHART GENERATION
# =============================================================================

def generate_chart(chart_type: str, data: Dict[str, Any], style: str,
                   title: str = None, width: int = 800, height: int = 600) -> dict:
    """Generate a chart as PNG and SVG"""
    palette = get_palette(style)

    # Set up matplotlib style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)

    labels = data.get("labels", [])
    values = data.get("values", [])
    series = data.get("series", None)

    # Color cycle from palette
    colors = [
        palette["primary"],
        palette["secondary"],
        palette["accent"],
        palette["success"],
        palette["warning"],
        palette["error"]
    ]

    if chart_type == "bar":
        if series:
            # Multi-series bar chart
            x = np.arange(len(labels))
            width_bar = 0.8 / len(series)
            for i, s in enumerate(series):
                offset = (i - len(series)/2 + 0.5) * width_bar
                ax.bar(x + offset, s["values"], width_bar, label=s.get("name", f"Series {i+1}"),
                      color=colors[i % len(colors)])
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend()
        else:
            ax.bar(labels, values, color=colors[0])

    elif chart_type == "hbar":
        ax.barh(labels, values, color=colors[0])

    elif chart_type == "line":
        if series:
            for i, s in enumerate(series):
                ax.plot(labels, s["values"], marker='o', label=s.get("name", f"Series {i+1}"),
                       color=colors[i % len(colors)], linewidth=2)
            ax.legend()
        else:
            ax.plot(labels, values, marker='o', color=colors[0], linewidth=2)

    elif chart_type == "area":
        if series:
            for i, s in enumerate(series):
                ax.fill_between(range(len(labels)), s["values"], alpha=0.6,
                               label=s.get("name", f"Series {i+1}"), color=colors[i % len(colors)])
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels)
            ax.legend()
        else:
            ax.fill_between(range(len(labels)), values, alpha=0.6, color=colors[0])
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels)

    elif chart_type == "pie":
        ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors[:len(values)],
               startangle=90)
        ax.axis('equal')

    elif chart_type == "donut":
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                          colors=colors[:len(values)], startangle=90,
                                          pctdistance=0.75)
        # Draw center circle for donut effect
        centre_circle = plt.Circle((0, 0), 0.50, fc='white')
        ax.add_patch(centre_circle)
        ax.axis('equal')

    elif chart_type == "scatter":
        x_values = data.get("x", values)
        y_values = data.get("y", values)
        ax.scatter(x_values, y_values, c=colors[0], s=100, alpha=0.7)

    # Title
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', color=palette["text"])

    # Style adjustments
    ax.tick_params(colors=palette["text"])
    for spine in ax.spines.values():
        spine.set_color(palette["accent"])

    plt.tight_layout()

    # Save as PNG and SVG
    file_id = generate_file_id()
    png_path = f"{OUTPUT_DIR}/chart_{file_id}.png"
    svg_path = f"{OUTPUT_DIR}/chart_{file_id}.svg"

    fig.savefig(png_path, dpi=150, bbox_inches='tight', facecolor='white')
    fig.savefig(svg_path, format='svg', bbox_inches='tight', facecolor='white')

    plt.close(fig)

    return {
        "image_path": png_path,
        "svg_path": svg_path,
        "animation_path": None  # Animation would require additional libraries
    }

# =============================================================================
# THUMBNAIL GENERATION
# =============================================================================

def create_gradient_background(size: tuple, color1: str, color2: str, direction: str = "diagonal") -> Image.Image:
    """Create a gradient background"""
    width, height = size
    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)

    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    if direction == "diagonal":
        for y in range(height):
            for x in range(width):
                # Diagonal gradient
                ratio = (x + y) / (width + height)
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                draw.point((x, y), fill=(r, g, b))
    elif direction == "horizontal":
        for x in range(width):
            ratio = x / width
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    else:  # vertical
        for y in range(height):
            ratio = y / height
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    return img

def generate_thumbnail(title: str, style: str, palette: dict,
                       background_image: str = None,
                       subtitle: str = None) -> dict:
    """Generate thumbnails in multiple sizes"""
    sizes = {
        "small": (320, 180),
        "medium": (640, 360),
        "large": (1280, 720)
    }

    file_id = generate_file_id()
    output_paths = {}

    for size_name, dimensions in sizes.items():
        width, height = dimensions

        # Create background
        if style == "gradient":
            img = create_gradient_background(dimensions, palette["primary"], palette["accent"])
        elif style == "solid":
            img = Image.new('RGB', dimensions, hex_to_rgb(palette["primary"]))
        elif style == "pattern":
            # Simple pattern with alternating colors
            img = Image.new('RGB', dimensions, hex_to_rgb(palette["background"]))
            draw = ImageDraw.Draw(img)
            pattern_color = hex_to_rgb(palette["light"])
            for i in range(0, width, 20):
                for j in range(0, height, 20):
                    if (i + j) % 40 == 0:
                        draw.rectangle([i, j, i+10, j+10], fill=pattern_color)
        elif background_image and style == "image":
            try:
                img = Image.open(background_image)
                img = img.resize(dimensions, Image.Resampling.LANCZOS)
                # Add overlay for text readability
                overlay = Image.new('RGBA', dimensions, (*hex_to_rgb(palette["primary"]), 180))
                img = img.convert('RGBA')
                img = Image.alpha_composite(img, overlay)
                img = img.convert('RGB')
            except Exception:
                img = create_gradient_background(dimensions, palette["primary"], palette["accent"])
        else:
            img = create_gradient_background(dimensions, palette["primary"], palette["accent"])

        draw = ImageDraw.Draw(img)

        # Try to load a good font, fall back to default
        try:
            # Calculate font size based on image dimensions
            title_font_size = int(height * 0.12)
            subtitle_font_size = int(height * 0.06)
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_font_size)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", subtitle_font_size)
        except Exception:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # Draw title (centered)
        text_color = hex_to_rgb(palette["background"])

        # Word wrap title if too long
        max_chars = int(width / (title_font_size * 0.6))
        if len(title) > max_chars:
            words = title.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            title_text = "\n".join(lines)
        else:
            title_text = title

        # Calculate text position
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        title_y = (height - text_height) // 2 - (int(height * 0.05) if subtitle else 0)
        title_x = (width - text_width) // 2

        draw.text((title_x, title_y), title_text, font=title_font, fill=text_color, align="center")

        # Draw subtitle if provided
        if subtitle:
            bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            sub_width = bbox[2] - bbox[0]
            sub_x = (width - sub_width) // 2
            sub_y = title_y + text_height + int(height * 0.03)
            sub_color = hex_to_rgb(palette["secondary"])
            draw.text((sub_x, sub_y), subtitle, font=subtitle_font, fill=sub_color)

        # Save
        output_path = f"{OUTPUT_DIR}/thumbnail_{file_id}_{size_name}.png"
        img.save(output_path, "PNG")
        output_paths[size_name] = output_path

    return output_paths

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "THALIA",
        "role": "Creative Fleet Designer",
        "version": "1.0.0",
        "port": 8032,
        "fleet": "Creative Fleet",
        "capabilities": [
            "presentation_design",
            "document_formatting",
            "chart_creation",
            "thumbnail_design",
            "brand_template_application",
            "layout_optimization"
        ],
        "current_time": time_ctx["current_datetime"],
        "days_to_launch": time_ctx["days_to_launch"]
    }

@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()

@app.get("/design-system")
async def get_design_system():
    """Return the design system configuration"""
    return {
        "color_palettes": COLOR_PALETTES,
        "typography": TYPOGRAPHY,
        "slide_layouts": SLIDE_LAYOUTS,
        "default_brand": "leveredge"
    }

@app.get("/palettes")
async def get_palettes():
    """List available color palettes"""
    return {
        "palettes": list(COLOR_PALETTES.keys()),
        "default": "leveredge"
    }

@app.get("/palette/{brand_id}")
async def get_palette_details(brand_id: str):
    """Get details of a specific palette"""
    if brand_id not in COLOR_PALETTES:
        raise HTTPException(status_code=404, detail=f"Palette '{brand_id}' not found")
    return {
        "brand_id": brand_id,
        "colors": COLOR_PALETTES[brand_id]
    }

@app.post("/design/presentation")
async def create_presentation(req: PresentationRequest):
    """Create a presentation from content"""
    time_ctx = get_time_context()

    try:
        palette = get_palette(req.brand_id)
        slides = req.content.get("slides", [])

        if not slides:
            raise HTTPException(status_code=400, detail="No slides provided in content")

        # Generate presentation
        file_path = generate_presentation(req.content, palette)

        # Generate preview URL (in production, this would be an actual accessible URL)
        preview_url = f"/files/{Path(file_path).name}"

        await notify_event_bus("presentation_created", {
            "slide_count": len(slides),
            "brand_id": req.brand_id,
            "file_path": file_path
        })

        return {
            "file_path": file_path,
            "preview_url": preview_url,
            "slide_count": len(slides),
            "brand_id": req.brand_id,
            "style": req.style,
            "agent": "THALIA",
            "timestamp": time_ctx["current_datetime"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presentation creation failed: {str(e)}")

@app.post("/design/document")
async def format_document(req: DocumentRequest):
    """Format a document with brand styling"""
    time_ctx = get_time_context()

    try:
        palette = get_palette(req.brand_id)

        # Generate document
        file_path = generate_document(
            content=req.content,
            format=req.format,
            palette=palette,
            title=req.title,
            author=req.author,
            headers=req.headers
        )

        # Generate preview URL
        preview_url = f"/files/{Path(file_path).name}"

        await notify_event_bus("document_created", {
            "format": req.format,
            "brand_id": req.brand_id,
            "file_path": file_path
        })

        return {
            "file_path": file_path,
            "preview_url": preview_url,
            "format": req.format,
            "brand_id": req.brand_id,
            "agent": "THALIA",
            "timestamp": time_ctx["current_datetime"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document creation failed: {str(e)}")

@app.post("/design/chart")
async def generate_chart_endpoint(req: ChartRequest):
    """Generate a chart/graph"""
    time_ctx = get_time_context()

    try:
        result = generate_chart(
            chart_type=req.type,
            data=req.data,
            style=req.style,
            title=req.title,
            width=req.width,
            height=req.height
        )

        await notify_event_bus("chart_created", {
            "chart_type": req.type,
            "style": req.style
        })

        return {
            "image_path": result["image_path"],
            "svg_path": result["svg_path"],
            "animation_path": result.get("animation_path"),
            "chart_type": req.type,
            "style": req.style,
            "agent": "THALIA",
            "timestamp": time_ctx["current_datetime"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart creation failed: {str(e)}")

@app.post("/design/thumbnail")
async def create_thumbnail(req: ThumbnailRequest):
    """Create a thumbnail image"""
    time_ctx = get_time_context()

    try:
        palette = get_palette(req.brand_id)

        sizes = generate_thumbnail(
            title=req.title,
            style=req.style,
            palette=palette,
            background_image=req.background_image,
            subtitle=req.subtitle
        )

        # Main image path (large size)
        image_path = sizes["large"]

        await notify_event_bus("thumbnail_created", {
            "title": req.title[:50],
            "style": req.style,
            "brand_id": req.brand_id
        })

        return {
            "image_path": image_path,
            "sizes": sizes,
            "style": req.style,
            "brand_id": req.brand_id,
            "agent": "THALIA",
            "timestamp": time_ctx["current_datetime"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail creation failed: {str(e)}")

@app.post("/design/layout")
async def optimize_layout(req: LayoutRequest):
    """Optimize content layout (returns layout suggestions)"""
    time_ctx = get_time_context()

    palette = get_palette(req.brand_id)

    # Simple layout recommendations based on content type
    layouts = {
        "email": {
            "max_width": "600px",
            "padding": "20px",
            "font_size": "16px",
            "line_height": "1.6",
            "sections": ["header", "hero", "body", "cta", "footer"],
            "recommendations": [
                "Keep subject line under 50 characters",
                "Use single-column layout for mobile compatibility",
                "Place CTA above the fold",
                "Limit images to reduce load time"
            ]
        },
        "document": {
            "margins": "1 inch",
            "font_size": "12pt",
            "line_height": "1.5",
            "heading_hierarchy": ["h1: 24pt", "h2: 18pt", "h3: 14pt"],
            "recommendations": [
                "Use consistent heading styles",
                "Add page numbers for documents over 3 pages",
                "Include table of contents for long documents",
                "Use bullet points for lists of 3+ items"
            ]
        },
        "slide": {
            "aspect_ratio": "16:9",
            "max_bullets": 5,
            "font_min": "24pt",
            "recommendations": [
                "One idea per slide",
                "Maximum 6 words per bullet",
                "Use high-contrast colors",
                "Images should fill at least 40% of slide"
            ]
        },
        "social": {
            "optimal_sizes": {
                "instagram_square": "1080x1080",
                "instagram_story": "1080x1920",
                "linkedin": "1200x627",
                "twitter": "1200x675"
            },
            "recommendations": [
                "Use bold, readable text",
                "Keep text to 20% of image area",
                "Include brand colors consistently",
                "Test on mobile before posting"
            ]
        }
    }

    layout_config = layouts.get(req.content_type, layouts["document"])

    return {
        "content_type": req.content_type,
        "layout_config": layout_config,
        "brand_colors": palette,
        "typography": TYPOGRAPHY,
        "agent": "THALIA",
        "timestamp": time_ctx["current_datetime"]
    }

@app.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve generated files"""
    file_path = f"{OUTPUT_DIR}/{filename}"
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/templates")
async def list_templates():
    """List available templates"""
    return {
        "presentation_templates": [
            {"id": "pitch_deck", "name": "Pitch Deck", "slides": 10},
            {"id": "company_overview", "name": "Company Overview", "slides": 8},
            {"id": "project_update", "name": "Project Update", "slides": 6},
            {"id": "training", "name": "Training Deck", "slides": 12}
        ],
        "document_templates": [
            {"id": "proposal", "name": "Business Proposal"},
            {"id": "report", "name": "Status Report"},
            {"id": "memo", "name": "Internal Memo"},
            {"id": "brief", "name": "Project Brief"}
        ],
        "thumbnail_styles": ["gradient", "solid", "pattern", "image"]
    }

@app.post("/batch/charts")
async def batch_create_charts(charts: List[ChartRequest]):
    """Create multiple charts in batch"""
    time_ctx = get_time_context()
    results = []

    for chart_req in charts:
        try:
            result = generate_chart(
                chart_type=chart_req.type,
                data=chart_req.data,
                style=chart_req.style,
                title=chart_req.title,
                width=chart_req.width,
                height=chart_req.height
            )
            results.append({
                "success": True,
                "chart_type": chart_req.type,
                **result
            })
        except Exception as e:
            results.append({
                "success": False,
                "chart_type": chart_req.type,
                "error": str(e)
            })

    await notify_event_bus("batch_charts_created", {
        "total": len(charts),
        "successful": sum(1 for r in results if r["success"])
    })

    return {
        "results": results,
        "total": len(charts),
        "successful": sum(1 for r in results if r["success"]),
        "agent": "THALIA",
        "timestamp": time_ctx["current_datetime"]
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8032)
