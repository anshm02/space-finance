# Space Money Database Setup Guide

Complete guide for setting up PostgreSQL database schema with AWS RDS integration and DIFC compliance.

## Prerequisites

- AWS RDS PostgreSQL 15 instance in me-central-1 region
- Database name: `spacemoney-db-dev`
- Python 3.10+ with backend dependencies installed
- Lean Technologies API credentials

## Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `cryptography>=41.0.0` - AES-256 encryption for PII
- `sqlalchemy-utils>=0.41.1` - Encrypted field types
- All existing dependencies

## Step 2: Generate Encryption Key

```bash
python generate_encryption_key.py
```

This generates an AES-256 encryption key like:
```
ENCRYPTION_KEY=xW8fH2mP9qJ4nK7vL3tR6yU1sA5dF8gH9jK2lM4nP7qR==
```

**CRITICAL**: Store this key securely! If lost, encrypted data cannot be recovered.

## Step 3: Configure Environment Variables

Copy `.env.example` to `.env` and fill in your actual credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# AWS RDS Database Configuration
DATABASE_URL=postgresql+asyncpg://spacemoney_admin:YourPassword@your-endpoint.me-central-1.rds.amazonaws.com:5432/spacemoney-db-dev?ssl=require

# Encryption (from Step 2)
ENCRYPTION_KEY=your-generated-encryption-key-here

# AWS Configuration
AWS_REGION=me-central-1

# Lean Technologies API (your existing values)
LEAN_BASE_URL=https://sandbox.leantech.me
LEAN_APP_TOKEN=your-lean-app-token
```

### AWS RDS Connection String Format:

```
postgresql+asyncpg://USERNAME:PASSWORD@ENDPOINT:PORT/DATABASE?ssl=require
```

Example:
```
postgresql+asyncpg://spacemoney_admin:MySecurePass123@spacemoney-db-dev.c9abc123xyz.me-central-1.rds.amazonaws.com:5432/spacemoney-db-dev?ssl=require
```

## Step 4: Test Database Connection

Before running migrations, verify your connection:

```bash
python test_db_connection.py
```

Expected output:
```
============================================================
Space Money Database Connection Test
============================================================

Connecting to: your-endpoint.me-central-1.rds.amazonaws.com:5432/spacemoney-db-dev

✓ Connected to database successfully
✓ PostgreSQL version: PostgreSQL 15.x
✓ SSL connection active (DIFC compliant)
✓ Connection pool size: 5

============================================================
✅ All connection tests passed!
============================================================
```

**If connection fails:**
1. Check DATABASE_URL in .env
2. Verify AWS RDS security group allows your IP
3. Confirm username/password are correct
4. Ensure SSL certificate is valid

## Step 5: Run Database Migrations

Create all schemas and tables:

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> init_spacemoney_schema, initial schema with DIFC encryption
```

This creates:
- 4 PostgreSQL schemas: `user`, `accounts`, `transactions`, `system`
- 9 tables with proper indexes and constraints
- All ENUM types
- UUID extension

## Step 6: Verify Table Structure

Run the connection test again to see created tables:

```bash
python test_db_connection.py
```

Now you should see:
```
✓ Schemas found: accounts, system, transactions, user
✓ Found 9 tables:
  - accounts.account_balances
  - accounts.credit_card_details
  - accounts.user_accounts
  - system.audit_log
  - transactions.raw_transactions
  - user.consent_records
  - user.data_ingestion_config
  - user.user_demographics
  - user.user_profiles
```

## Step 7: Start Backend Server

```bash
uvicorn main:app --reload
```

The server will start with:
- Database connection pool (20 connections)
- SSL connection to AWS RDS
- Field-level encryption active

## Step 8: Test Dual Persistence

### 8.1 Link a Bank Account

Use your mobile app or API client to:
1. Create a Lean customer: `POST /api/v1/lean/customers`
2. Get customer token: `POST /api/v1/lean/customer-token/{customer_id}`
3. Use Lean Link SDK to connect bank account
4. Link entity: `POST /api/v1/lean/entities/link`

### 8.2 Sync Data

Trigger a data sync:

```bash
POST /api/v1/lean/sync
{
  "entity_id": "your-entity-id-from-lean",
  "from_date": "2024-01-01",
  "to_date": "2024-12-31"
}
```

### 8.3 Verify Dual Persistence

Run the verification script:

```bash
python verify_data_upsert.py
```

