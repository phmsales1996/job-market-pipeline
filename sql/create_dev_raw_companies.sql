CREATE TABLE `dev_raw.companies` (
    name STRING NOT NULL OPTIONS(description="Company name for humans, e.g. 'GitLab'. Display only: never used to match or fetch."),
    external_id STRING NOT NULL OPTIONS(description="The company's identifier on its ATS platform - for Greenhouse, the job board slug used in the API URL, e.g. 'gitlab'. Case-sensitive, and the value the extractor iterates over."),
    ats STRING NOT NULL OPTIONS(description="Which ATS platform hosts this company's board, lowercase, e.g. 'greenhouse'. Compared in code (WHERE ats = 'greenhouse'), so casing matters; each source DAG filters on it."),
    PRIMARY KEY (external_id, ats) NOT ENFORCED
)
OPTIONS(description="One row per company per ATS platform: the registry of boards the pipeline collects from. Pipeline configuration, not a warehouse dimension - dim_company in the marts layer is a different thing. The extractor reads this table to decide what to fetch.");
