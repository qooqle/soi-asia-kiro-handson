# Implementation Plan: Internet Adoption Analysis

## Overview

Build a reproducible, batch-oriented Python pipeline that ingests World Bank and ITU data,
constructs a tidy country-year panel, and produces charts, cluster assignments, and a
plain-language policy summary. The pipeline is driven by `make` and configured through two
YAML files. Each task below is scoped to produce a single reviewable output (file, chart, or
printed summary) and should complete in under 10 minutes.

---

## Tasks

### Phase 1 — Project Scaffolding

- [x] 1. Create the top-level directory layout
  - Create directories: `config/`, `data/raw/`, `data/processed/`, `outputs/`, `src/utils/`, `tests/`
  - Add `.gitkeep` files to empty leaf directories so they are tracked by git
  - _Requirements: 10.1, 10.3_

- [x] 2. Write `requirements.txt` with pinned dependencies
  - Pin: `requests`, `tenacity`, `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`,
    `scipy`, `pyyaml`, `textstat`, `hypothesis`, `pytest`, `pycountry`
  - Include a comment block at the top stating the minimum Python version (3.10)
  - **Reviewable output:** `requirements.txt` printed to stdout
  - _Requirements: 10.1, 10.3_

- [x] 3. Write `environment.yml` for conda users
  - Mirror the same pinned versions from `requirements.txt` under `dependencies:`
  - Set `name: internet-adoption-analysis`
  - **Reviewable output:** `environment.yml` printed to stdout
  - _Requirements: 10.1_

- [x] 4. Write `config/countries.yaml` with 35 country entries
  - Use the sub-region grouping from the design (East Asia, Southeast Asia, South Asia,
    Oceania, Pacific Rim Americas) — exactly 35 unique ISO3 codes, no duplicates
  - **Reviewable output:** `config/countries.yaml` printed to stdout; confirm entry count = 35
  - _Requirements: 3.1, 3.2, 3.4_

- [x] 5. Write `config/key_events.yaml` with the five required events
  - Include: Jio commercial launch (2016-09), Palapa Ring completion (2019), Coral Sea Cable
    activation (2019), COVID-19 pandemic onset (2020), Starlink Asia-Pacific expansion (2022)
  - **Reviewable output:** `config/key_events.yaml` printed to stdout
  - _Requirements: 8.2, 8.3_

- [x] 6. Write `src/utils/config_loader.py`
  - Implement `load_countries(path)` — flattens sub-regions, validates ISO3 codes via
    `pycountry`, raises `ConfigError` if count < 30 or > 40 or any code is invalid
  - Implement `load_key_events(path)` — returns list of `{name, year, month?}` dicts
  - **Reviewable output:** run `python -c "from src.utils.config_loader import load_countries; print(load_countries())"` and confirm 35 entries printed
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 6.1 Write property test for `load_countries` — Property 5: Country Count Validation
    - **Property 5:** For any `countries.yaml`, accept iff 30–40 valid ISO3 entries; raise
      `ConfigError` otherwise
    - **Validates: Requirements 3.2, 3.3, 3.4**
    - Use `hypothesis` with `st.lists(iso3_codes, min_size=0, max_size=50)`
    - Tag: `# Feature: internet-adoption-analysis, Property 5: Country Count Validation`

- [x] 7. Write `src/utils/http_client.py`
  - Implement `get_with_retry(url, params, timeout=30, max_attempts=3)` using `tenacity`
  - Retry on HTTP 5xx and connection timeouts with back-off delays of 1 s, 2 s, 4 s
  - Do not retry on HTTP 4xx; log error and return immediately
  - **Reviewable output:** run the module's `__main__` block against a known-good URL and print status code
  - _Requirements: 1.3_

  - [ ]* 7.1 Write property test for `get_with_retry` — Property 3: Retry Behaviour Under Failure
    - **Property 3:** For N consecutive failures (N ∈ {1..5}), client makes exactly min(N, 3)
      retry attempts and logs failure when N ≥ 3
    - **Validates: Requirements 1.3**
    - Use `hypothesis` with `st.integers(min_value=1, max_value=5)` and a mock HTTP adapter
    - Tag: `# Feature: internet-adoption-analysis, Property 3: Retry Behaviour Under Failure`

