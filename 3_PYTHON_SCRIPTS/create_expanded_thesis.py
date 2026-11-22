#!/usr/bin/env python3
"""
Create expanded version with longer introduction
Target: ~100 pages
Strategy: Expand Introduction section with more detailed background and context
"""

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def find_section_start(doc, section_name):
    """Find the paragraph index where a section starts"""
    for i, para in enumerate(doc.paragraphs):
        if section_name.upper() in para.text.upper():
            return i
    return None

def insert_introduction_expansion(doc, insert_index):
    """
    Insert expanded introduction content after the original introduction heading
    """
    
    expanded_content = [
        # Additional background on 3D-ICs
        {
            "heading": "1.1 Three-Dimensional Integrated Circuits: Architecture and Evolution",
            "paragraphs": [
                "Three-dimensional integrated circuits (3D-ICs) represent a paradigm shift in semiconductor design and manufacturing. Unlike traditional two-dimensional (2D) planar circuits, 3D-ICs stack multiple silicon dies vertically and interconnect them through through-silicon vias (TSVs). This vertical integration enables significant improvements in interconnect length reduction, power consumption, and performance metrics compared to their 2D counterparts.",
                
                "The evolution toward 3D-ICs was driven by the fundamental limitations encountered in continued 2D planar scaling. As feature sizes have shrunk to the nanometer regime, traditional scaling approaches face increasing challenges including increased interconnect delays, higher power dissipation, and manufacturing complexity. The International Technology Roadmap for Semiconductors (ITRS) identified 3D-IC integration as a critical technology enabler for continued performance improvement in the post-Moore's Law era.",
                
                "Modern 3D-IC architectures employ various integration schemes, including die-to-wafer stacking, wafer-to-wafer bonding, and chiplet-based designs. Each approach offers different trade-offs in terms of integration density, manufacturing yield, and thermal characteristics. The vertical interconnects (TSVs) in 3D-ICs are typically 10-100 micrometers in diameter and spaced at pitches ranging from 10-50 micrometers, fundamentally changing the thermal and electrical characteristics compared to traditional 2D layouts.",
                
                "The benefits of 3D-IC integration extend beyond performance improvements. By reducing interconnect lengths, 3D-ICs can achieve lower power consumption per operation, enabling more efficient computing platforms. Additionally, the ability to mix and match different technologies (heterogeneous integration) allows for more flexible design optimization, combining logic, memory, and specialized processing units in a single package.",
            ]
        },
        
        # Thermal challenges specific to 3D-ICs
        {
            "heading": "1.2 Thermal Challenges in Three-Dimensional Integrated Circuits",
            "paragraphs": [
                "While 3D-IC integration offers significant benefits, it introduces substantial thermal management challenges that have become increasingly critical as semiconductor density continues to increase. The vertical stacking of multiple active layers creates thermal hotspots with unprecedentedly high temperature gradients, fundamentally different from the thermal characteristics of 2D designs.",
                
                "One of the most critical challenges in 3D-IC thermal management is the phenomenon of thermal hotspots. These are localized regions of extremely high power density that can reach temperatures far exceeding the average chip temperature. In 3D-ICs, thermal hotspots are particularly problematic because heat generated in lower layers must conduct through the intermediate layers to reach the heat sink, creating temperature gradients that can exceed 100°C across distances of just a few hundred micrometers.",
                
                "The spatial proximity of multiple active layers in 3D-ICs amplifies thermal coupling effects. Heat generated in one layer directly influences the temperature profile of adjacent layers, creating complex three-dimensional heat flow patterns that are difficult to predict using traditional thermal analysis methods. This vertical thermal coupling means that localized hotspots in lower layers can significantly elevate the temperature of overlying layers, even if those layers have lower local power density.",
                
                "Temperature-dependent performance degradation is another critical concern in 3D-IC design. The delay of CMOS logic gates increases significantly with temperature, following a negative temperature coefficient of approximately -0.1% to -0.2% per °C. This temperature dependence means that thermal hotspots not only dissipate more power but also cause performance degradation in those regions, creating a positive feedback loop that can limit overall chip performance.",
                
                "Reliability concerns are exacerbated by the extreme temperatures and steep temperature gradients present in 3D-ICs. Electromigration, the movement of metal atoms in interconnects due to high current density, is exponentially accelerated by temperature, with failure rates increasing by roughly a factor of 2 for every 10°C increase in temperature. Additionally, thermal cycling from repeated power-on and power-off events, combined with the coefficient of thermal expansion (CTE) mismatch between different materials in the 3D stack, creates mechanical stress that can lead to die-level cracking and interconnect fatigue.",
                
                "These thermal challenges necessitate accurate predictive thermal simulation tools that can capture the complex heat flow patterns in 3D-ICs and enable designers to optimize thermal performance during the design phase rather than relying on post-silicon remediation.",
            ]
        },
        
        # Current simulation approaches
        {
            "heading": "1.3 Traditional Approaches to Thermal Simulation and Their Limitations",
            "paragraphs": [
                "Thermal simulation has long been recognized as essential for chip design and optimization. Traditional approaches to 3D-IC thermal analysis typically employ one of two complementary strategies: detailed physical simulation and simplified analytical models.",
                
                "Detailed physical simulation tools such as ANSYS Fluent, COMSOL Multiphysics, and specialized thermal simulators like HotSpot employ finite difference or finite element methods to solve the heat diffusion equation on discretized spatial grids. These tools can model complex geometries, material properties, and boundary conditions with high fidelity. However, this accuracy comes at a significant computational cost. A single thermal simulation of a realistic 3D-IC can require hours or even days of computation on high-performance computing systems, making iterative design exploration prohibitively expensive.",
                
                "The computational burden of detailed simulations is particularly acute for 3D-ICs because of the complexity of the vertical geometry. Simulating a full 3D-IC stack with appropriate spatial resolution to capture localized hotspots typically requires millions of mesh elements and correspondingly large memory requirements. This computational cost severely limits the design space that can be explored during the chip design phase.",
                
                "To address the computational limitations of detailed simulation, designers often employ reduced-order thermal models or analytical approximations. These simplified models make assumptions to enable faster computation, such as assuming uniform material properties, idealized geometries, or quasi-steady-state heat flow. While these simplified models can provide order-of-magnitude estimates of thermal behavior, they typically lack the fidelity needed to accurately predict extreme temperature gradients and localized hotspots that are characteristic of modern 3D-ICs.",
                
                "A critical limitation of traditional thermal modeling approaches is the spectral bias problem. When neural networks or machine learning models are trained to emulate thermal simulators, they tend to perform well on average values but struggle to accurately capture high-frequency spatial variations—the sharp temperature peaks corresponding to thermal hotspots. This spectral bias arises from the fundamental characteristics of how neural networks learn patterns from training data, favoring smooth, low-frequency variations over sharp, discontinuous features.",
                
                "The existing gap between the computational expense of detailed simulation and the limited fidelity of simplified models creates a critical need for new approaches that can combine computational efficiency with high-fidelity prediction, particularly for capturing extreme thermal gradients in 3D-IC designs.",
            ]
        },
        
        # Machine learning context
        {
            "heading": "1.4 Machine Learning and Neural Operators for Scientific Computing",
            "paragraphs": [
                "Recent years have witnessed a paradigm shift in scientific computing toward machine learning-based approaches that can complement or augment traditional simulation tools. These approaches leverage the ability of neural networks to learn complex mappings from limited data, enabling faster inference once training is complete.",
                
                "Traditional neural networks, including multilayer perceptrons and convolutional neural networks, have been successfully applied to various scientific computing problems. These architectures excel at learning mappings from spatially structured data to prediction targets. However, their application to operator learning—learning the implicit operators that map input functions to output functions—has been more limited, particularly for problems involving physical laws and complex spatial variations.",
                
                "Neural operators represent a newer class of machine learning architectures specifically designed to learn the action of continuous operators. Rather than predicting a single output value given an input vector, neural operators learn to map entire input functions to output functions in a way that is resolution-invariant and can generalize to function values and domains not seen during training. This capability is fundamentally important for scientific computing applications where the resolution of simulations may vary and where models trained on coarse grids need to work on fine grids.",
                
                "Physics-informed neural networks (PINNs) take this further by incorporating knowledge of the governing physical equations into the neural network training process. PINNs are trained not just on observed data but also on the residuals of the governing differential equations, allowing the network to enforce physical constraints during learning. This physics-informed approach has demonstrated promise for solving inverse problems, surrogate modeling, and discovering equations from data.",
                
                "However, traditional PINNs and neural operators can still suffer from spectral bias when applied to problems with sharp transitions or high-frequency features. This limitation is particularly acute for thermal problems with localized hotspots that require accurate representation of sharp temperature peaks on complex geometries.",
            ]
        },
        
        # Research motivation and contribution
        {
            "heading": "1.5 Research Motivation and Thesis Objectives",
            "paragraphs": [
                "The convergence of three important factors motivates this research work: (1) the increasing criticality of accurate thermal simulation for 3D-IC design, (2) the computational expense of traditional detailed simulation approaches, and (3) the recent advances in neural operator-based learning for scientific computing.",
                
                "While neural operators and physics-informed approaches show promise, their application to thermal simulation has not fully addressed the spectral bias challenge. This thesis is motivated by the hypothesis that combining physics-informed regularization with modern neural operator architectures, specifically Kolmogorov-Arnold Networks (KANs), can overcome spectral bias and enable accurate prediction of extreme temperature gradients in 3D-ICs.",
                
                "The primary objectives of this research are: (1) to develop a novel physics-informed neural operator approach specifically tailored for 3D-IC thermal simulation, (2) to address the spectral bias problem in predicting localized thermal hotspots, (3) to validate the approach on realistic 3D-IC geometries including complex scenarios with adjacent hotspots, and (4) to demonstrate that the resulting models can achieve high inference speed while maintaining simulation fidelity.",
                
                "This work builds on recent developments in neural operator theory and physics-informed machine learning, while directly addressing the gap between computational efficiency and simulation fidelity in 3D-IC thermal analysis. By combining domain knowledge about thermal physics with modern deep learning architectures, this research aims to enable more efficient design space exploration in 3D-IC development.",
            ]
        }
    ]
    
    # Find where to insert (after the main introduction heading/first paragraph)
    # Look for Section 1 or Introduction heading
    intro_section_idx = None
    for i in range(insert_index, min(insert_index + 20, len(doc.paragraphs))):
        if "1." in doc.paragraphs[i].text and len(doc.paragraphs[i].text) < 100:
            # Found section 1
            intro_section_idx = i + 1
            break
    
    if intro_section_idx is None:
        intro_section_idx = insert_index + 1
    
    # Insert expanded content
    inserted_count = 0
    for section in expanded_content:
        # Insert heading
        heading_para = doc.paragraphs[intro_section_idx + inserted_count].insert_paragraph_before(
            section["heading"]
        )
        heading_para.style = 'Heading 2'
        heading_para.paragraph_format.space_before = Pt(12)
        heading_para.paragraph_format.space_after = Pt(6)
        inserted_count += 1
        
        # Insert paragraphs
        for para_text in section["paragraphs"]:
            new_para = doc.paragraphs[intro_section_idx + inserted_count].insert_paragraph_before(
                para_text
            )
            new_para.style = 'Normal'
            new_para.paragraph_format.line_spacing = 1.5
            new_para.paragraph_format.space_after = Pt(12)
            new_para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            # Set font for all runs
            for run in new_para.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)
            
            inserted_count += 1
    
    return inserted_count

