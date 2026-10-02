MERGE `{dataset}.workable_postings` AS T
USING (
    SELECT *
    FROM `{dataset}.workable_postings_incoming`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY landed_at DESC) = 1
) AS S
ON T.id = S.id
-- List columns follow the newest file. Detail columns change only when this file carried a
-- detail response (has_detail): most nights fetch none for a known job, and a plain
-- "newest wins" would overwrite last week's description with NULL.
WHEN MATCHED and T.last_seen_at < S.last_seen_at THEN
    UPDATE SET
    T.title = S.title,
    T.url = S.url,
    T.city = S.city,
    T.region = S.region,
    T.country = S.country,
    T.country_code = S.country_code,
    T.telecommuting = S.telecommuting,
    T.department = S.department,
    T.employment_type = S.employment_type,
    T.education = S.education,
    T.experience = S.experience,
    T.industry = S.industry,
    T.job_function = S.job_function,
    T.published_on = S.published_on,
    T.raw = S.raw,
    T.workplace = IF(S.has_detail, S.workplace, T.workplace),
    T.language = IF(S.has_detail, S.language, T.language),
    T.content = IF(S.has_detail, S.content, T.content),
    T.requirements = IF(S.has_detail, S.requirements, T.requirements),
    T.benefits = IF(S.has_detail, S.benefits, T.benefits),
    T.salary_min = IF(S.has_detail, S.salary_min, T.salary_min),
    T.salary_max = IF(S.has_detail, S.salary_max, T.salary_max),
    T.salary_currency = IF(S.has_detail, S.salary_currency, T.salary_currency),
    T.salary_frequency = IF(S.has_detail, S.salary_frequency, T.salary_frequency),
    T.raw_detail = IF(S.has_detail, S.raw_detail, T.raw_detail),
    T.detail_fetched_at = IF(S.has_detail, S.last_seen_at, T.detail_fetched_at),
    T.last_seen_at = S.last_seen_at
WHEN MATCHED and T.first_seen_at > S.first_seen_at THEN
    UPDATE SET
    T.first_seen_at = S.first_seen_at
WHEN NOT MATCHED THEN
    INSERT (id, title, url, city, region, country, country_code, telecommuting, department, employment_type, education, experience, industry, job_function, published_on, raw, workplace, language, content, requirements, benefits, salary_min, salary_max, salary_currency, salary_frequency, raw_detail, detail_fetched_at, first_seen_at, last_seen_at)
    VALUES (S.id, S.title, S.url, S.city, S.region, S.country, S.country_code, S.telecommuting, S.department, S.employment_type, S.education, S.experience, S.industry, S.job_function, S.published_on, S.raw, S.workplace, S.language, S.content, S.requirements, S.benefits, S.salary_min, S.salary_max, S.salary_currency, S.salary_frequency, S.raw_detail, IF(S.has_detail, S.last_seen_at, NULL), S.first_seen_at, S.last_seen_at)
