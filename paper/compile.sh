#!/usr/bin/env bash
set -e

echo "=== Compiling IEEE manuscript in paper/ ==="
pdflatex -interaction=nonstopmode main_ieee.tex
bibtex main_ieee
pdflatex -interaction=nonstopmode main_ieee.tex
pdflatex -interaction=nonstopmode main_ieee.tex

echo "=== Verifying Build ==="
PAGES=$(python3 -c "import pypdf; print(len(pypdf.PdfReader('main_ieee.pdf').pages))")
echo "Page count: $PAGES pages (Budget: 10 pages)"

if [ "$PAGES" -ne 10 ]; then
  echo "WARNING: Page count is $PAGES, expected 10."
else
  echo "PASS: Exactly 10 pages."
fi

cp main_ieee.pdf final_main_ieee.pdf
echo "Compilation complete: final_main_ieee.pdf updated."
