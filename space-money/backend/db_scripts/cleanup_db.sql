-- Complete cleanup script for Space Money database
-- Run this to remove all objects before migration

-- Drop all schemas (CASCADE will drop all dependent tables/enums)
DROP SCHEMA IF EXISTS "user" CASCADE;
DROP SCHEMA IF EXISTS "accounts" CASCADE;
DROP SCHEMA IF EXISTS "transactions" CASCADE;
DROP SCHEMA IF EXISTS "system" CASCADE;

-- Drop all ENUMs just to be sure
DROP TYPE IF EXISTS user_status_enum CASCADE;
DROP TYPE IF EXISTS sex_enum CASCADE;
DROP TYPE IF EXISTS income_source_enum CASCADE;
DROP TYPE IF EXISTS consent_type_enum CASCADE;
DROP TYPE IF EXISTS ingestion_method_enum CASCADE;
DROP TYPE IF EXISTS sync_status_enum CASCADE;
DROP TYPE IF EXISTS account_type_enum CASCADE;
DROP TYPE IF EXISTS account_status_enum CASCADE;
DROP TYPE IF EXISTS transaction_type_enum CASCADE;
DROP TYPE IF EXISTS event_type_enum CASCADE;
DROP TYPE IF EXISTS entity_type_enum CASCADE;

-- Drop alembic version table
DROP TABLE IF EXISTS alembic_version;