- [x] 8. Write `Makefile` with phony targets
  - Targets: `all`, `acquire`, `clean` (data cleaning step), `visualize`, `cluster`,
    `annotate`, `report`, `test`, `clean-outputs` (removes `outputs/` and `data/processed/`)
  - `all` depends on `acquire → clean → visualize cluster annotate → report`
  - Each target prints a one-line status message before invoking its script
  - **Reviewable output:** run `make --dry-run all` and confirm the dependency chain is printed correctly
  - _Requirements: 10.2_

- [x] 9. Checkpoint — scaffolding complete
  - Run `python -m pytest tests/ -q --tb=short` (tests directory may be empty; confirm no import errors)
  - Confirm all directories exist and config files load without errors
  - Ensure all tests pass; ask the user if questions arise before proceeding to Phase 2

---

### Phase 2 — Data Acquisition

- [x] 10. Write `src/acquire_worldbank.py` — indicator loop and file saving
  - Load country list via `config_loader`; map ISO3 → ISO2 using `pycountry`
  - For each of the five WB indicator codes, call the REST API v2 endpoint for all countries
    in a single paginated request (`per_page=500`); save raw JSON to `data/raw/wb_{indicator}.json`
  - Log success/failure counts to stdout at the end
  - **Reviewable output:** `data/raw/wb_NY.GDP.PCAP.KD.json` exists and its first record is printed
  - _Requirements: 1.1, 1.2, 1.4_

  - [ ]* 10.1 Write property test for acquisition completeness — Property 1
    - **Property 1:** For any valid country list (30–40 entries) and mocked HTTP responses,
      saved raw files contain at least one record per (iso3, year) in scope
    - **Validates: Requirements 1.1, 2.1**
    - Use `hypothesis` with `st.lists(iso3_codes, min_size=30, max_size=40)` and `responses` mock
    - Tag: `# Feature: internet-adoption-analysis, Property 1: Acquisition Completeness`

  - [ ]* 10.2 Write property test for raw data immutability — Property 2
    - **Property 2:** Bytes written to `data/raw/` are identical to bytes received in the HTTP response
    - **Validates: Requirements 1.2, 2.2**
    - Use `hypothesis` with `st.binary()` for response bodies
    - Tag: `# Feature: internet-adoption-analysis, Property 2: Raw Data Immutability`

- [x] 11. Write `src/acquire_itu.py` — ITU download, fallback, and provenance log
  - Download ITU bulk CSV from the configured endpoint; filter to Country_Scope and 2010–present
  - For each (iso3, year) absent from ITU data, fall back to `wb_IT.NET.USER.ZS.json`
  - Write `data/raw/itu_internet_use.csv` and `data/raw/provenance.csv`
  - **Reviewable output:** print first 10 rows of `provenance.csv` to stdout showing `source` column values
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 11.1 Write property test for fallback and provenance completeness — Property 4
    - **Property 4:** For any set of missing (iso3, year) pairs, pipeline uses WB fallback value
      and records exactly one provenance row per substituted entry with correct `source` value
    - **Validates: Requirements 2.3, 2.4**
    - Use `hypothesis` with random sets of missing (iso3, year) pairs
    - Tag: `# Feature: internet-adoption-analysis, Property 4: Fallback and Provenance Completeness`

- [x] 12. Checkpoint — acquisition complete
  - Confirm `data/raw/` contains all expected files (5 WB JSON files, `itu_internet_use.csv`,
    `provenance.csv`)
  - Print file names and sizes in KB to stdout
  - Ensure all tests pass; ask the user if questions arise before proceeding to Phase 3

---

### Phase 3 — Data Cleaning and Panel Construction

- [x] 13. Write `src/utils/quality.py` — data-quality report helpers
  - Implement `print_quality_report(df)` that prints: total row count, interpolated value
    count per country, and null count per indicator column
  - **Reviewable output:** call `print_quality_report` on a small synthetic DataFrame and confirm output format
  - _Requirements: 4.6_

