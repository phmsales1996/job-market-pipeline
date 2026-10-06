MERGE `{dataset}.recruitee_postings` AS T
USING (
    SELECT *
    FROM `{dataset}.recruitee_postings_incoming`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY landed_at DESC) = 1
) AS S
ON T.id = S.id
WHEN MATCHED and T.last_seen_at < S.last_seen_at THEN
    UPDATE SET
    T.title = S.title,
    T.company_slug = S.company_slug,
    T.language = S.language,
    T.url = S.url,
    T.location = S.location,
    T.remote = S.remote,
    T.hybrid = S.hybrid,
    T.on_site = S.on_site,
    T.country_code = S.country_code,
    T.department = S.department,
    T.employment_type = S.employment_type,
    T.content = S.content,
    T.requirements = S.requirements,
    T.highlight = S.highlight,
    T.salary_min = S.salary_min,
    T.salary_max = S.salary_max,
    T.salary_currency = S.salary_currency,
    T.salary_period = S.salary_period,
    T.published_at = S.published_at,
    T.updated_at = S.updated_at,
    T.raw = S.raw,
    T.last_seen_at = S.last_seen_at
WHEN MATCHED and T.first_seen_at > S.first_seen_at THEN
    UPDATE SET
    T.first_seen_at = S.first_seen_at
WHEN NOT MATCHED THEN
    INSERT (id, title, company_slug, language, url, location, remote, hybrid, on_site, country_code, department, employment_type, content, requirements, highlight, salary_min, salary_max, salary_currency, salary_period, published_at, updated_at, raw, first_seen_at, last_seen_at)
    VALUES (S.id, S.title, S.company_slug, S.language, S.url, S.location, S.remote, S.hybrid, S.on_site, S.country_code, S.department, S.employment_type, S.content, S.requirements, S.highlight, S.salary_min, S.salary_max, S.salary_currency, S.salary_period, S.published_at, S.updated_at, S.raw, S.first_seen_at, S.last_seen_at)
