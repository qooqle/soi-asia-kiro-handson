# Requirements Document

## Introduction

This project builds a reproducible data analysis pipeline that explores the relationship between internet penetration, economic indicators, and demographic indicators across 30–40 countries in Asia, Oceania, and the Pacific Rim from 2010 to the latest available year. The pipeline covers data acquisition from public sources (World Bank, ITU), cleaning and panel construction, exploratory visualization, unsupervised clustering of adoption patterns, event-annotated timeline charts, and a concise policy-audience summary report.

The project is a standalone analytical artefact — it does not include a web application, real-time data feeds, predictive modelling, or policy recommendations beyond descriptive findings.

---

## Glossary

- **Pipeline**: The end-to-end sequence of scripts that transforms raw source data into final outputs.
- **Panel_Dataset**: A tidy, country-year structured dataset where each row represents one country in one year.
- **Country_Scope**: The fixed list of 30–40 countries in Asia, Oceania, and the Pacific Rim defined in the project configuration.
- **Indicator**: A named, numeric time-series variable (e.g., internet penetration rate, GDP per capita, population).
- **Internet_Penetration_Rate**: Percentage of a country's population that uses the internet, as reported by ITU or World Bank.
- **GDP_per_Capita**: Gross domestic product divided by mid-year population, expressed in constant 2015 USD (World Bank series NY.GDP.PCAP.KD).
- **Key_Event**: A named, dated occurrence known to have influenced internet adoption in the region (e.g., Jio launch 2016, Palapa Ring completion 2019, Coral Sea Cable 2019, COVID-19 pandemic 2020, Starlink Asia-Pacific expansion 2022).
- **Cluster**: A group of countries assigned by an unsupervised algorithm based on similarity of adoption-pattern features.
- **Adoption_Pattern**: The shape of a country's internet penetration trajectory over the study period, characterised by starting level, growth rate, and inflection points.
- **Policy_Summary**: A short (≤ 1,000-word) plain-language document describing findings for a non-technical policy audience.
- **Reproducibility_Artifact**: Any file (requirements.txt, environment.yml, Makefile, or equivalent) that allows a third party to recreate the analysis environment and re-run the pipeline.
- **Raw_Data_Directory**: The local directory `data/raw/` where downloaded source files are stored unmodified.
- **Processed_Data_Directory**: The local directory `data/processed/` where cleaned and merged files are stored.
- **Output_Directory**: The local directory `outputs/` where all charts, tables, and the policy summary are written.

---

## Requirements

### Requirement 1: Data Acquisition — World Bank Indicators

**User Story:** As a data analyst, I want to download World Bank indicator series for all countries in scope, so that I have authoritative economic and demographic data for the study period.

#### Acceptance Criteria

1. WHEN the acquisition script is executed, THE Pipeline SHALL download the following World Bank series for every country in Country_Scope and every year from 2010 to the latest available year: GDP per capita (NY.GDP.PCAP.KD), population (SP.POP.TOTL), urban population share (SP.URB.TOTL.IN.ZS), and fixed-broadband subscriptions per 100 people (IT.NET.BBND.P2).
2. WHEN a World Bank API request succeeds, THE Pipeline SHALL save the raw response to Raw_Data_Directory without modification.
3. IF a World Bank API request returns an HTTP error code or times out after 30 seconds, THEN THE Pipeline SHALL retry the request up to 3 times with exponential back-off before logging the failure and continuing with remaining requests.
4. WHEN all World Bank downloads complete, THE Pipeline SHALL log the count of successfully retrieved series and the count of failures to standard output.

---

### Requirement 2: Data Acquisition — ITU Internet Penetration Data

**User Story:** As a data analyst, I want to incorporate ITU internet-use statistics, so that I have the most authoritative internet penetration figures available.

#### Acceptance Criteria

1. WHEN the acquisition script is executed, THE Pipeline SHALL retrieve ITU "Individuals using the Internet (% of population)" data for every country in Country_Scope and every year from 2010 to the latest available year.
2. WHEN ITU data is retrieved, THE Pipeline SHALL save the raw file to Raw_Data_Directory without modification.
3. IF ITU data for a given country-year is unavailable from the ITU source, THEN THE Pipeline SHALL fall back to the equivalent World Bank series (IT.NET.USER.ZS) for that country-year and record the substitution in a provenance log.
4. WHEN data acquisition completes, THE Pipeline SHALL produce a provenance log file in Raw_Data_Directory that records the source (ITU or World Bank fallback) for every country-year internet penetration value.

---

### Requirement 3: Country Scope Configuration

**User Story:** As a data analyst, I want the country list to be defined in a single configuration file, so that the scope can be adjusted without modifying pipeline code.

#### Acceptance Criteria

