# PIKAN Thesis - Google Colab Package

**Author:** Muhammad Firdaus Bin Mohd Noor  
**Title:** Overcoming Spectral Bias in 3D-IC Thermal Simulation: Modeling Extreme Temperature Gradients Using Physics-Informed Kolmogorov-Arnold Networks (PIKAN)  
**Institution:** Universiti Teknologi PETRONAS  
**Date:** November 2026

---

## 📋 Package Contents

This folder contains all code, documents, and data for the PIKAN research project, organized for Google Colab.

### Directory Structure

```
COLAB_PACKAGE/
├── 0_README/                          # This file & setup instructions
├── 1_THESIS_DOCUMENTS/                # Final thesis & related documents
├── 2_HOTSPOT_CODE/                    # HotSpot simulation & phase code
├── 3_PYTHON_SCRIPTS/                  # Standalone Python utilities
├── 4_DATA/                            # Datasets (if any)
├── 5_REFERENCES/                      # Bibliography & citations
└── 6_GUIDELINES/                      # UTP guidelines & requirements
```

---

## 🚀 Quick Start for Google Colab

### Step 1: Upload to Colab

```python
# In Colab cell, mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Upload the COLAB_PACKAGE folder to your Drive, then:
import os
os.chdir('/content/drive/My Drive/COLAB_PACKAGE')
```

### Step 2: Install Dependencies

```bash
!pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
!pip install numpy scipy matplotlib scikit-learn pandas
!pip install jupyter ipython
```

### Step 3: Run Phase Scripts

```python
# Example: Run Phase 2 (Single-hotspot benchmark)
os.chdir('/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase2')
exec(open('train_phase2.py').read())
```

---

## 📁 Detailed Folder Description

### 1_THESIS_DOCUMENTS/
- **Final_report_draft.docx** - Latest thesis draft (working version)
- **Final_Report_FORMATTED.docx** - Formatted according to UTP guidelines
- **FINAL_CONCLUSION.docx** - Conclusion chapter (ready to integrate)
- **Literature_Review_*.docx** - Literature review additions & enhancements
- **Progress_Report_word_resubmit_v2.docx** - Progress report snapshot

**Use:** Reference for thesis structure and content.

### 2_HOTSPOT_CODE/
Complete experimental pipeline organized by phase:

```
2_HOTSPOT_CODE/
├── phase1/        # Physical model extraction (SKY130 8-cell block)
├── phase2/        # Single-hotspot benchmark (PINO vs PIKAN)
├── phase3d/       # Two-tier synthetic stack (data-only training)
├── phase3d_v2/    # Physics-informed loss experiments
└── scripts/       # Utilities (HotSpot wrapping, data processing)
```

**Key files in each phase:**
- `generate_data.py` - Create HotSpot ground truth
- `train_model.py` - Train PINO/PIKAN models
- `evaluate.py` - Benchmark against HotSpot
- `config.json` - Hyperparameters and settings

**Usage:**
```python
# Navigate to a phase folder and run:
!python generate_data.py
!python train_model.py --model pikan --seeds 8
!python evaluate.py --compare
```

### 3_PYTHON_SCRIPTS/
Standalone utilities for document generation and processing:

- `generate_thesis_docx.py` - Build thesis from components
- `format_exact_report.py` - Apply UTP formatting
- `add_conclusion_appendices.py` - Append sections
- `create_expanded_comprehensive.py` - Expand content
- ... and others

**These are helper scripts** - most are for development. For Colab, focus on phase code.

### 4_DATA/
Data files and datasets:
- `s.xlsx` - Spreadsheet with results/metrics
- Any `.csv` or `.json` files with training data

### 5_REFERENCES/
Reserved for bibliography and reference management files.

### 6_GUIDELINES/
- `Master Engineering Project Guidelines 2023 (Structure B) 2.pdf` - UTP requirements
- `R&D 2.pdf` - Research domain guidelines

---

## 🔬 Experiment Overview

### Phase 1: Physical Model
- Extract SKY130 8-cell inverter block geometry
- Define thermal domain and boundary conditions
- Generate HotSpot thermal RC network

### Phase 2: Single-Hotspot Benchmark
- Create 10 single-hotspot test cases
- Train PINO (MLP-based) and PIKAN (KAN-based) operators
- Compare peak error: PIKAN shows 35.5% lower error than PINO

