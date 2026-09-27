CREATE TABLE `dev_raw.companies` (
    name STRING NOT NULL OPTIONS(description="Company name for humans, e.g. 'GitLab'. Display only: never used to match or fetch. MIXED PROVENANCE: for Greenhouse it is the real name the API reports ('company_name'); for Lever, whose payload carries no company name, it is DERIVED from external_id by scripts/seed_companies.py (hyphens and underscores to spaces, title-cased), so 'octoenergy' becomes 'Octoenergy' rather than 'Octopus Energy'. Nothing in this table distinguishes the two - check the source's row in ats before trusting a name."),
    external_id STRING NOT NULL OPTIONS(description="The company's identifier on its ATS platform - for Greenhouse, the job board slug used in the API URL, e.g. 'gitlab'. Case-sensitive, and the value the extractor iterates over."),
    ats STRING NOT NULL OPTIONS(description="Which ATS platform hosts this company's board, lowercase, e.g. 'greenhouse'. Compared in code (WHERE ats = 'greenhouse'), so casing matters; each source DAG filters on it."),
    PRIMARY KEY (external_id, ats) NOT ENFORCED
)
OPTIONS(description="One row per company per ATS platform: the registry of boards the pipeline collects from. Pipeline configuration, not a warehouse dimension - dim_company in the marts layer is a different thing. The extractor reads this table to decide what to fetch.");
