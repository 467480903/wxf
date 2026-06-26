-- G2A map id 39 restore helper generated 20260625_202853
-- Source DB: /data/dlb/dlb.db
-- Expects map39_map_info.blob and map39_updated_map_info.blob in the sqlite3 working directory.
BEGIN;
CREATE TABLE IF NOT EXISTS maps (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      version INTEGER,
      map_info BLOB,
      updated_map_info BLOB,
      is_current BOOLEAN,
      name TEXT,
      aid TEXT,
      timestamp INTEGER,
      status TEXT
    );
INSERT OR REPLACE INTO maps (id, version, map_info, updated_map_info, is_current, name, aid, timestamp, status)
VALUES (39, 35, readfile('map39_map_info.blob'), readfile('map39_updated_map_info.blob'), 1, "", "G2A0004BC00689", 1782114862, "stg");
COMMIT;