Expected output:
```
============================================================
Space Money Dual Persistence Verification
============================================================

1. Checking local file storage...
   ✓ Found 15 JSON files in ./data/raw
     - Accounts: 3
     - Balances: 3
     - Transactions: 3

2. Checking database storage...
   ✓ User accounts in database: 3
   ✓ Balance snapshots in database: 3
   ✓ Transactions in database: 156
   ✓ Audit log entries: 6

3. Verifying data integrity...
   Sample account:
     - ID: 550e8400-e29b-41d4-a716-446655440000
     - Institution: Emirates NBD
     - Type: CURRENT
     - Currency: AED
     - Linked: 2026-02-03 14:35:00

   Latest transaction:
     - ID: 660e8400-e29b-41d4-a716-446655440001
     - Date: 2024-12-15
     - Amount: 45.50
     - Type: debit
     - Created: 2026-02-03 14:35:10

============================================================
✅ Dual persistence verification complete!
   Data is being stored in BOTH files AND database
============================================================
```

## Database Schema Overview

### user Schema
- `user_profiles` - User accounts with encrypted email
- `user_demographics` - Age, income, demographics
- `consent_records` - DIFC compliance consent tracking
- `data_ingestion_config` - Lean access tokens (encrypted)

### accounts Schema
- `user_accounts` - Bank accounts with encrypted account numbers/IBANs
- `account_balances` - Historical balance snapshots
- `credit_card_details` - Credit card info with encrypted card numbers

### transactions Schema
- `raw_transactions` - All transactions with encrypted descriptions and Lean Insights categorization

### system Schema
- `audit_log` - DIFC compliance audit logging

## DIFC Compliance Features

### 1. Field-Level Encryption (AES-256)
Encrypted fields:
- `user.user_profiles.email`
- `user.data_ingestion_config.lean_access_token`
- `accounts.user_accounts.account_number`
- `accounts.user_accounts.iban`
- `accounts.credit_card_details.card_last_four`
- `transactions.raw_transactions.description`

### 2. Hashed Fields (SHA-256)
- `user.consent_records.ip_address`
- `system.audit_log.ip_address`

### 3. Encryption at Rest
- Enabled at AWS RDS level (verify in AWS console)

### 4. SSL/TLS in Transit
- All connections use `sslmode=require`

### 5. Audit Logging
- All sync operations logged in `system.audit_log`
- User actions tracked with event types

## Querying the Database

### Get User Accounts
```sql
SELECT 
    account_id,
    institution_name,
    account_name,
    account_type,
    currency_code,
    linked_at
FROM accounts.user_accounts
WHERE user_id = 'your-user-uuid'
ORDER BY linked_at DESC;
```

Note: `account_number` and `iban` will show encrypted ciphertext.

### Get Recent Transactions
```sql
SELECT 
    transaction_id,
    transaction_date,
    amount,
    currency_code,
    description_cleansed,  -- Use cleansed, not encrypted description
    transaction_type,
    lean_insights_category
FROM transactions.raw_transactions
WHERE account_id = 'your-account-uuid'
ORDER BY transaction_date DESC
LIMIT 20;
```

### Get Balance History
```sql
SELECT 
    snapshot_timestamp,
    balance,
    currency_code
FROM accounts.account_balances
WHERE account_id = 'your-account-uuid'
ORDER BY snapshot_timestamp DESC;
```

### Check Audit Logs
```sql
SELECT 
    timestamp,
    event_type,
    entity_type,
    user_id
FROM system.audit_log
ORDER BY timestamp DESC
LIMIT 50;
```

## Troubleshooting

### Migration Fails

**Error**: `permission denied for schema user`

Solution: Ensure database user has CREATE privileges:
```sql
GRANT CREATE ON DATABASE spacemoney-db-dev TO spacemoney_admin;
```

### Encryption Key Error

**Error**: `ENCRYPTION_KEY environment variable is not set`

Solution: Add key to .env file (run `python generate_encryption_key.py`)

### SSL Connection Error

**Error**: `SSL connection has been closed unexpectedly`

Solution: Verify connection string includes `?ssl=require` at the end

### No Data in Database

**Issue**: Files created but database empty

Check:
1. Database session passed to DataService
2. User ID mapping exists
3. Check logs for upsert errors
4. Run `verify_data_upsert.py`

## Backup and Recovery

### Backup Encryption Key
```bash
# Store in AWS Secrets Manager
aws secretsmanager create-secret \
    --name spacemoney/encryption-key \
    --secret-string "$ENCRYPTION_KEY" \
    --region me-central-1
```

### Database Backup
Use AWS RDS automated backups (configured in RDS console)

### Restore Encrypted Data
**CRITICAL**: You MUST have the original encryption key to decrypt data.

## Next Steps

1. ✅ Database schema created
2. ✅ Dual persistence working
3. ⬜ Configure AWS RDS automated backups
4. ⬜ Set up CloudWatch monitoring for database
5. ⬜ Implement key rotation policy
6. ⬜ Add database indexes optimization based on query patterns
7. ⬜ Set up read replicas for scaling (if needed)

## Support

For issues or questions:
1. Check logs: `backend/logs/`
2. Run diagnostic scripts: `test_db_connection.py`, `verify_data_upsert.py`
3. Verify all environment variables in `.env`
4. Check AWS RDS console for connection limits and performance
