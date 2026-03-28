-- Initialize PostgreSQL database for APISEC
-- This script runs automatically when the PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_apis_base_url ON apis(base_url);
CREATE INDEX IF NOT EXISTS idx_schema_snapshots_api_id ON schema_snapshots(api_id);
CREATE INDEX IF NOT EXISTS idx_schema_snapshots_version ON schema_snapshots(api_id, version_number);

-- Create GIN index for JSONB operations
CREATE INDEX IF NOT EXISTS idx_schema_snapshots_json_gin ON schema_snapshots USING GIN (schema_json);

-- Set proper permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO apisec_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO apisec_user;
