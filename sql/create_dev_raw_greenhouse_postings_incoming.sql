CREATE TABLE `dev_raw.greenhouse_postings_incoming` (
    id INT64 NOT NULL OPTIONS(description="Unique identifier of job posting"),
    title STRING NOT NULL,
    url STRING NOT NULL,
    location STRING,
    company  STRING NOT NULL,
    department STRING,
    office  STRING,
    language STRING NOT NULL,
    content STRING NOT NULL,
    updated_at TIMESTAMP,
    published_at TIMESTAMP NOT NULL,
    deadline_at TIMESTAMP,
    raw STRING NOT NULL,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    landed_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id, landed_at) NOT ENFORCED
)
PARTITION BY DATE(last_seen_at)
OPTIONS(description="This table holds raw greenhouse job postings. Grain is one row per job posting per landed file.");