-- Remove query strings from historical artifact URLs; they may contain bearer tokens,
-- signed download parameters, search terms, or other sensitive values.
UPDATE twi_artifact_records
SET source_url = split_part(source_url, '?', 1)
WHERE strpos(source_url, '?') > 0;

INSERT INTO twi_schema_migrations(version) VALUES (4)
ON CONFLICT (version) DO NOTHING;
