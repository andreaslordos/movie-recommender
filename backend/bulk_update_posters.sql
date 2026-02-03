CREATE OR REPLACE FUNCTION bulk_update_posters(updates JSONB)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
  affected INT;
BEGIN
  UPDATE movies m
  SET poster_path = u.poster_path
  FROM jsonb_to_recordset(updates) AS u(id BIGINT, poster_path TEXT)
  WHERE m.id = u.id;

  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$;
