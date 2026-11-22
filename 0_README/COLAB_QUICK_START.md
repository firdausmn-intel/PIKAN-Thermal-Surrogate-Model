# Google Colab Quick Start Guide

**Copy-paste these commands into Google Colab cells to get started immediately.**

---

## 🚀 Setup (Run These First)

### Cell 1: Mount Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
print("✓ Drive mounted!")
```

### Cell 2: Navigate to Package & Check Structure
```python
import os
os.chdir('/content/drive/My Drive/COLAB_PACKAGE')
!ls -la
print("\n✓ Current directory: " + os.getcwd())
```

### Cell 3: Install Dependencies
```bash
!pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
!pip install -q numpy scipy matplotlib scikit-learn pandas seaborn
!pip install -q jupyter ipython tqdm
print("✓ All dependencies installed!")
```

### Cell 4: Verify Setup
```python
import torch
import numpy as np
import pandas as pd
print(f"✓ PyTorch version: {torch.__version__}")
print(f"✓ NumPy version: {np.__version__}")
print(f"✓ CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
```

---

## 🔬 Running Experiments

### Cell 5: Run Phase 2 (Single-Hotspot Benchmark) - Most Important
```python
import os
os.chdir('/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase2')

# Check what scripts are available
!ls -la

# Generate HotSpot ground truth
print("Step 1: Generating HotSpot ground truth...")
!python generate_data.py --config config.json

# Train PINO
print("\nStep 2: Training PINO (MLP-based)...")
!python train_model.py --model pino --seeds 1 2 3

# Train PIKAN  
print("\nStep 3: Training PIKAN (KAN-based)...")
!python train_model.py --model pikan --seeds 1 2 3

# Evaluate
print("\nStep 4: Evaluating results...")
!python evaluate.py --compare pino pikan
```

### Cell 6: Run Phase 3D (Two-Tier Stack - Physics-Informed)
```python
import os
os.chdir('/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase3d_v2')

# Generate data
print("Generating Phase 3D data...")
!python generate_data.py --config config.json

# Train with physics loss
print("Training with physics-informed loss...")
!python train_model.py --model pikan --lambda_physics 1.0 --seeds 1 2 3

# Evaluate
print("Evaluating physics-informed training...")
!python evaluate.py
```

### Cell 7: Compare All Results
```python
import os
import json
import pandas as pd

results_summary = []

for phase in ['phase2', 'phase3d', 'phase3d_v2']:
    phase_dir = f'/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/{phase}'
    results_file = os.path.join(phase_dir, 'results/metrics.json')
    
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            metrics = json.load(f)
        
        results_summary.append({
            'Phase': phase,
            'PINO Peak Error': metrics.get('pino_peak_error'),
            'PIKAN Peak Error': metrics.get('pikan_peak_error'),
            'Improvement %': metrics.get('improvement_percent'),
        })

df = pd.DataFrame(results_summary)
print(df.to_string())
```

---

## 📊 Visualization

### Cell 8: Plot Results
```python
import matplotlib.pyplot as plt
import numpy as np

# Example: Plot single-hotspot benchmark results
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Peak Error Comparison
models = ['PINO', 'PIKAN']
errors = [0.797, 0.514]  # From Phase 2
axes[0].bar(models, errors, color=['#FF6B6B', '#4ECDC4'])
axes[0].set_ylabel('Peak Error (K)')
axes[0].set_title('Single-Hotspot Benchmark: Peak Temperature Error')
axes[0].set_ylim([0, 1])

# Improvement
improvement = ((0.797 - 0.514) / 0.797) * 100
axes[1].text(0.5, 0.5, f'{improvement:.1f}%\nImprovement', 
             ha='center', va='center', fontsize=24, weight='bold',
             transform=axes[1].transAxes)
axes[1].set_title('PIKAN vs PINO')
axes[1].axis('off')

plt.tight_layout()
plt.savefig('/content/drive/My Drive/COLAB_PACKAGE/results_benchmark.png', dpi=150)
plt.show()
print("✓ Plot saved!")
```

---

## 🔧 Customization

### Cell 9: Modify Configuration
```python
import json
import os

# Edit Phase 2 config
config_path = '/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase2/config.json'

with open(config_path, 'r') as f:
    config = json.load(f)

# Customize
config['epochs'] = 1000  # Increase training
config['lambda_physics'] = 0.5  # Adjust physics loss weight
config['learning_rate'] = 0.0005  # Lower learning rate
config['seeds'] = [1, 2, 3, 4, 5, 6, 7, 8]  # Use all 8 seeds

# Save back
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Config updated!")
print(json.dumps(config, indent=2))
```

### Cell 10: Check Available Models
```python
# List all model files
import os
model_dir = '/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/scripts'

print("Available models:")
for f in os.listdir(model_dir):
    if f.endswith('.py'):
        print(f"  - {f}")

# Check loss functions
print("\nAvailable loss functions:")
!grep -n "def " {model_dir}/losses.py | head -20
```

---

## 📥 Download Results

### Cell 11: Save Results to Drive
```python
import shutil
import os
from datetime import datetime

# Create timestamped results folder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
results_dir = f'/content/drive/My Drive/COLAB_RESULTS_{timestamp}'
os.makedirs(results_dir, exist_ok=True)

# Copy all results
source_dirs = [
    '/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase2/results',
    '/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase3d_v2/results'
]

for source in source_dirs:
    if os.path.exists(source):
        dest = os.path.join(results_dir, os.path.basename(source))
        shutil.copytree(source, dest)

print(f"✓ Results saved to: {results_dir}")
print(f"✓ Files saved:")
!ls -lh {results_dir}/
```

### Cell 12: Download to Local Computer
```python
# Create a zip file of results
import shutil
import os

results_zip = '/content/drive/My Drive/COLAB_RESULTS.zip'
source_dir = '/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/results'

if os.path.exists(source_dir):
    shutil.make_archive(results_zip.replace('.zip', ''), 'zip', source_dir)
    print(f"✓ Created: {results_zip}")
else:
    print("No results directory found")

# List recent files
!ls -lh /content/drive/My\ Drive/COLAB_RESULTS*
```

---

## 🐛 Troubleshooting

### Issue: "No such file or directory"
```python
# Check exact path
import os
path = '/content/drive/My Drive/COLAB_PACKAGE'
print(f"Exists: {os.path.exists(path)}")
print(f"Contents: {os.listdir(path)}")
```

### Issue: "Permission denied"
```python
# Fix permissions
!chmod -R 755 /content/drive/My\ Drive/COLAB_PACKAGE
!chmod -R 755 /content/drive/My\ Drive/COLAB_PACKAGE/2_HOTSPOT_CODE
```

### Issue: "CUDA out of memory"
```python
import torch
torch.cuda.empty_cache()

# Or switch to CPU in config:
# Edit config.json and change "device": "cuda" to "device": "cpu"
```

---

## ⏱️ Typical Runtimes

| Phase | Task | Time (CPU) | Time (GPU) |
|-------|------|-----------|-----------|
| Phase 1 | Generate HotSpot data | 5-10 min | N/A |
| Phase 2 | Train PINO (8 seeds) | 30-45 min | 10-15 min |
| Phase 2 | Train PIKAN (8 seeds) | 30-45 min | 10-15 min |
| Phase 2 | Evaluate & compare | 5-10 min | 2-5 min |
| Phase 3D-v2 | Train with physics loss | 60-90 min | 15-25 min |

**Total Full Experiment:** ~3-4 hours (GPU) or ~6-8 hours (CPU)

---

## 💾 Pro Tips

1. **Save frequently:** Colab sessions disconnect. Save results to Drive often.
2. **Use GPU:** Colab free tier gives GPU. Toggle in Runtime > Change runtime type.
3. **Monitor memory:** Add `!nvidia-smi` cell to watch GPU usage.
4. **Checkpoint:** Save model weights during training in case of disconnect.

---

## 📝 Example: Full Experiment in One Colab Notebook

```python
# ==== COMPLETE WORKFLOW ====

# 1. Setup
from google.colab import drive
drive.mount('/content/drive')
!pip install -q torch numpy scipy matplotlib scikit-learn

import os
os.chdir('/content/drive/My Drive/COLAB_PACKAGE/2_HOTSPOT_CODE/phase2')

# 2. Generate data
!python generate_data.py

# 3. Train models
!python train_model.py --model pino --seeds 1 2 3 4 5 6 7 8
!python train_model.py --model pikan --seeds 1 2 3 4 5 6 7 8

# 4. Evaluate
!python evaluate.py --compare pino pikan

# 5. Save results
import shutil
shutil.copytree('results', '/content/drive/My Drive/Phase2_Results')
print("✓ All done! Results saved to Drive.")
```

---

**Ready? Start with Cell 1 above! 🚀**