def create_expanded_thesis(source_path, output_path):
    """Main function to create expanded thesis"""
    
    print("=" * 70)
    print("CREATING EXPANDED THESIS (~100 pages)")
    print("=" * 70)
    print("")
    
    # Load source document
    doc = Document(source_path)
    
    print(f"Source document loaded: {source_path}")
    print(f"Original paragraphs: {len(doc.paragraphs)}")
    print(f"Original tables: {len(doc.tables)}")
    print("")
    
    # Find Introduction section
    intro_idx = None
    for i, para in enumerate(doc.paragraphs):
        if "INTRODUCTION" in para.text.upper() or "1. INTRODUCTION" in para.text.upper():
            intro_idx = i
            print(f"Found Introduction section at paragraph {i}")
            break
    
    if intro_idx is None:
        # Look for Section 1
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip().startswith("1.") or "INTRODUCTION" in para.text:
                intro_idx = i
                break
    
    if intro_idx is None:
        print("WARNING: Could not find Introduction section")
        print("Inserting expanded introduction after first 50 paragraphs")
        intro_idx = 50
    
    # Insert expanded introduction content
    print("Inserting expanded introduction content...")
    inserted = insert_introduction_expansion(doc, intro_idx)
    print(f"Added {inserted} new paragraphs to introduction")
    print("")
    
    # Save expanded document
    doc.save(output_path)
    
    print(f"Expanded thesis saved: {output_path}")
    print(f"New paragraph count: {len(doc.paragraphs)}")
    print("")
    
    # Estimate page count
    # Rough estimate: ~300-400 words per page, 12pt Times New Roman, 1.5 spacing
    all_text = " ".join([p.text for p in doc.paragraphs])
    word_count = len(all_text.split())
    estimated_pages = int(word_count / 350)  # Conservative estimate
    
    print("=" * 70)
    print("EXPANSION COMPLETE")
    print("=" * 70)
    print(f"Estimated word count: {word_count:,}")
    print(f"Estimated pages: {estimated_pages}")
    print(f"Target: ~100 pages")
    print("")
    print("Document is ready for use.")

def main():
    base_dir = r"C:\Users\PidotKing\Downloads\Research\RND2"
    source_path = f"{base_dir}\\Final_Report_FORMATTED.docx"
    output_path = f"{base_dir}\\Final_Report_EXPANDED_100pages.docx"
    
    create_expanded_thesis(source_path, output_path)

if __name__ == "__main__":
    main()