- [x] 14. Write `src/clean.py` — merge, interpolate, and write panel
  - Load all raw files; merge on (iso3, year) into a single DataFrame with the schema from
    the design (`iso3`, `country_name`, `year`, `internet_penetration_pct`, `gdp_per_capita_usd`,
    `population`, `urban_pop_share_pct`, `broadband_per_100`, `internet_pct_interpolated`)
  - Apply linear interpolation for gaps ≤ 3 consecutive missing years; set
    `internet_pct_interpolated = True` for filled rows; leave longer gaps as null with `False`
  - Deduplicate on (iso3, year); write `data/processed/panel_dataset.csv` (UTF-8)
  - Call `print_quality_report` before exiting
  - **Reviewable output:** `data/processed/panel_dataset.csv` row count and quality report printed to stdout
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 14.1 Write property test for panel schema and uniqueness — Property 6
    - **Property 6:** For any valid raw input files, cleaned panel has exactly the required
      columns and no duplicate (iso3, year) pairs
    - **Validates: Requirements 4.1, 4.2**
    - Use `hypothesis` with random raw DataFrames containing potential duplicates
    - Tag: `# Feature: internet-adoption-analysis, Property 6: Panel Schema and Uniqueness`

  - [ ]* 14.2 Write property test for interpolation correctness — Property 7
    - **Property 7:** Gaps of 1–3 consecutive nulls are filled with linear interpolation
      (`internet_pct_interpolated = True`); gaps ≥ 4 remain null (`internet_pct_interpolated = False`)
    - **Validates: Requirements 4.3, 4.4**
    - Use `hypothesis` with time series containing gaps of random length (1–10)
    - Tag: `# Feature: internet-adoption-analysis, Property 7: Interpolation Correctness`

- [x] 15. Checkpoint — panel construction complete
  - Confirm `data/processed/panel_dataset.csv` exists; print row count, column names, and
    null rate for `internet_penetration_pct` (must be ≤ 10%)
  - Ensure all tests pass; ask the user if questions arise before proceeding to Phase 4

---

### Phase 4 — Visualization and Analysis

- [x] 16. Write `src/viz_gdp.py` — GDP vs. internet penetration scatter plot
  - X-axis: `gdp_per_capita_usd` (log scale); Y-axis: `internet_penetration_pct` (0–100%)
  - Colour each point by country; size proportional to `population`
  - Add OLS regression line with 95% CI band using `seaborn.regplot`
  - Annotate with Pearson r and p-value (computed via `scipy.stats.pearsonr`)
  - Include axis labels, title, legend, and data-source caption
  - Write `outputs/gdp_vs_internet.png` at 150 DPI minimum
  - **Reviewable output:** `outputs/gdp_vs_internet.png` written; print file size in KB
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 17. Write `src/viz_trends.py` — small-multiples per-country trend lines
  - One subplot per country; Y-axis `internet_penetration_pct` 0–100% (consistent across all panels);
    X-axis: year
  - Arrange panels in a grid (e.g., 6 × 6 for 35 countries); label each panel with country name
  - Write `outputs/country_trends.png` at 150 DPI minimum
  - **Reviewable output:** `outputs/country_trends.png` written; print file size in KB
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 18. Write `src/cluster.py` — k-means clustering, PCA plot, and summary CSV
  - Compute per-country feature vector: `penetration_2010`, `penetration_latest`,
    `mean_annual_growth`, `year_crossed_50pct` (impute NaN with sentinel 2030)
  - Standardise with `StandardScaler`; run k-means for k ∈ {4, 5}; select k by silhouette score
  - Print warning to stdout if selected silhouette score < 0.25
  - Run PCA (2 components); produce scatter plot coloured by cluster, annotated with ISO3 codes;
    write `outputs/cluster_pca.png` at 150 DPI minimum
  - Write `data/processed/cluster_assignments.csv` and `outputs/cluster_summary.csv`
  - **Reviewable output:** print selected k, silhouette score, and cluster sizes to stdout;
    confirm both CSV files and PNG exist
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 18.1 Write property test for clustering feature correctness — Property 8
    - **Property 8:** For any country penetration time series, computed features satisfy the
      exact definitions: `penetration_2010` = earliest year ≥ 2010, `penetration_latest` =
      latest non-null year, `mean_annual_growth` = mean of year-on-year differences,
      `year_crossed_50pct` = first year > 50 or NaN
    - **Validates: Requirements 7.1**
    - Use `hypothesis` with random penetration time series
    - Tag: `# Feature: internet-adoption-analysis, Property 8: Clustering Feature Correctness`

  - [ ]* 18.2 Write property test for silhouette-based k selection — Property 9
    - **Property 9:** For any feature matrix where k=4 and k=5 produce different silhouette
      scores, pipeline selects the k with the strictly higher score
    - **Validates: Requirements 7.2, 7.3**
    - Use `hypothesis` with feature matrices of known cluster structure
    - Tag: `# Feature: internet-adoption-analysis, Property 9: Silhouette-Based k Selection`

