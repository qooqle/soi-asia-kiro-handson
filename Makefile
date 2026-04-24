# Internet Adoption Analysis — Pipeline Makefile
# Usage: make all
# Requires Python 3.10+ and dependencies from requirements.txt

PYTHON := python
SRC    := src

.PHONY: all acquire clean-data visualize cluster annotate report test clean-outputs help

## all: Run the full pipeline end-to-end
all: acquire clean-data visualize cluster annotate report

## acquire: Download raw data from World Bank and ITU
acquire:
	@echo "==> [1/6] Acquiring data from World Bank and ITU..."
	$(PYTHON) $(SRC)/acquire_worldbank.py
	$(PYTHON) $(SRC)/acquire_itu.py

## clean-data: Merge, interpolate, and write the panel dataset
clean-data: acquire
	@echo "==> [2/6] Cleaning data and building panel dataset..."
	$(PYTHON) $(SRC)/clean.py

## visualize: Generate GDP scatter plot and per-country trend lines
visualize: clean-data
	@echo "==> [3/6] Generating visualizations..."
	$(PYTHON) $(SRC)/viz_gdp.py
	$(PYTHON) $(SRC)/viz_trends.py

## cluster: Run k-means clustering and produce PCA plot + summary CSVs
cluster: clean-data
	@echo "==> [4/6] Running clustering analysis..."
	$(PYTHON) $(SRC)/cluster.py

## annotate: Generate annotated regional timeline
annotate: clean-data
	@echo "==> [5/6] Generating annotated timeline..."
	$(PYTHON) $(SRC)/annotate_timeline.py

## report: Generate policy summary and print output file list
report: visualize cluster annotate
	@echo "==> [6/6] Generating policy summary report..."
	$(PYTHON) $(SRC)/report.py
	@echo ""
	@echo "==> Pipeline complete. Output files:"
	@for f in outputs/gdp_vs_internet.png outputs/country_trends.png \
	           outputs/cluster_pca.png outputs/annotated_timeline.png \
	           outputs/policy_summary.md; do \
	    if [ -f "$$f" ]; then \
	        size=$$(du -k "$$f" | cut -f1); \
	        echo "    $$f  ($${size} KB)"; \
	    else \
	        echo "    $$f  (MISSING)"; \
	    fi; \
	done

## test: Run the full test suite
test:
	@echo "==> Running tests..."
	$(PYTHON) -m pytest tests/ -q --tb=short

## clean-outputs: Remove generated outputs and processed data (keeps raw data)
clean-outputs:
	@echo "==> Removing outputs/ and data/processed/..."
	rm -rf outputs/* data/processed/*
	@echo "    Done."

## help: Show available targets
help:
	@echo "Available targets:"
	@grep -E '^## ' Makefile | sed 's/## /  /'
