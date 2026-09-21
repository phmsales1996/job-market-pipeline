MERGE `{dataset}.greenhouse_postings` AS T
USING (
    SELECT *
    FROM `{dataset}.greenhouse_postings_incoming`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY landed_at DESC) = 1
) AS S
ON T.id = S.id
WHEN MATCHED THEN
    UPDATE SET
    T.title = S.title,
    T.url = S.url,
    T.location = S.location,
    T.company = S.company,
    T.department = S.department,
    T.office = S.office,
    T.language = S.language,
    T.content = S.content,
    T.updated_at = S.updated_at,
    T.published_at = S.published_at,
    T.deadline_at = S.deadline_at,
    T.raw = S.raw,
    T.last_seen_at = S.last_seen_at
WHEN NOT MATCHED THEN
    INSERT (id, title, url, location, company, department, office, language, content, updated_at, published_at, deadline_at, raw, first_seen_at, last_seen_at)
    VALUES (S.id, S.title, S.url, S.location, S.company, S.department, S.office, S.language, S.content, S.updated_at, S.published_at, S.deadline_at, S.raw, S.first_seen_at, S.last_seen_at)