- [x] 19. Write `src/annotate_timeline.py` — population-weighted regional trend with event annotations
  - Compute population-weighted mean `internet_penetration_pct` per year across all countries
  - Load key events from `config/key_events.yaml`; draw a vertical dashed line and label for
    each event; skip events outside the study period with a logged warning
  - Include axis labels, title, data-source caption, and legend
  - Write `outputs/annotated_timeline.png` at 150 DPI minimum
  - **Reviewable output:** `outputs/annotated_timeline.png` written; print file size in KB
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 19.1 Write property test for population-weighted mean correctness — Property 10
    - **Property 10:** For any panel DataFrame, the weighted mean per year equals
      `sum(internet_penetration_pct × population) / sum(population)` computed independently
    - **Validates: Requirements 8.1**
    - Use `hypothesis` with random panel DataFrames containing population and penetration columns
    - Tag: `# Feature: internet-adoption-analysis, Property 10: Population-Weighted Mean Correctness`

- [x] 20. Checkpoint — visualization and analysis complete
  - Confirm all four output images exist in `outputs/`; print each file name and size in KB
  - Confirm both cluster CSVs exist in their respective directories
  - Ensure all tests pass; ask the user if questions arise before proceeding to Phase 5

---

### Phase 5 — Synthesis

- [x] 21. Write `src/report.py` — policy summary report generator
  - Read `panel_dataset.csv`, `cluster_assignments.csv`, and `config/key_events.yaml`
  - Generate `outputs/policy_summary.md` using string templates (no LLM dependency) with
    sections: Overview, Key Findings (one paragraph per cluster), Event Impacts, Data
    Limitations, Scope
  - Include date range, country count, cluster labels, and representative countries
  - Check Flesch–Kincaid reading ease with `textstat`; print warning if score < 50
  - **Reviewable output:** print word count, section headings, and Flesch–Kincaid score to stdout
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 22. Add final-pipeline summary to `Makefile` `report` target
  - After `report.py` completes, print a summary listing each output file and its size in KB
  - **Reviewable output:** run `make report` (or `make all`) and confirm the summary block is printed
  - _Requirements: 10.2, 10.4_

- [x] 23. Write reproducibility verification script `src/verify_outputs.py`
  - Check that all five required output files exist: `gdp_vs_internet.png`,
    `country_trends.png`, `cluster_pca.png`, `annotated_timeline.png`, `policy_summary.md`
  - Verify each PNG meets 150 DPI minimum (read DPI metadata with `PIL`/`Pillow`)
  - Verify `panel_dataset.csv` covers ≥ 30 countries and ≥ 10 years
  - Verify null rate in `internet_penetration_pct` ≤ 10%
  - Verify `policy_summary.md` word count ≤ 1,000
  - Print PASS / FAIL for each check; exit with code 1 if any check fails
  - **Reviewable output:** run `python src/verify_outputs.py` and confirm all checks print PASS
  - _Requirements: 12.1, 12.2, 12.3, 12.5_

- [x] 24. Final checkpoint — full pipeline end-to-end
  - Run `make all` (or equivalent) and confirm it completes without errors
  - Run `python src/verify_outputs.py` and confirm all checks pass
  - Run `python -m pytest tests/ -q --tb=short` and confirm all tests pass
  - Ensure all tests pass; ask the user if questions arise

---

## Notes on Execution

When executing any task in this plan, the agent will:

1. **Announce the task** — state the task number and title before starting work.
2. **Perform the task** — write or modify the relevant code, config, or file.
3. **Show the output** — display the reviewable output (file contents, printed summary, chart
   confirmation, or test results) so the result can be inspected.
4. **Wait for approval** — pause and ask the user to confirm before moving on to the next task.

Tasks marked with `*` are optional property-based tests. They can be skipped for a faster
MVP run; the pipeline will still be fully functional without them. All non-optional tasks
must be completed in order within each phase before the phase checkpoint is reached.
