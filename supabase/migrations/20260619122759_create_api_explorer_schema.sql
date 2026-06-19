/*
# API Explorer Dashboard Schema

1. New Tables
- `api_modules` - Stores API module categories (agent, call, club, common, finance, game, live, message, online, user, workbench)
- `api_endpoints` - Stores all 270 API endpoints from Duoo APK
- `api_test_history` - Stores test execution history
- `uploaded_files` - Stores APK/config file uploads
- `api_environments` - Stores base URLs for different environments (prod, qa)

2. Security
- Enable RLS on all tables.
- Single-tenant: allow anon + authenticated access since this is a local testing tool.
*/

-- API Modules table
CREATE TABLE IF NOT EXISTS api_modules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  endpoint_count integer NOT NULL DEFAULT 0,
  color text DEFAULT '#3b82f6',
  created_at timestamptz DEFAULT now()
);

-- API Endpoints table
CREATE TABLE IF NOT EXISTS api_endpoints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id uuid REFERENCES api_modules(id) ON DELETE CASCADE,
  path text NOT NULL,
  method text NOT NULL DEFAULT 'GET',
  description text,
  query_params jsonb DEFAULT '[]',
  headers jsonb DEFAULT '{}',
  body_schema jsonb DEFAULT '{}',
  response_schema jsonb DEFAULT '{}',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- API Test History table
CREATE TABLE IF NOT EXISTS api_test_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint_id uuid REFERENCES api_endpoints(id) ON DELETE CASCADE,
  base_url text NOT NULL DEFAULT 'https://api.duoo.live',
  full_url text NOT NULL,
  method text NOT NULL,
  request_headers jsonb DEFAULT '{}',
  request_body jsonb DEFAULT '{}',
  response_status integer,
  response_body jsonb DEFAULT '{}',
  response_headers jsonb DEFAULT '{}',
  duration_ms integer,
  error_message text,
  created_at timestamptz DEFAULT now()
);

-- Uploaded Files table
CREATE TABLE IF NOT EXISTS uploaded_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  file_type text NOT NULL,
  file_size integer NOT NULL,
  storage_path text NOT NULL,
  description text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- API Environments table
CREATE TABLE IF NOT EXISTS api_environments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  base_url text NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE api_modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_endpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_test_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_environments ENABLE ROW LEVEL SECURITY;

-- Policies for api_modules (public read)
DROP POLICY IF EXISTS "select_api_modules" ON api_modules;
CREATE POLICY "select_api_modules" ON api_modules FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_api_modules" ON api_modules;
CREATE POLICY "insert_api_modules" ON api_modules FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "update_api_modules" ON api_modules;
CREATE POLICY "update_api_modules" ON api_modules FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "delete_api_modules" ON api_modules;
CREATE POLICY "delete_api_modules" ON api_modules FOR DELETE
  TO anon, authenticated USING (true);

-- Policies for api_endpoints (public read)
DROP POLICY IF EXISTS "select_api_endpoints" ON api_endpoints;
CREATE POLICY "select_api_endpoints" ON api_endpoints FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_api_endpoints" ON api_endpoints;
CREATE POLICY "insert_api_endpoints" ON api_endpoints FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "update_api_endpoints" ON api_endpoints;
CREATE POLICY "update_api_endpoints" ON api_endpoints FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "delete_api_endpoints" ON api_endpoints;
CREATE POLICY "delete_api_endpoints" ON api_endpoints FOR DELETE
  TO anon, authenticated USING (true);

-- Policies for api_test_history (public read)
DROP POLICY IF EXISTS "select_api_test_history" ON api_test_history;
CREATE POLICY "select_api_test_history" ON api_test_history FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_api_test_history" ON api_test_history;
CREATE POLICY "insert_api_test_history" ON api_test_history FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "update_api_test_history" ON api_test_history;
CREATE POLICY "update_api_test_history" ON api_test_history FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "delete_api_test_history" ON api_test_history;
CREATE POLICY "delete_api_test_history" ON api_test_history FOR DELETE
  TO anon, authenticated USING (true);

-- Policies for uploaded_files (public read)
DROP POLICY IF EXISTS "select_uploaded_files" ON uploaded_files;
CREATE POLICY "select_uploaded_files" ON uploaded_files FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_uploaded_files" ON uploaded_files;
CREATE POLICY "insert_uploaded_files" ON uploaded_files FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "update_uploaded_files" ON uploaded_files;
CREATE POLICY "update_uploaded_files" ON uploaded_files FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "delete_uploaded_files" ON uploaded_files;
CREATE POLICY "delete_uploaded_files" ON uploaded_files FOR DELETE
  TO anon, authenticated USING (true);

-- Policies for api_environments (public read)
DROP POLICY IF EXISTS "select_api_environments" ON api_environments;
CREATE POLICY "select_api_environments" ON api_environments FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_api_environments" ON api_environments;
CREATE POLICY "insert_api_environments" ON api_environments FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "update_api_environments" ON api_environments;
CREATE POLICY "update_api_environments" ON api_environments FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "delete_api_environments" ON api_environments;
CREATE POLICY "delete_api_environments" ON api_environments FOR DELETE
  TO anon, authenticated USING (true);
