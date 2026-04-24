# soi-asia-kiro-handson

# Prompts
## Requirements
```
I want to build a data analysis project that explores the relationship between internet penetration, economic indicators, and demographic indicators across roughly 30–40 countries in Asia, Oceania, and the Pacific Rim from 2010 to the latest available year.
Goals:

1. Build a clean country-year panel dataset from public sources (World Bank, ITU).
2. Visualize the relationship between GDP per capita and internet penetration.
3. Cluster countries into 4–5 interpretable adoption patterns.
4. Annotate a timeline with key events that shaped adoption (Jio launch, Palapa Ring, Coral Sea Cable, COVID-19, Starlink).
5. Produce a short policy-audience summary.

Please generate requirements.md using user stories with EARS-style acceptance criteria ("When X, the system shall Y"). Cover data acquisition, cleaning, visualization, clustering, event annotation, and the final summary. Include scope boundaries and success criteria.
Do not start implementation yet. Just produce requirements.md for my review.
```

## Design
```
Requirements look good. Now generate design.md based on requirements.md.
Include: target country list with ISO3 codes grouped by sub-region; concrete data sources (World Bank indicator codes and ITU endpoints); the processing pipeline as a diagram; analytical methods for clustering (k-means with silhouette selection); the directory layout; library choices; and a risks-and-mitigations table.
Do not start implementation. Produce design.md for my review.
```

## Tasks 
```
Let's begin executing tasks.md. Start with task T1.
After completing it, show me what you produced and wait for my approval before moving to T2.
Task Tn failed with <error>. Please:
Explain what went wrong in plain language.
Propose a fix.
If this reveals a gap in design.md, update the design first, then retry.
```