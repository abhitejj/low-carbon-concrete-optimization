# Low-Carbon Concrete Optimization

Lifecycle optimization framework for structural concrete mix design, balancing carbon reduction, compressive strength requirements, and long-term natural carbonation resistance.

Developed for the course **Modeling of Earth System and Sustainability (MESS)**, Department of Civil Engineering.

---

## Repository Structure

```text
low-carbon-concrete-optimization/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   └── carbonation_master.csv
├── figures/
│   ├── fig1_carbonation_kinetics_by_condition.png
│   ├── fig2_fly_ash_tradeoff_isoparametric.png
│   ├── fig3_optimization_tradeoff_landscape.png
│   ├── fig4_strength_verification_abrams_air.png
│   ├── fig5_sheltered_vs_unsheltered_divergence.png
│   ├── fig6_pareto_carbon_vs_strength.png
│   └── fig7_sensitivity_analysis.png
├── paper/
│   ├── compile.sh
│   ├── final_main_ieee.pdf
│   ├── IEEEtran.cls
│   ├── main_ieee.bbl
│   ├── main_ieee.tex
│   └── references.bib
├── results/
│   ├── continuous_optimization_results.csv
│   ├── discrete_screening_results.csv
│   ├── lifecycle_carbon_mix_catalog.csv
│   ├── sensitivity_matrix_results.csv
│   └── summary_best_candidates_9cases.csv
└── scripts/
    ├── run_constrained_optimization.py
    └── verify_all_numbers.py
```

---

## Directory Overview

* **`data/`**: Master dataset (`carbonation_master.csv`) containing mixture proportions, compressive strengths, air void contents, and natural carbonation depth measurements over 11 years.
* **`scripts/`**:
  * `run_constrained_optimization.py`: Fits Bolomey strength and carbonation kinetics models, executes discrete mix screening, performs continuous multi-start SLSQP optimization, and generates publication figures.
  * `verify_all_numbers.py`: Automated verification suite checking mathematical invariants, bounds, and sensitivity metrics.
* **`results/`**: Tabular CSV outputs from discrete screening, continuous optimization runs, sensitivity sweeps, and candidate mix summaries.
* **`figures/`**: High-resolution PNG plots depicting kinetics, strength normalization, Pareto frontiers, and sensitivity sweeps.
* **`paper/`**: Complete LaTeX source (`main_ieee.tex`), bibliography (`references.bib`), IEEE style class, automated compilation script (`compile.sh`), and compiled PDF (`final_main_ieee.pdf`).

---

## Quickstart

### 1. Installation

Python 3.10 or later is recommended.

```bash
# Clone the repository
git clone https://github.com/abhitejj/low-carbon-concrete-optimization.git
cd low-carbon-concrete-optimization

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Optimization Analysis

To run the complete modeling and optimization pipeline:

```bash
python scripts/run_constrained_optimization.py
```

This reads `data/carbonation_master.csv`, updates the result CSVs in `results/`, and refreshes Figures 6 and 7 in `figures/`.

### 3. Verify Calculations

To run the automated numerical check:

```bash
python scripts/verify_all_numbers.py
```

### 4. Compile Paper

To rebuild the manuscript PDF from LaTeX source:

```bash
cd paper
chmod +x compile.sh
./compile.sh
```

---

## Data Attribution & Notes

* The empirical carbonation dataset is attributed to Hule et al. (2024), Mendeley Data, DOI: [10.17632/gkcf2z4ts5.1](https://doi.org/10.17632/gkcf2z4ts5.1).
* See the manuscript in `paper/final_main_ieee.pdf` for complete discussion of modeling assumptions, design code limits, and safety buffers.
