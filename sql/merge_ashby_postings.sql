MERGE `{dataset}.ashby_postings` AS T
USING (
    SELECT *
    FROM `{dataset}.ashby_postings_incoming`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY landed_at DESC) = 1
) AS S
ON T.id = S.id
WHEN MATCHED and T.last_seen_at < S.last_seen_at THEN
    UPDATE SET
    T.title = S.title,
    T.company_slug = S.company_slug,
    T.url = S.url,
    T.location = S.location,
    T.department = S.department,
    T.team = S.team,
    T.employment_type = S.employment_type,
    T.is_listed = S.is_listed,
    T.compensation_summary = S.compensation_summary,
    T.workplace_type = S.workplace_type,
    T.country = S.country,
    T.content = S.content,
    T.salary_min = S.salary_min,
    T.salary_max = S.salary_max,
    T.salary_currency = S.salary_currency,
    T.salary_interval = S.salary_interval,
    T.published_at = S.published_at,
    T.raw = S.raw,
    T.last_seen_at = S.last_seen_at
WHEN MATCHED and T.first_seen_at > S.first_seen_at THEN
    UPDATE SET
    T.first_seen_at = S.first_seen_at
WHEN NOT MATCHED THEN
    INSERT (id, title, company_slug, url, location, department, workplace_type, country, team, employment_type, is_listed, compensation_summary, content, salary_min, salary_max, salary_currency, salary_interval, published_at, raw, first_seen_at, last_seen_at)
    VALUES (S.id, S.title, S.company_slug, S.url, S.location, S.department, S.workplace_type, S.country, S.team, S.employment_type, S.is_listed, S.compensation_summary, S.content, S.salary_min, S.salary_max, S.salary_currency, S.salary_interval, S.published_at, S.raw, S.first_seen_at, S.last_seen_at)