1. THE Pipeline SHALL read Country_Scope exclusively from a configuration file located at `config/countries.yaml`.
2. WHEN the configuration file specifies between 30 and 40 country entries, THE Pipeline SHALL include exactly those countries in all downstream steps.
3. IF the configuration file specifies fewer than 30 or more than 40 country entries, THEN THE Pipeline SHALL exit with a descriptive error message before executing any download or processing step.
4. THE Pipeline SHALL validate that every country entry in the configuration file contains a valid ISO 3166-1 alpha-3 code before proceeding.

---

### Requirement 4: Data Cleaning and Panel Construction

**User Story:** As a data analyst, I want a clean, tidy country-year panel dataset, so that all analysis steps operate on a consistent, well-documented data structure.

#### Acceptance Criteria

1. WHEN the cleaning script is executed, THE Pipeline SHALL merge all acquired indicator series into a single Panel_Dataset with columns: `iso3`, `country_name`, `year`, `internet_penetration_pct`, `gdp_per_capita_usd`, `population`, `urban_pop_share_pct`, `broadband_per_100`.
2. THE Panel_Dataset SHALL contain one row per unique (iso3, year) combination with no duplicate rows.
3. WHEN a country-year observation is missing internet penetration data for 3 or fewer consecutive years, THE Pipeline SHALL apply linear interpolation to fill those gaps and flag the interpolated values in a boolean column `internet_pct_interpolated`.
4. IF a country-year observation is missing internet penetration data for more than 3 consecutive years, THEN THE Pipeline SHALL retain the row with a null value and set `internet_pct_interpolated` to False.
5. WHEN cleaning is complete, THE Pipeline SHALL write the Panel_Dataset to Processed_Data_Directory as a UTF-8 encoded CSV file named `panel_dataset.csv`.
6. WHEN cleaning is complete, THE Pipeline SHALL print a data-quality report to standard output showing: total row count, count of interpolated values per country, and count of null values per indicator column.

---

### Requirement 5: Exploratory Visualization — GDP vs. Internet Penetration

**User Story:** As a data analyst, I want a scatter plot of GDP per capita against internet penetration for each country-year, so that I can communicate the economic correlation to a policy audience.

#### Acceptance Criteria

1. WHEN the visualization script is executed, THE Pipeline SHALL produce a scatter plot where the x-axis represents GDP_per_Capita (log scale) and the y-axis represents Internet_Penetration_Rate (linear scale, 0–100%).
2. THE scatter plot SHALL encode each data point with a colour that identifies the country and a marker size proportional to population.
3. THE scatter plot SHALL include a best-fit regression line with a 95% confidence interval band.
4. THE scatter plot SHALL display the Pearson correlation coefficient and its p-value as an annotation within the plot area.
5. WHEN the scatter plot is generated, THE Pipeline SHALL write it to Output_Directory as `gdp_vs_internet.png` at a minimum resolution of 150 DPI.
6. THE scatter plot SHALL include axis labels, a title, a legend identifying countries, and a caption stating the data sources and year range.

---

### Requirement 6: Exploratory Visualization — Per-Country Trend Lines

**User Story:** As a data analyst, I want a small-multiples chart showing each country's internet penetration trend over time, so that I can identify individual trajectories at a glance.

#### Acceptance Criteria

1. WHEN the visualization script is executed, THE Pipeline SHALL produce a small-multiples line chart with one panel per country in Country_Scope, showing Internet_Penetration_Rate on the y-axis and year on the x-axis.
2. THE small-multiples chart SHALL use a consistent y-axis range of 0–100% across all panels to allow direct visual comparison.
3. WHEN the small-multiples chart is generated, THE Pipeline SHALL write it to Output_Directory as `country_trends.png` at a minimum resolution of 150 DPI.

---

### Requirement 7: Clustering — Adoption Pattern Segmentation

**User Story:** As a data analyst, I want countries grouped into 4–5 interpretable adoption-pattern clusters, so that I can describe distinct regional trajectories in the policy summary.

#### Acceptance Criteria

1. WHEN the clustering script is executed, THE Pipeline SHALL compute per-country features from the Panel_Dataset including: internet penetration in 2010 (or earliest available year), internet penetration in the latest available year, mean annual growth rate of internet penetration, and year in which internet penetration first exceeded 50%.
2. THE Pipeline SHALL apply k-means clustering with k values of 4 and 5, and SHALL select the final k using the silhouette score, choosing the k with the higher mean silhouette score.
3. WHEN clustering is complete, THE Pipeline SHALL assign each country a cluster label and write a CSV file named `cluster_assignments.csv` to Processed_Data_Directory containing columns: `iso3`, `country_name`, `cluster_label`, and all features used in clustering.
4. THE Pipeline SHALL produce a 2-D scatter plot of the first two principal components of the feature matrix, coloured by cluster label and annotated with country ISO3 codes, and write it to Output_Directory as `cluster_pca.png` at a minimum resolution of 150 DPI.
5. THE Pipeline SHALL produce a summary table showing the mean value of each clustering feature per cluster and write it to Output_Directory as `cluster_summary.csv`.
6. WHEN the silhouette score for the selected k is below 0.25, THE Pipeline SHALL print a warning to standard output stating that cluster separation is weak and results should be interpreted with caution.

