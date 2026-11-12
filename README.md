# Low-carbon concrete optimization

Research project by Abhitej Singh Bhullar for Modeling of Earth System and Sustainability (MESS).

## Paper

Read [the final IEEE manuscript](final_main_ieee.pdf). The editable source is `main_ieee.tex`; figures, bibliography, and IEEE class are included.

Compile with pdfLaTeX, BibTeX, and two further pdfLaTeX passes.

## Analysis

`run_constrained_optimization.py` fits models and performs constrained optimization using `carbonation_master.csv`. Install dependencies from `requirements.txt`, then run `python run_constrained_optimization.py`. Running it overwrites generated result tables and Figures 6–7. The CSV files included here are the saved analysis outputs accompanying the manuscript; reproduction has not been independently rerun for this release.

The underlying experimental dataset is attributed to Hule et al. (2024), Mendeley Data, DOI: [10.17632/gkcf2z4ts5.1](https://doi.org/10.17632/gkcf2z4ts5.1). Consult that source for original data and reuse terms. The master CSV is the processed analysis input.

Model predictions and extrapolations are subject to the limitations stated in the paper. AI assistance is disclosed in the manuscript.
