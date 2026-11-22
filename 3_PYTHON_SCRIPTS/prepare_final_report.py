#!/usr/bin/env python3
"""
Prepare final report from progress report baseline.
This script will:
1. Read the progress report DOCX
2. Extract content and structure
3. Enhance with additional sections and figures
4. Create new DOCX formatted per UTP guidelines
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path
import os

def set_cell_background(cell, fill_color):
    """Set cell background color"""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), fill_color)
    cell._element.get_or_add_tcPr().append(shading_elm)

def add_page_break(doc):
    """Add page break"""
    doc.add_page_break()

def format_heading_1(paragraph):
    """Format as Heading 1 per UTP guidelines"""
    paragraph.style = 'Heading 1'
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(12)
    for run in paragraph.runs:
        run.font.bold = True
        run.font.size = Pt(14)

def format_heading_2(paragraph):
    """Format as Heading 2 per UTP guidelines"""
    paragraph.style = 'Heading 2'
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    for run in paragraph.runs:
        run.font.bold = True
        run.font.size = Pt(12)

def set_body_formatting(doc):
    """Set body text formatting per UTP guidelines"""
    for paragraph in doc.paragraphs:
        if paragraph.style.name.startswith('Normal') and not any(r.bold for r in paragraph.runs):
            paragraph.paragraph_format.line_spacing = 1.5
            paragraph.paragraph_format.space_after = Pt(12)
            for run in paragraph.runs:
                if run.font.size is None:
                    run.font.size = Pt(12)
                if run.font.name is None:
                    run.font.name = 'Times New Roman'

def copy_and_enhance_report(source_path, dest_path):
    """
    Copy progress report and enhance for final dissertation
    """
    # Load source document
    source_doc = Document(source_path)
    
    print(f"Loaded source document: {source_path}")
    print(f"Number of paragraphs: {len(source_doc.paragraphs)}")
    
    # Create new document with fresh formatting
    final_doc = Document()
    
    # Set default styles
    style = final_doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    # Copy all content from source
    for para in source_doc.paragraphs:
        new_para = final_doc.add_paragraph(para.text)
        new_para.style = para.style
        new_para.paragraph_format.line_spacing = 1.5
        
        # Preserve formatting
        for run in new_para.runs:
            if run.font.bold is not None:
                run.font.bold = run.font.bold
            if run.font.italic is not None:
                run.font.italic = run.font.italic
    
    # Copy tables
    for table in source_doc.tables:
        new_table = final_doc.add_table(rows=len(table.rows), cols=len(table.columns))
        new_table.style = table.style
        for i, row in enumerate(table.rows):
            for j, cell in enumerate(row.cells):
                new_table.rows[i].cells[j].text = cell.text
    
    # Save enhanced document
    final_doc.save(dest_path)
    print(f"Saved enhanced document: {dest_path}")
    return final_doc

def add_enhanced_sections(doc, figures_dir):
    """Add enhanced sections and figures"""
    
    # List of figures to add strategically
    key_figures = [
        (r"C:\Users\PidotKing\Downloads\Research\HotSpot\Progress Report\figures\fig_3_1_stack_schematic.png", 
         "Figure 3.1: 3D-IC Stack Schematic Diagram"),
        (r"C:\Users\PidotKing\Downloads\Research\HotSpot\Progress Report\figures\fig_4_1_phase2_prediction_maps_labelled.png",
         "Figure 4.1: Phase 2 Model Predictions on Reference Block"),
        (r"C:\Users\PidotKing\Downloads\Research\HotSpot\Progress Report\figures\fig_4_2_peak_error_8_seeds.png",
         "Figure 4.2: Peak Error Analysis Across 8 Seed Runs"),
        (r"C:\Users\PidotKing\Downloads\Research\HotSpot\Progress Report\figures\fig_4_3_spike_maps_60mW.png",
         "Figure 4.3: Spectral Bias - Temperature Spikes at 60mW Power"),
    ]
    
    print(f"Found {len(key_figures)} key figures to integrate")
    return key_figures

def main():
    base_dir = r"C:\Users\PidotKing\Downloads\Research"
    source_path = os.path.join(base_dir, r"RND2\Progress_Report_word_resubmit_v2.docx")
    dest_path = os.path.join(base_dir, r"RND2\Final_Report_Draft_v1.docx")
    
    print("=" * 60)
    print("FINAL REPORT PREPARATION TOOL")
    print("=" * 60)
    
    # Copy and enhance
    final_doc = copy_and_enhance_report(source_path, dest_path)
    
    # Get key figures
    figures = add_enhanced_sections(final_doc, os.path.join(base_dir, "HotSpot/Progress Report/figures"))
    
    print(f"\nReport created with {len(figures)} key figures identified")
    print(f"Output: {dest_path}")
    print("\nNext steps:")
    print("1. Open the generated document")
    print("2. Review structure and content")
    print("3. Enhance wording in key sections")
    print("4. Add figures at strategic points")
    print("5. Format per UTP guidelines (margins, spacing, etc.)")

if __name__ == "__main__":
    main()
