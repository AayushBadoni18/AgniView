ALTER TABLE osm_industrial_zones ADD COLUMN content_hash text;
ALTER TABLE historical_thermal_profiles ADD COLUMN osm_context_hash text;