### Phase 3D-v1: Two-Tier Stack (Data-Only)
- Synthetic controlled two-tier structure
- Train operators with data loss only
- Result: Training data coverage matters more than model choice

### Phase 3D-v2: Physics-Informed Training
- Same two-tier stack
- Add physics loss term (heat diffusion PDE residual)
- Result: Physics loss helps KAN (~5% improvement) but not MLP

---

## 📊 Key Results

| Metric | PINO (MLP) | PIKAN (KAN) | Improvement |
|--------|-----------|------------|-------------|
| Peak Error (Single Hotspot) | 0.797 K | 0.514 K | **35.5% ↓** |
| Inference Speed | ~5 ms | ~2-5 ms | **100-170x vs HotSpot** |
| Out-of-Distribution (60 mW) | 0.3 K | 0.25 K | **~5% ↓** (with physics loss) |
| Generalization | Medium | Medium-High | **Conditional** |

---

## 🛠️ Common Colab Workflows

### Workflow 1: Run all phases
```python
phases = ['phase1', 'phase2', 'phase3d', 'phase3d_v2']
for phase in phases:
    os.chdir(f'/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/{phase}')
    print(f"\n=== Running {phase} ===")
    os.system('python train_model.py --model pikan')
```

### Workflow 2: Compare PINO vs PIKAN
```python
os.chdir('/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase2')
os.system('python train_model.py --model pino --seeds 8')
os.system('python train_model.py --model pikan --seeds 8')
os.system('python evaluate.py --compare pino pikan')
```

### Workflow 3: Extract results to notebook
```python
import json
with open('/path/to/results/metrics.json', 'r') as f:
    results = json.load(f)
print(results)
```

---

## 📝 Configuration Files

Each phase has a `config.json`:

```json
{
  "model": "pikan",
  "architecture": "fno",
  "modes": 12,
  "hidden_dim": 64,
  "learning_rate": 0.001,
  "epochs": 500,
  "lambda_physics": 1.0,
  "seeds": [1, 2, 3, 4, 5, 6, 7, 8]
}
```

**Edit these to:**
- Change model (pino vs pikan)
- Adjust hyperparameters
- Run with different random seeds

---

## 🔗 Important Files to Check First

1. **Phase 2 training:** `2_HOTSPOT_CODE/phase2/train_model.py`
2. **Evaluation script:** `2_HOTSPOT_CODE/phase2/evaluate.py`
3. **Loss functions:** `2_HOTSPOT_CODE/scripts/losses.py`
4. **Model definitions:** `2_HOTSPOT_CODE/scripts/models.py`
5. **Latest thesis:** `1_THESIS_DOCUMENTS/Final_report_draft.docx`

---

## ⚠️ Known Issues & Workarounds

### Issue: HotSpot not installed
**Solution:** HotSpot code is included. Use the Python wrapper instead of calling binary directly.

### Issue: CUDA out of memory
**Solution:** Reduce `batch_size` in config.json or switch to CPU mode.

### Issue: PyTorch version conflicts
**Solution:** Use `!pip install torch --upgrade` to get latest compatible version for Colab.

---

## 📚 References

- [1] Kolmogorov-Arnold Networks (Liu et al., 2024)
- [2] Fourier Neural Operators (Li et al., 2021)
- [3] Physics-Informed Neural Networks (Raissi et al., 2019)
- [4] Spectral Bias in Neural Networks (Rahaman et al., 2019)
- [23] DeepONet (Lu et al., 2019)

See `6_GUIDELINES/` for full bibliography.

---

## 👤 Contact & Questions

**Author:** Muhammad Firdaus  
**Supervisor:** Dr. Eric Ho  
**Institution:** Universiti Teknologi PETRONAS  
**Email:** (Add your email)

---

## 📄 License & Usage

This code and documentation are for academic research purposes at Universiti Teknologi PETRONAS. 

**When using this in Colab:**
1. Create your own copy of the Drive folder (don't modify original)
2. Document any modifications you make
3. Keep backup of results

---

## ✅ Checklist for Colab Setup

- [ ] Upload COLAB_PACKAGE to Google Drive
- [ ] Mount Drive in Colab
- [ ] Install PyTorch and dependencies
- [ ] Test one phase script (e.g., `phase2/train_model.py`)
- [ ] Verify HotSpot ground truth generation works
- [ ] Run evaluation script to see results
- [ ] Save outputs to Drive before Colab session ends

---

**Last Updated:** November 22, 2026  
**Status:** Ready for Colab Deployment
