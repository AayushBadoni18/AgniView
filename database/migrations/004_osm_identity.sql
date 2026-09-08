ALTER TABLE osm_industrial_zones ADD COLUMN osm_key text;
UPDATE osm_industrial_zones SET osm_key=osm_type || '/' || id;
ALTER TABLE osm_industrial_zones ALTER COLUMN osm_key SET NOT NULL;

ALTER TABLE historical_thermal_profiles ADD COLUMN industrial_zone_key text;
UPDATE historical_thermal_profiles p SET industrial_zone_key=z.osm_key
FROM osm_industrial_zones z WHERE p.industrial_zone_id=z.id;
ALTER TABLE historical_thermal_profiles DROP CONSTRAINT historical_thermal_profiles_industrial_zone_id_fkey;
ALTER TABLE historical_thermal_profiles DROP COLUMN industrial_zone_id;
ALTER TABLE historical_thermal_profiles RENAME COLUMN industrial_zone_key TO industrial_zone_id;

ALTER TABLE osm_industrial_zones DROP CONSTRAINT osm_industrial_zones_pkey;
ALTER TABLE osm_industrial_zones ADD PRIMARY KEY (osm_key);
ALTER TABLE historical_thermal_profiles ADD CONSTRAINT historical_thermal_profiles_industrial_zone_id_fkey
    FOREIGN KEY (industrial_zone_id) REFERENCES osm_industrial_zones(osm_key) ON DELETE SET NULL;
