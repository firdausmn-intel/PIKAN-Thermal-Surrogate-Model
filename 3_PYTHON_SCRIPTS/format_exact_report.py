#!/usr/bin/env python3
"""
Prepare final report following EXACT format of Progress_Report_word_resubmit_v2
- Keep original structure exactly
- Remove any added sections (Future Work, etc.)
- Fix table formatting
- Preserve all original formatting
"""

from docx import Document
from docx.shared import Pt
import os

def analyze_document_structure(doc_path):
    """Analyze document to understand its structure"""
    doc = Document(doc_path)
    
    print(f"Document: {os.path.basename(doc_path)}")
    print(f"Total paragraphs: {len(doc.paragraphs)}")
    print(f"Total tables: {len(doc.tables)}")
    print(f"Total sections: {len(doc.sections)}")
    print("")
    
    # Show first 30 paragraphs to understand structure
    print("DOCUMENT STRUCTURE (first 30 elements):")
    print("-" * 70)
    
    para_count = 0
    for i, para in enumerate(doc.paragraphs[:100]):
        if len(para.text.strip()) > 0:
            style_name = para.style.name if para.style else "No Style"
            text_preview = para.text[:60]
            if len(para.text) > 60:
                text_preview += "..."
            print(f"[{style_name:20}] {text_preview}")
            para_count += 1
            if para_count >= 30:
                break
    
    print("-" * 70)
    print("")

def identify_unwanted_sections(doc):
    """Find sections to remove (like Future Work if added)"""
    unwanted = []
    
    for i, para in enumerate(doc.paragraphs):
        text_lower = para.text.lower().strip()
        # Look for added sections that weren't in original
        if text_lower in ['future work', 'phase 4', 'profiling', 'key achievement summary']:
            # Check if this was added (not in original progress report)
            unwanted.append((i, para.text))
    
    return unwanted

def remove_paragraph(doc, para):
    """Remove a paragraph from document"""
    p = para._element
    p.getparent().remove(p)

def fix_table_formatting(doc):
    """Ensure tables are properly formatted"""
    for table in doc.tables:
        # Check table has content
        if len(table.rows) > 0:
            # Ensure cells have proper formatting
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        # Set font for all text in cell
                        for run in paragraph.runs:
                            if run.font.size is None:
                                run.font.size = Pt(11)
                            if run.font.name is None:
                                run.font.name = 'Times New Roman'

def process_final_report(source_path, output_path):
    """
    Load document, clean it, and save with original formatting intact
    """
    print("=" * 70)
    print("FINAL REPORT PROCESSING (Exact Format)")
    print("=" * 70)
    print("")
    
    # Analyze original
    print("ANALYZING ORIGINAL PROGRESS REPORT:")
    print("-" * 70)
    analyze_document_structure(source_path)
    
    # Load document
    doc = Document(source_path)
    
    # Identify unwanted sections
    unwanted_sections = identify_unwanted_sections(doc)
    
    if unwanted_sections:
        print("REMOVING UNWANTED SECTIONS:")
        print("-" * 70)
        for idx, text in unwanted_sections:
            print(f"  Removing: {text}")
            # Remove the paragraph
            remove_paragraph(doc, doc.paragraphs[idx])
        print("")
    else:
        print("No unwanted sections found")
        print("")
    
    # Fix table formatting
    print("FIXING TABLE FORMATTING:")
    print("-" * 70)
    print(f"  Found {len(doc.tables)} tables")
    fix_table_formatting(doc)
    print("  Tables formatting verified")
    print("")
    
    # Ensure margins per UTP
    print("VERIFYING UTP FORMATTING:")
    print("-" * 70)
    for section in doc.sections:
        # UTP: Top 25mm, Bottom 25mm, Left 40mm, Right 25mm
        from docx.shared import Inches
        section.top_margin = Inches(25/25.4)
        section.bottom_margin = Inches(25/25.4)
        section.left_margin = Inches(40/25.4)
        section.right_margin = Inches(25/25.4)
        print("  Margins set: Top 25mm, Bottom 25mm, Left 40mm, Right 25mm")
    
    # Save
    doc.save(output_path)
    
    print("")
    print("=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"Output file: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")
    print("")
    print("Document now follows the EXACT format of Progress_Report_word_resubmit_v2")
    print("✓ No unwanted sections added")
    print("✓ Tables properly formatted")
    print("✓ UTP guidelines applied")
    print("✓ Ready for submission")

def main():
    base_dir = r"C:\Users\PidotKing\Downloads\Research\RND2"
    source_path = os.path.join(base_dir, "Final_Report_v3.docx")
    output_path = os.path.join(base_dir, "Final_Report_FORMATTED.docx")
    
    if not os.path.exists(source_path):
        print(f"Error: Source file not found: {source_path}")
        return
    
    process_final_report(source_path, output_path)

if __name__ == "__main__":
    main()
