CREATE TABLE `dev_raw.greenhouse_postings_incoming` (
    id INT64 NOT NULL OPTIONS(description="Greenhouse's own job posting id. Unique per row: this is the merge key."),
    title STRING OPTIONS(description="Job title as published, from the source field 'title'. Not cleaned: real values contain trailing spaces and inconsistent casing."),
    url STRING OPTIONS(description="Public URL of the posting on the company's Greenhouse board, from the source field 'absolute_url'."),
    location STRING OPTIONS(description="Free-text location as published by the company, from 'location.name', e.g. 'Remote - US', 'San Francisco or Remote', 'London'. Not normalised: country and remote status are not derived here."),
    company STRING OPTIONS(description="Company name as Greenhouse reports it ('company_name'), e.g. 'GitLab'. Not the board slug used to fetch it - that lives in dev_raw.companies.external_id."),
    department STRING OPTIONS(description="Name of the FIRST department listed for the posting ('departments[0].name'). Null when the posting lists none; any further departments are dropped here and remain available in 'raw'."),
    office STRING OPTIONS(description="Location of the FIRST office listed for the posting ('offices[0].location'). Null when the posting lists none; any further offices are dropped here and remain available in 'raw'."),
    language STRING OPTIONS(description="Language code of the posting as reported by the source ('language'), e.g. 'en'. Describes the posting text, not a language requirement for the role."),
    content STRING OPTIONS(description="Full job description as published, from 'content'. HTML with escaped entities (e.g. &lt;p&gt;), deliberately stored unparsed; cleaning belongs downstream."),
    updated_at TIMESTAMP OPTIONS(description="When the company last edited the posting, as reported by the source ('updated_at'). A source timestamp, not a pipeline one."),
    published_at TIMESTAMP OPTIONS(description="When the posting was first published, as reported by the source ('first_published'). A source timestamp, not a pipeline one."),
    deadline_at TIMESTAMP OPTIONS(description="Application deadline as reported by the source ('application_deadline'). Usually null: most postings have none."),
    raw STRING NOT NULL OPTIONS(description="The complete original API object for this posting, as JSON text. Kept so any field dropped or flattened above can be recovered without re-fetching."),
    first_seen_at TIMESTAMP NOT NULL OPTIONS(description="Landing time of the file this row came from. In staging it equals landed_at and last_seen_at; the MERGE decides what reaches the final table."),
    last_seen_at TIMESTAMP NOT NULL OPTIONS(description="Landing time of the file this row came from. Compared against the final table's last_seen_at by the MERGE, so older files cannot overwrite newer rows."),
    landed_at TIMESTAMP NOT NULL OPTIONS(description="When the GCS file this row came from was created (the object's time_created). Ties every row back to one landed file: used to deduplicate (newest file wins per id) and by the C2 check to prove staging was rebuilt from this day's files."),
    PRIMARY KEY (id, landed_at) NOT ENFORCED
)
PARTITION BY DATE(last_seen_at)
OPTIONS(description="One row per Greenhouse job posting PER LANDED FILE (so the same id appears once per file that contained it). Load-mechanics staging only: fully replaced (WRITE_TRUNCATE) on every run and then MERGEd into dev_raw.greenhouse_postings. Not the dbt staging layer - unrelated concept, same word.");
