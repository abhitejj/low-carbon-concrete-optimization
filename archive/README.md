# Supporting project archive

This archive preserves original data, exploratory analysis, supporting notes, and
presentation materials from the former `revision` folder. Use the repository's
main `paper/`, `scripts/`, `data/`, and `results/` folders for the final manuscript
and current analysis. Archived calculations and claims can differ from the final
paper; they are retained for provenance, not as replacements for final results.

| Folder | Contents |
| --- | --- |
| `data/` | Original experimental Excel workbook, including the source mix and carbonation measurements. Source attribution is in the main repository README. |
| `analysis/` | Three distinct analysis notebooks, original preprocessing and inspection scripts, historical optimization and verification scripts, intermediate CSV files, and the editable long-form workbook. |
| `notes/` | Methods, audit, evidence, external review, and project context notes. These documents describe earlier stages of the work. |
| `presentation/` | The retained presentation PDF, historical slide-building script, and carbonation mechanism diagram. |

## Using historical analysis

The archived files are preserved unchanged. Some scripts and notebooks refer to
old absolute paths under `MESS/Project`; update those paths before running them.
Do not run archived scripts in the main repository folders: they can overwrite
outputs and reflect earlier assumptions. Use a separate working copy.

`carbonation_master.csv` is retained once at `../data/carbonation_master.csv`,
and the final scenario summary is at
`../results/summary_best_candidates_9cases.csv`. Paths here are relative to this
README. The notebooks originally expected these files alongside the notebook or
in the old project directory. The archived intermediate data remain in
`analysis/`.

The presentation builder expects its diagram and figure images in its working
directory, and requires `python-pptx`. Its figure inputs are retained in the main
`figures/` folder. It produces a historical slide deck, not a verified editable
copy of every correction in the retained presentation PDF.

Obsolete manuscript exports, duplicate upload ZIP files, page renders, editing
checkpoints, caches, and notebook-generation utilities are intentionally excluded.
