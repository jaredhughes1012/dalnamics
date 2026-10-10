DROP TRIGGER IF EXISTS sessions_record_rotated_refresh_token ON sessions;
DROP FUNCTION IF EXISTS record_rotated_refresh_token();
DROP TABLE IF EXISTS rotated_refresh_tokens;