---

### Requirement 8: Event Annotation — Annotated Timeline

**User Story:** As a data analyst, I want a regional internet penetration timeline annotated with key events, so that I can show policy audiences how specific interventions or shocks correlate with adoption changes.

#### Acceptance Criteria

1. WHEN the annotation script is executed, THE Pipeline SHALL compute the population-weighted mean Internet_Penetration_Rate across all countries in Country_Scope for each year and plot it as a line chart with year on the x-axis and weighted mean penetration on the y-axis.
2. THE Pipeline SHALL read Key_Event definitions (name, year, optional month) from a configuration file located at `config/key_events.yaml` and SHALL annotate the timeline chart with a vertical dashed line and label for each Key_Event.
3. THE configuration file `config/key_events.yaml` SHALL include at minimum the following events: Jio commercial launch (September 2016), Palapa Ring completion (2019), Coral Sea Cable activation (2019), COVID-19 pandemic onset (2020), and Starlink Asia-Pacific expansion (2022).
4. IF a Key_Event year falls outside the study period, THEN THE Pipeline SHALL log a warning and omit that event from the chart without raising an error.
5. WHEN the annotated timeline is generated, THE Pipeline SHALL write it to Output_Directory as `annotated_timeline.png` at a minimum resolution of 150 DPI.
6. THE annotated timeline SHALL include axis labels, a title, a data-source caption, and a legend identifying the Key_Events.

---

### Requirement 9: Policy Summary Report

**User Story:** As a policy analyst, I want a concise written summary of the findings, so that I can share key insights with non-technical stakeholders without requiring them to interpret charts directly.

#### Acceptance Criteria

1. WHEN the report generation script is executed, THE Pipeline SHALL produce a Policy_Summary document of no more than 1,000 words written in plain language free of statistical jargon.
2. THE Policy_Summary SHALL include the following sections: Overview, Key Findings (one paragraph per cluster describing its adoption pattern and representative countries), Event Impacts (a brief description of each Key_Event's apparent effect on the regional trend), Data Limitations, and Scope.
3. THE Policy_Summary SHALL reference the cluster labels and representative countries derived from the clustering step.
4. THE Policy_Summary SHALL state the date range and country count covered by the analysis.
5. WHEN the report is generated, THE Pipeline SHALL write it to Output_Directory as `policy_summary.md` in valid Markdown format.

---

### Requirement 10: Reproducibility and Environment

**User Story:** As a collaborator, I want a fully specified execution environment and a single entry-point command, so that I can reproduce the entire analysis on a fresh machine without manual configuration.

#### Acceptance Criteria

1. THE Pipeline SHALL include a Reproducibility_Artifact that lists all Python package dependencies with pinned version numbers.
2. WHEN the entry-point command `make all` (or equivalent) is executed in a correctly configured environment, THE Pipeline SHALL execute all steps — acquisition, cleaning, visualization, clustering, annotation, and report generation — in dependency order without manual intervention.
3. THE Pipeline SHALL be executable with Python 3.10 or later.
4. WHEN the full pipeline completes successfully, THE Pipeline SHALL print a summary to standard output listing each output file written and its file size in kilobytes.

---

### Requirement 11: Scope Boundaries

**User Story:** As a project stakeholder, I want explicit scope boundaries documented, so that out-of-scope requests do not expand the project without deliberate decision.

#### Acceptance Criteria

1. THE Pipeline SHALL NOT include a web application, interactive dashboard, or real-time data feed.
2. THE Pipeline SHALL NOT perform predictive modelling, forecasting, or causal inference.
3. THE Pipeline SHALL NOT cover countries outside Asia, Oceania, and the Pacific Rim as defined in `config/countries.yaml`.
4. THE Pipeline SHALL NOT cover years before 2010.
5. THE Policy_Summary SHALL NOT make prescriptive policy recommendations; it SHALL describe findings only.

---

### Requirement 12: Success Criteria

**User Story:** As a project stakeholder, I want measurable success criteria, so that I can objectively determine when the project is complete.

#### Acceptance Criteria

1. THE Pipeline SHALL produce all five output files — `gdp_vs_internet.png`, `country_trends.png`, `cluster_pca.png`, `annotated_timeline.png`, and `policy_summary.md` — without manual intervention.
2. THE Panel_Dataset SHALL cover at least 30 countries and at least 10 years of data.
3. THE Panel_Dataset SHALL have no more than 10% null values in the `internet_penetration_pct` column across all country-year rows.
4. THE clustering step SHALL produce a silhouette score of 0.20 or above for the selected k.
5. THE Policy_Summary SHALL pass a Flesch–Kincaid readability check with a reading ease score of 50 or above, confirming plain-language accessibility.
6. WHEN executed on a clean environment with valid credentials and internet access, THE Pipeline SHALL complete all steps within 30 minutes on a standard laptop (defined as a machine with 4 CPU cores and 8 GB RAM).
