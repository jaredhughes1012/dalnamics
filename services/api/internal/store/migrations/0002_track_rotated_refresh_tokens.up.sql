CREATE TABLE rotated_refresh_tokens (
    token_hash bytea PRIMARY KEY,
    session_id uuid NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    rotated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX rotated_refresh_tokens_session_id_idx ON rotated_refresh_tokens (session_id);

COMMENT ON TABLE rotated_refresh_tokens IS
    'SHA-256 of every refresh token a session has rotated away from, written by a trigger on sessions. Presenting one of these again means the token was copied, so the api revokes its session.';

CREATE FUNCTION record_rotated_refresh_token() RETURNS trigger AS $$
BEGIN
    INSERT INTO rotated_refresh_tokens (token_hash, session_id)
    VALUES (OLD.refresh_token_hash, OLD.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_record_rotated_refresh_token
    AFTER UPDATE OF refresh_token_hash ON sessions
    FOR EACH ROW
    WHEN (OLD.refresh_token_hash IS DISTINCT FROM NEW.refresh_token_hash)
    EXECUTE FUNCTION record_rotated_refresh_token();
