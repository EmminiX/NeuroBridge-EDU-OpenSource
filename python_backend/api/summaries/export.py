"""
Summary Export Endpoint
Export summaries as PDF or Markdown without database storage
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import os
from datetime import datetime
from pathlib import Path

router = APIRouter()


class ExportSummaryRequest(BaseModel):
    """Request schema for summary export"""
    title: str
    content: str
    transcript: Optional[str] = None
    format: str = "markdown"  # markdown or pdf


@router.post("/export")
async def export_summary(request: ExportSummaryRequest):
    """
    Export summary as PDF or Markdown
    
    Args:
        request: ExportSummaryRequest with summary data and format
        
    Returns:
        File download response
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in request.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        if request.format == "markdown":
            # Generate markdown content
            markdown_content = f"""# {request.title}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

{request.content}
"""
            
            if request.transcript:
                markdown_content += f"""

---

## Original Transcript

{request.transcript}
"""
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                tmp_file.write(markdown_content)
                tmp_file_path = tmp_file.name
            
            filename = f"{safe_title}_{timestamp}.md"
            
            return FileResponse(
                path=tmp_file_path,
                filename=filename,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
            
        elif request.format == "pdf":
            # Generate PDF using ReportLab with proper markdown rendering
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
            from reportlab.lib.units import inch
            import io
            import re
            
            def parse_markdown_to_reportlab(text):
                """Convert markdown text to ReportLab story elements"""
                lines = text.split('\n')
                story_elements = []
                current_list_items = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        # Handle accumulated list items
                        if current_list_items:
                            story_elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                            current_list_items = []
                        story_elements.append(Spacer(1, 0.1*inch))
                        continue
                    
                    # Handle headers
                    if line.startswith('## '):
                        if current_list_items:
                            story_elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                            current_list_items = []
                        header_text = line[3:].strip()
                        story_elements.append(Spacer(1, 0.2*inch))
                        story_elements.append(Paragraph(header_text, heading2_style))
                        story_elements.append(Spacer(1, 0.1*inch))
                    
                    elif line.startswith('# '):
                        if current_list_items:
                            story_elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                            current_list_items = []
                        header_text = line[2:].strip()
                        story_elements.append(Spacer(1, 0.2*inch))
                        story_elements.append(Paragraph(header_text, heading1_style))
                        story_elements.append(Spacer(1, 0.1*inch))
                    
                    # Handle bullet points
                    elif line.startswith('- '):
                        bullet_text = line[2:].strip()
                        # Convert **bold** to <b>bold</b> for ReportLab
                        bullet_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', bullet_text)
                        current_list_items.append(ListItem(Paragraph(bullet_text, normal_style)))
                    
                    # Handle regular paragraphs
                    else:
                        if current_list_items:
                            story_elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                            current_list_items = []
                        
                        # Convert **bold** to <b>bold</b> for ReportLab
                        paragraph_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                        story_elements.append(Paragraph(paragraph_text, normal_style))
                        story_elements.append(Spacer(1, 0.1*inch))
                
                # Handle any remaining list items
                if current_list_items:
                    story_elements.append(ListFlowable(current_list_items, bulletType='bullet'))
                
                return story_elements
            
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Define custom styles
            normal_style = styles['Normal']
            heading1_style = styles['Heading1']
            heading2_style = ParagraphStyle('Heading2', parent=styles['Heading2'], spaceAfter=12)
            
            # Add title
            title_style = styles['Title']
            story.append(Paragraph(request.title, title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Add timestamp
            story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Add summary header
            story.append(Paragraph("Summary", heading1_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Parse and add summary content with markdown formatting
            story.extend(parse_markdown_to_reportlab(request.content))
            
            # Add transcript if provided
            if request.transcript:
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph("Original Transcript", heading1_style))
                story.append(Spacer(1, 0.1*inch))
                
                # Parse transcript content as well
                story.extend(parse_markdown_to_reportlab(request.transcript))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(buffer.read())
                tmp_file_path = tmp_file.name
            
            filename = f"{safe_title}_{timestamp}.pdf"
            
            return FileResponse(
                path=tmp_file_path,
                filename=filename,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
            
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'markdown' or 'pdf'")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")