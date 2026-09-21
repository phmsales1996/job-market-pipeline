CREATE TABLE `dev_raw.companies` (
    name STRING NOT NULL,
    external_id STRING NOT NULL,
    ats STRING NOT NULL,
    PRIMARY KEY (external_id, ats) NOT ENFORCED
)
OPTIONS(description="This table holds one row per company per ATS platform.");