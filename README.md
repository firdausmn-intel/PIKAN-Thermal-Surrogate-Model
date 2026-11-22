# PIKAN-Thermal-Surrogate-Model
Physics-Informed KANs for Ultra-Fast 3D-IC Thermal Prediction

A neural surrogate model framework combining Kolmogorov-Arnold Networks (KANs) 
with physics-informed loss to predict thermal hotspots in 3D integrated circuits. 
Achieves 170x speedup over HotSpot simulations while maintaining accuracy within 
0.25% of ground truth.

## Key Features
- **PIKAN vs PINO:** Learnable spline-based KANs outperform fixed-activation MLPs 
  on sharp thermal gradients and extrapolation scenarios
- **Multi-Phase Pipeline:** Single-hotspot benchmark → 2-tier stack validation → 
  full 3D physics-informed training
- **High Spatial Resolution:** Accurately predicts closely-spaced hotspots (1.4μm pitch)
- **Energy Efficient:** 2000x lower energy per prediction than CPU simulators
- **Reproducible:** 8-seed experiments with stratified cross-validation

## Results
| Metric | PINO | PIKAN | Improvement |
|--------|------|-------|-------------|
| Peak Error | 0.797 K | 0.514 K | 35.5% ↓ |
| Inference Speed | 2.5s | 2.3ms | 170x ↑ |

## Project Structure
- **2_HOTSPOT_CODE:** Phase 1-3D training pipelines
- **3_PYTHON_SCRIPTS:** Model implementations and utilities
- **4_DATA:** Training datasets and ground truth
- **5_REFERENCES:** Related papers and citations
- **0_README:** Quick-start guides for Colab and local setup

## Quick Start
```bash
# Local
git clone https://github.com/YOUR_USERNAME/PIKAN-Thermal-Surrogate-Model.git
cd PIKAN-Thermal-Surrogate-Model
pip install -r 3_PYTHON_SCRIPTS/requirements.txt
cd 2_HOTSPOT_CODE/phase2 && python train_model.py --model pikan
