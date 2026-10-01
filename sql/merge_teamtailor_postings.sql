MERGE `{dataset}.teamtailor_postings` AS T
USING (
    SELECT *
    FROM `{dataset}.teamtailor_postings_incoming`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY landed_at DESC) = 1
) AS S
ON T.id = S.id
WHEN MATCHED and T.last_seen_at < S.last_seen_at THEN
    UPDATE SET
    T.title = S.title,
    T.url = S.url,
    T.location = S.location,
    T.city = S.city,
    T.country = S.country,
    T.remote_status = S.remote_status,
    T.department = S.department,
    T.role = S.role,
    T.content = S.content,
    T.published_at = S.published_at,
    T.raw = S.raw,
    T.last_seen_at = S.last_seen_at
WHEN MATCHED and T.first_seen_at > S.first_seen_at THEN
    UPDATE SET
    T.first_seen_at = S.first_seen_at
WHEN NOT MATCHED THEN
    INSERT (id, title, url, location, city, country, remote_status, department, role, content, published_at, raw, first_seen_at, last_seen_at)
    VALUES (S.id, S.title, S.url, S.location, S.city, S.country, S.remote_status, S.department, S.role, S.content, S.published_at, S.raw, S.first_seen_at, S.last_seen_at)
