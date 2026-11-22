#!/usr/bin/env python3
"""
Create expanded version with longer Introduction AND Literature Review
Target: ~100 pages
Strategy: Significantly expand both Introduction and Literature Review sections
"""

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

def Mm(mm):
    """Convert millimeters to Inches for margins"""
    from docx.shared import Inches
    return Inches(mm / 25.4)

def find_section_by_text(doc, search_text):
    """Find section index by searching for text"""
    for i, para in enumerate(doc.paragraphs):
        if search_text.lower() in para.text.lower():
            return i
    return None

def insert_paragraphs_after_index(doc, insert_index, new_paragraphs_data):
    """
    Insert new paragraphs after a specific index
    new_paragraphs_data is a list of dicts with 'heading' and 'paragraphs' keys
    """
    
    inserted_count = 0
    
    for section in new_paragraphs_data:
        # Insert heading if provided
        if 'heading' in section and section['heading']:
            heading_para = doc.paragraphs[insert_index + inserted_count].insert_paragraph_before(
                section['heading']
            )
            heading_para.style = 'Heading 2'
            heading_para.paragraph_format.space_before = Pt(12)
            heading_para.paragraph_format.space_after = Pt(6)
            heading_para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            # Format heading font
            for run in heading_para.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)
                run.font.bold = True
            
            inserted_count += 1
        
        # Insert body paragraphs
        for para_text in section.get('paragraphs', []):
            new_para = doc.paragraphs[insert_index + inserted_count].insert_paragraph_before(
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

def get_introduction_expansion():
    """Get expanded introduction content"""
    return [
        {
            "heading": "1.1 Three-Dimensional Integrated Circuits: Architecture and Evolution",
            "paragraphs": [
                "Three-dimensional integrated circuits (3D-ICs) represent a fundamental paradigm shift in semiconductor design and manufacturing. Unlike traditional two-dimensional (2D) planar circuits, 3D-ICs stack multiple silicon dies vertically and interconnect them through through-silicon vias (TSVs). This vertical integration enables significant improvements in interconnect length reduction, power consumption, and performance metrics compared to their 2D counterparts.",
                
                "The evolution toward 3D-IC technology was driven by the fundamental limitations encountered in continued 2D planar scaling following Moore's Law. As feature sizes have shrunk to the nanometer regime, traditional scaling approaches face increasing challenges including increased interconnect delays, exponentially higher power dissipation per unit area, and manufacturing complexity that grows super-linearly with transistor count. The International Technology Roadmap for Semiconductors (ITRS) identified 3D-IC integration as a critical technology enabler for continued performance improvement in the post-Moore's Law era and beyond.",
                
                "Modern 3D-IC architectures employ various integration schemes, including die-to-wafer stacking, wafer-to-wafer bonding, chiplet-based heterogeneous designs, and advanced packaging approaches such as chiplet and chipstack architectures. Each approach offers different trade-offs in terms of integration density, manufacturing yield, thermal characteristics, and cost. The vertical interconnects (TSVs) in 3D-ICs are typically 10-100 micrometers in diameter and spaced at pitches ranging from 10-50 micrometers, fundamentally changing the thermal, electrical, and mechanical characteristics compared to traditional 2D layouts.",
                
                "The benefits of 3D-IC integration extend far beyond simple performance improvements. By reducing average interconnect lengths from millimeters to micrometers, 3D-ICs can achieve substantially lower power consumption per operation, enabling more efficient computing platforms and improved energy efficiency metrics. Additionally, the ability to mix and match different technologies and process nodes through heterogeneous integration allows for more flexible design optimization, enabling designers to combine logic, memory, analog circuits, and specialized processing units in a single package, each optimized for its specific function.",
                
                "The economic benefits of 3D integration are also significant. By enabling higher performance density without requiring more aggressive transistor scaling, 3D-ICs can extend the economic viability of mature process technologies and potentially slow the increase in chip manufacturing costs. This has implications for cost-performance optimization across a wide range of applications from mobile computing to data center servers.",
            ]
        },
        
        {
            "heading": "1.2 Thermal Challenges in Three-Dimensional Integrated Circuits",
            "paragraphs": [
                "While 3D-IC integration offers significant benefits, it simultaneously introduces substantial thermal management challenges that have become increasingly critical as semiconductor density continues to increase at an unprecedented rate. The vertical stacking of multiple active layers creates thermal hotspots with unprecedentedly high temperature gradients and spatial variation, fundamentally different in character from the thermal characteristics of 2D designs.",
                
                "One of the most critical and distinctive challenges in 3D-IC thermal management is the phenomenon of thermal hotspots. These are localized regions of extremely high power density that can reach temperatures far exceeding the average chip temperature, sometimes by 50°C or more. In 3D-ICs, thermal hotspots are particularly problematic because heat generated in lower layers must conduct through the intermediate layers to reach the heat sink, creating temperature gradients that can exceed 100°C across distances of just a few hundred micrometers or less.",
                
                "The spatial proximity of multiple active layers in 3D-ICs amplifies thermal coupling effects in ways not present in 2D designs. Heat generated in one layer directly influences the temperature profile of all adjacent layers, creating complex three-dimensional heat flow patterns that are difficult to predict using traditional thermal analysis methods or simplified analytical models. This vertical thermal coupling means that localized hotspots in lower layers can significantly elevate the temperature of overlying layers, even if those layers have lower local power density or lower switching activity.",
                
                "The fundamental governing equation for steady-state heat conduction in 3D is given by the Fourier heat equation: ∇²T = -q/k, where T is temperature, q is heat generation, and k is thermal conductivity. In 3D-ICs with multiple material layers and complex geometries, this equation becomes increasingly difficult to solve analytically, requiring numerical methods that are computationally expensive.",
                
                "Temperature-dependent performance degradation is another critical concern in 3D-IC design that creates challenging feedback loops. The delay of CMOS logic gates increases significantly with temperature, following a negative temperature coefficient of approximately -0.1% to -0.2% per °C. This temperature dependence means that thermal hotspots not only dissipate more power but also cause performance degradation in those regions, potentially creating a positive feedback loop that can limit overall chip performance and system throughput.",
                
                "Reliability concerns are exacerbated by the extreme temperatures and steep temperature gradients present in 3D-ICs. Electromigration, the movement of metal atoms in interconnects due to high current density, is exponentially accelerated by temperature, with failure rates increasing by roughly a factor of 2 for every 10°C increase in temperature. Additionally, thermal cycling from repeated power-on and power-off events, combined with the coefficient of thermal expansion (CTE) mismatch between different materials in the 3D stack (silicon, copper, dielectrics), creates mechanical stress that can lead to die-level cracking, interconnect fatigue, and long-term reliability degradation.",
                
                "These thermal challenges necessitate accurate predictive thermal simulation tools that can capture the complex three-dimensional heat flow patterns in 3D-ICs and enable designers to optimize thermal performance during the design phase rather than relying on post-silicon remediation or thermal management band-aids.",
            ]
        },
        
        {
            "heading": "1.3 Traditional Approaches to Thermal Simulation and Their Limitations",
            "paragraphs": [
                "Thermal simulation has long been recognized as essential for chip design and optimization in the semiconductor industry. Traditional approaches to 3D-IC thermal analysis typically employ one of two complementary strategies: detailed physical simulation using discretization methods, and simplified analytical or reduced-order models.",
                
                "Detailed physical simulation tools such as ANSYS Fluent, COMSOL Multiphysics, and specialized thermal simulators like HotSpot employ finite difference (FD) or finite element methods (FEM) to solve the heat diffusion equation on discretized spatial grids. These tools can model complex geometries, spatially-varying material properties, nonlinear thermal effects, and sophisticated boundary conditions with high fidelity. However, this accuracy comes at a significant computational cost that often limits practical utility.",
                
                "The computational burden of detailed simulations is particularly acute for 3D-ICs because of the inherent complexity of the vertical geometry and the need for fine spatial resolution. Simulating a full 3D-IC stack with appropriate spatial resolution to capture localized hotspots typically requires millions of mesh elements and correspondingly large memory requirements. A single thermal simulation of a realistic 3D-IC can require hours or even days of computation on high-performance computing systems, making iterative design space exploration prohibitively expensive.",
                
                "To address the computational limitations of detailed simulation, designers often employ reduced-order thermal models or analytical approximations. These simplified models make simplifying assumptions to enable faster computation, such as assuming uniform material properties, idealized geometries, quasi-steady-state heat flow, or homogeneous power distributions. While these simplified models can provide order-of-magnitude estimates of thermal behavior and are suitable for high-level architecture trade-offs, they typically lack the fidelity needed to accurately predict extreme temperature gradients and localized hotspots that are characteristic of modern aggressive 3D-ICs.",
                
                "A critical limitation of traditional thermal modeling approaches is the spectral bias problem. When neural networks or machine learning models are trained to emulate thermal simulators, they tend to perform well on average values and smooth variations but struggle to accurately capture high-frequency spatial variations—the sharp temperature peaks corresponding to thermal hotspots. This spectral bias arises from fundamental characteristics of how neural networks learn patterns from training data, inherently favoring smooth, low-frequency variations over sharp, discontinuous features.",
                
                "The existing gap between the computational expense of detailed simulation and the limited fidelity of simplified models creates a critical need for new approaches that can combine computational efficiency with high-fidelity prediction, particularly for capturing extreme thermal gradients and accurate hotspot characterization in 3D-IC designs.",
            ]
        },
        
        {
            "heading": "1.4 Machine Learning and Neural Operators for Scientific Computing",
            "paragraphs": [
                "Recent years have witnessed a paradigm shift in scientific computing toward machine learning-based approaches that can complement or augment traditional simulation tools. These approaches leverage the ability of neural networks to learn complex nonlinear mappings from limited data, enabling faster inference once training is complete compared to running full numerical simulations.",
                
                "Traditional neural networks, including multilayer perceptrons (MLPs) and convolutional neural networks (CNNs), have been successfully applied to various scientific computing problems. These architectures excel at learning mappings from spatially structured data to prediction targets. However, their application to operator learning—learning the implicit operators that map input functions to output functions—has been more limited, particularly for problems involving complex physical laws and extreme spatial variations.",
                
                "Neural operators represent a newer class of machine learning architectures specifically designed to learn the action of continuous operators. Rather than predicting a single scalar output value given an input vector, neural operators learn to map entire input functions to output functions in a way that is resolution-invariant and can generalize to function values and domains not seen during training. This capability is fundamentally important for scientific computing applications where the resolution of simulations may vary and where models trained on coarse grids need to work reliably on fine grids.",
                
                "Physics-informed neural networks (PINNs) take this further by incorporating knowledge of the governing physical equations into the neural network training process. PINNs are trained not just on observed simulation data but also on the residuals of the governing differential equations, allowing the network to enforce physical constraints during learning. This physics-informed approach has demonstrated promise for solving inverse problems, surrogate modeling, discovering equations from noisy data, and solving forward problems with limited training data.",
                
                "However, traditional PINNs and neural operators can still suffer from spectral bias when applied to problems with sharp transitions or high-frequency features. This limitation is particularly acute for thermal problems with localized hotspots that require accurate representation of sharp temperature peaks on complex geometries. The spectral bias problem manifests as the network preferentially learning smooth features while missing sharp peaks, leading to substantial errors in hotspot prediction.",
            ]
        },
        
        {
            "heading": "1.5 Kolmogorov-Arnold Networks and Overcoming Spectral Bias",
            "paragraphs": [
                "Kolmogorov-Arnold Networks (KANs) represent a recent innovation in neural network architecture design inspired by the Kolmogorov-Arnold representation theorem. The theorem states that any continuous function can be represented as a composition of continuous univariate functions and the binary operation of addition. This theoretical foundation suggests that neural architectures based on this principle might have better expressivity for capturing sharp features compared to traditional architectures.",
                
                "Unlike traditional MLPs that use fixed activation functions at neurons, KANs employ learnable univariate functions (splines or other basis functions) on the edges connecting neurons. This fundamental architectural difference allows KANs to adapt their activation functions during training to better fit the target function's characteristics, potentially enabling better representation of both smooth and sharp features.",
                
                "Recent applications of KANs to scientific computing problems have shown promising results in overcoming spectral bias. By combining the learnable activation functions of KANs with physics-informed training strategies, researchers have demonstrated improved accuracy for capturing sharp features and high-frequency variations in solution fields.",
            ]
        },
        
        {
            "heading": "1.6 Research Motivation and Thesis Objectives",
            "paragraphs": [
                "The convergence of three important factors motivates this research work: (1) the increasing criticality of accurate thermal simulation for 3D-IC design and verification, (2) the computational expense of traditional detailed simulation approaches, and (3) the recent advances in neural operator-based learning for scientific computing.",
                
                "While neural operators and physics-informed approaches show promise, their application to thermal simulation has not fully addressed the spectral bias challenge for predicting extreme temperature gradients. This thesis is motivated by the hypothesis that combining physics-informed regularization with modern neural operator architectures, specifically Kolmogorov-Arnold Networks (KANs), can overcome spectral bias and enable accurate prediction of extreme temperature gradients in 3D-ICs.",
                
                "The primary objectives of this research are: (1) to develop a novel physics-informed neural operator approach specifically tailored for 3D-IC thermal simulation, (2) to address the spectral bias problem in predicting localized thermal hotspots with extreme temperature gradients, (3) to validate the approach on realistic 3D-IC geometries including complex scenarios with adjacent hotspots and challenging thermal scenarios, and (4) to demonstrate that the resulting models can achieve high inference speed while maintaining simulation fidelity comparable to detailed numerical solvers.",
                
                "This work builds on recent developments in neural operator theory and physics-informed machine learning, while directly addressing the gap between computational efficiency and simulation fidelity in 3D-IC thermal analysis. By combining domain knowledge about thermal physics with modern deep learning architectures, this research aims to enable more efficient design space exploration in 3D-IC development.",
            ]
        }
    ]

def get_literature_review_expansion():
    """Get expanded literature review content"""
    return [
        {
            "heading": "2.1 Historical Development of Thermal Simulation in Semiconductor Design",
            "paragraphs": [
                "Thermal simulation has evolved significantly over the past three decades as semiconductor power dissipation became an increasingly critical design concern. Early thermal analysis in the 1990s relied primarily on analytical models and simplified empirical relationships. As feature sizes decreased and power density increased, the need for more accurate simulation became apparent.",
                
                "The development of tools like HotSpot in the mid-2000s represented a major milestone in thermal simulation research. HotSpot introduced efficient thermal modeling approaches specifically tailored for processor design, enabling faster thermal analysis than full finite element simulations while maintaining reasonable accuracy. The tool discretizes the chip into a grid of thermal cells and solves the coupled thermal differential equations, providing a good balance between accuracy and speed.",
                
                "However, even with tools like HotSpot, the fundamental computational cost of running thermal simulations remains significant. For 3D-ICs with complex geometry and multiple active layers, the computational burden grows substantially, making real-time or near-real-time thermal feedback during design optimization challenging.",
            ]
        },
        
        {
            "heading": "2.2 Physics of Heat Conduction in Semiconductor Devices",
            "paragraphs": [
                "Heat conduction in semiconductors and semiconductor packaging follows Fourier's law of heat conduction, which states that the heat flux is proportional to the negative gradient of temperature: q = -k∇T. For multi-dimensional steady-state heat conduction, this leads to the Poisson equation: ∇²T = -q/k.",
                
                "In semiconductor devices, thermal conductivity varies significantly with material type. Silicon has relatively high thermal conductivity (~150 W/m-K at room temperature), while dielectric materials like silicon dioxide have much lower conductivity (~1.4 W/m-K). This material heterogeneity in 3D-ICs creates complex temperature profiles as heat flows preferentially through high-conductivity paths.",
                
                "Temperature-dependent thermal properties add another layer of complexity. Thermal conductivity in semiconductors generally decreases with increasing temperature, while thermal resistance increases. This temperature dependence means that the governing equations are not perfectly linear, requiring iterative or nonlinear solution methods for accurate results.",
                
                "In transient thermal analysis, the time-dependent heat equation must be solved: ρc∂T/∂t = ∇²(kT) + q, where ρ is density, c is heat capacity, and t is time. This parabolic PDE introduces additional complexity and computational cost compared to steady-state analysis.",
            ]
        },
        
        {
            "heading": "2.3 Finite Element and Finite Difference Methods for Thermal Simulation",
            "paragraphs": [
                "Finite element methods (FEM) represent the dominant approach for detailed thermal simulation in commercial tools. FEM discretizes the domain into elements, typically tetrahedral or hexahedral, and solves the weak form of the governing equations. FEM provides flexibility in handling complex geometries and boundary conditions, making it ideal for detailed thermal analysis.",
                
                "Finite difference methods (FDM) offer an alternative discretization approach that is particularly well-suited for structured grids. FDM approximates derivatives using Taylor series expansions on a regular grid, resulting in simpler implementation compared to FEM but less geometric flexibility.",
                
                "Both FEM and FDM require mesh generation and refinement to achieve adequate spatial resolution, particularly in regions with high thermal gradients. For 3D-IC thermal analysis, appropriate mesh resolution can require millions of elements, leading to substantial memory requirements and computational time.",
                
                "Multigrid methods and other advanced solution techniques have been developed to accelerate convergence of thermal simulations. These methods exploit the multiscale nature of heat conduction to achieve faster convergence compared to simple iterative solvers.",
            ]
        },
        
        {
            "heading": "2.4 Reduced-Order Thermal Modeling",
            "paragraphs": [
                "Reduced-order models (ROMs) represent an alternative approach to accelerating thermal simulation. ROMs project the full-dimensional problem onto a lower-dimensional subspace, reducing computational cost while attempting to maintain reasonable accuracy. Principal Component Analysis (PCA) and Proper Orthogonal Decomposition (POD) are common techniques for constructing reduced bases.",
                
                "The basic idea behind ROMs is to represent the temperature field as a linear combination of basis functions: T(x,y,z,t) ≈ Σᵢ αᵢ(t)φᵢ(x,y,z), where φᵢ are basis functions and αᵢ are time-dependent coefficients. By solving only for the low-dimensional coefficients, the computational cost can be reduced by orders of magnitude.",
                
                "However, ROMs face fundamental limitations for capturing sharp features and extreme variations that are not well-represented in the basis functions. If the basis functions are computed from training data that lacks sharp hotspots, the ROM will inherently be unable to represent such features accurately.",
                
                "Parametric ROMs extend this approach to handle parameter variations, enabling faster thermal analysis across different power distributions and thermal scenarios. However, the same limitations regarding sharp features apply.",
            ]
        },
        
        {
            "heading": "2.5 Machine Learning Applications in Thermal Management",
            "paragraphs": [
                "Over the past five to ten years, machine learning has been increasingly applied to thermal management and thermal simulation problems in semiconductors. Early applications focused on predicting peak temperature or average temperature given power distributions using simple machine learning models like support vector machines (SVMs) or decision trees.",
                
                "Deep learning approaches, particularly convolutional neural networks (CNNs) and fully convolutional networks (FCNs), have shown improved performance for spatially-structured thermal prediction problems. These models can learn to predict full temperature maps from power maps and have demonstrated reasonable speed advantages over simulation-based approaches.",
                
                "However, most prior work on neural network-based thermal surrogates has focused on predicting smooth temperature fields or average temperatures. Accurate prediction of localized hotspots with sharp temperature peaks remains challenging due to spectral bias—the tendency of neural networks to learn smooth, low-frequency features better than sharp, high-frequency features.",
                
                "Several approaches have been proposed to address spectral bias in neural networks, including: (1) using periodic activation functions, (2) incorporating Fourier features in the input, (3) applying Fourier transform to the output, and (4) using residual connections that explicitly model the difference between smooth and sharp components.",
            ]
        },
        
        {
            "heading": "2.6 Physics-Informed Neural Networks (PINNs)",
            "paragraphs": [
                "Physics-informed neural networks represent a significant paradigm shift in neural network application to scientific computing. Rather than training purely on data, PINNs incorporate knowledge of governing physical equations into the training objective. The loss function for a PINN typically includes both a data term and a physics term.",
                
                "For thermal problems, the physics term enforces the heat equation: ∇²T + q/k = 0 (steady-state) or ρc∂T/∂t - ∇²(kT) - q = 0 (transient). The network is trained to minimize both the difference from observed data and the residual of the governing equation.",
                
                "PINNs have been successfully applied to various PDEs including heat diffusion, fluid dynamics, and wave equations. The physics-informed approach enables training with less data compared to pure data-driven approaches and can improve generalization to new scenarios.",
                
                "However, PINNs are not immune to spectral bias. When the solution has sharp features, PINNs still struggle to capture them accurately. Additionally, training PINNs requires computing derivatives of the network output with respect to inputs (via automatic differentiation), which can be computationally expensive and numerically unstable for high-order derivatives.",
            ]
        },
        
        {
            "heading": "2.7 Neural Operators: DeepONet and Fourier Neural Operators",
            "paragraphs": [
                "Neural operators represent an advanced class of deep learning models specifically designed to learn mappings between function spaces. DeepONet (Deep Operator Network) is a framework where a trunk network encodes the input function and branch networks encode the query location, with the final output combining these components.",
                
                "Fourier Neural Operators (FNO) leverage the Fourier transform to implement convolution operations efficiently in frequency domain. FNO applies convolution in Fourier space by multiplication, exploiting Fast Fourier Transform algorithms for efficiency. FNO has shown impressive performance on various PDE-based problems including fluid dynamics and heat diffusion.",
                
                "A key advantage of neural operators is resolution-invariance: models trained on data at one resolution can be applied to data at different resolutions. This property is valuable for scientific computing where simulation resolution may vary.",
                
                "However, FNO and DeepONet can also suffer from spectral bias when high-frequency features are present. The periodic boundary conditions assumed by FFT-based approaches can be problematic for some domains.",
            ]
        },
        
        {
            "heading": "2.8 Spectral Bias in Neural Networks",
            "paragraphs": [
                "Spectral bias describes the phenomenon where neural networks, particularly those with smooth activation functions like ReLU or tanh, tend to learn low-frequency features faster than high-frequency features. This bias has been theoretically analyzed and empirically observed across many domains.",
                
                "For thermal problems with sharp hotspots, spectral bias is particularly problematic. The sharp temperature peaks require high-frequency Fourier components to represent accurately, but neural networks naturally bias toward low-frequency smooth components.",
                
                "Several approaches have been proposed to overcome spectral bias: (1) positional encoding using periodic functions like sin(2πkx) for different frequencies k, (2) using networks with higher expressivity like KANs, (3) direct supervision of high-frequency components, and (4) hybrid approaches combining neural networks with traditional solvers.",
                
                "Recent work on KANs and other learnable activation function approaches shows promise in reducing spectral bias by allowing the network to adaptively learn features across different frequency scales.",
            ]
        },
        
        {
            "heading": "2.9 State of the Art in AI-based Thermal Simulation",
            "paragraphs": [
                "Current state-of-the-art approaches to neural network-based thermal simulation generally fall into several categories: (1) pure data-driven CNN/FCN approaches, (2) physics-informed neural networks, (3) neural operators (DeepONet, FNO), and (4) hybrid physics-ML approaches.",
                
                "Among these approaches, physics-informed methods have generally shown better generalization and reliability for thermal problems. However, challenges remain in accurately capturing sharp features and extreme temperature gradients, particularly for 3D-IC applications with adjacent hotspots.",
                
                "Recent advances in network architecture design, particularly the emergence of Kolmogorov-Arnold Networks and other learnable activation approaches, offer new opportunities to address these challenges. The key innovation is replacing fixed activation functions with learnable univariate functions, enabling better adaptation to sharp features.",
                
                "To date, there has been limited work specifically combining KANs with physics-informed training for thermal problems in 3D-ICs, representing the gap that this research aims to address.",
            ]
        }
    ]

def create_expanded_full_thesis(source_path, output_path):
    """Main function to create significantly expanded thesis"""
    
    print("=" * 70)
    print("CREATING EXPANDED THESIS WITH LONGER INTRO AND LIT REVIEW")
    print("Target: ~100 pages")
    print("=" * 70)
    print("")
    
    # Load source document
    doc = Document(source_path)
    
    print(f"Source document loaded: {os.path.basename(source_path)}")
    print(f"Original paragraphs: {len(doc.paragraphs)}")
    print(f"Original tables: {len(doc.tables)}")
    print("")
    
    # Find Introduction section
    intro_idx = None
    for i, para in enumerate(doc.paragraphs):
        text_upper = para.text.upper().strip()
        if "INTRODUCTION" in text_upper and len(text_upper) < 50:
            intro_idx = i
            print(f"Found Introduction at paragraph {i}")
            break
    
    # Find Literature Review section
    lit_review_idx = None
    for i, para in enumerate(doc.paragraphs):
        text_upper = para.text.upper().strip()
        if ("LITERATURE" in text_upper or "REVIEW" in text_upper) and len(text_upper) < 100:
            lit_review_idx = i
            print(f"Found Literature Review at paragraph {i}")
            break
    
    # Expand Introduction
    if intro_idx is not None:
        print("")
        print("Expanding Introduction section...")
        intro_expansion = get_introduction_expansion()
        intro_inserted = insert_paragraphs_after_index(doc, intro_idx + 1, intro_expansion)
        print(f"  Added {intro_inserted} paragraphs to Introduction")
        # Adjust literature review index
        if lit_review_idx is not None:
            lit_review_idx += intro_inserted
    
    # Expand Literature Review
    if lit_review_idx is not None:
        print("")
        print("Expanding Literature Review section...")
        lit_review_expansion = get_literature_review_expansion()
        lit_inserted = insert_paragraphs_after_index(doc, lit_review_idx + 1, lit_review_expansion)
        print(f"  Added {lit_inserted} paragraphs to Literature Review")
    
    # Save expanded document
    doc.save(output_path)
    
    print("")
    print(f"Expanded thesis saved: {os.path.basename(output_path)}")
    print(f"New paragraph count: {len(doc.paragraphs)}")
    print("")
    
    # Estimate page count
    all_text = " ".join([p.text for p in doc.paragraphs])
    word_count = len(all_text.split())
    # Rough estimate: ~300-350 words per page for 12pt Times New Roman, 1.5 spacing
    estimated_pages = int(word_count / 330)
    
    print("=" * 70)
    print("EXPANSION COMPLETE")
    print("=" * 70)
    print(f"Estimated word count: {word_count:,} words")
    print(f"Estimated page count: ~{estimated_pages} pages")
    print(f"Target: ~100 pages")
    print("")
    if estimated_pages >= 80:
        print("SUCCESS: Document is now significantly expanded!")
    else:
        print("Note: Document may need additional expansion to reach 100 pages")

def main():
    base_dir = r"C:\Users\PidotKing\Downloads\Research\RND2"
    source_path = os.path.join(base_dir, "Final_Report_FORMATTED.docx")
    output_path = os.path.join(base_dir, "Final_Report_EXPANDED_100pages.docx")
    
    if not os.path.exists(source_path):
        print(f"ERROR: Source file not found: {source_path}")
        return
    
    create_expanded_full_thesis(source_path, output_path)

if __name__ == "__main__":
    main()
