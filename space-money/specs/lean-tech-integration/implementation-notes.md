# Lean Technologies Integration - Implementation Notes

## Overview
This implementation provides full integration with Lean Technologies Open Finance API in sandbox mode, including backend API services and mobile React Native components.

## Implementation Structure

### Backend (`backend/`)
- **config.py** - Environment configuration management with Pydantic
- **database.py** - Async PostgreSQL database setup with SQLAlchemy
- **models.py** - Database models for users, customers, entities, accounts, and sync logs
- **schemas.py** - Pydantic schemas for request/response validation
- **services/lean_client.py** - Lean API client with OAuth authentication and retry logic
- **services/data_service.py** - Data extraction service that saves API responses to JSON files
- **routers/lean.py** - FastAPI endpoints for customer management, entity linking, and data sync
- **main.py** - FastAPI application entry point
- **test_lean_integration.py** - Test script for validating the integration

### Mobile (`mobile/features/lean-integration/`)
- **types/index.ts** - TypeScript type definitions
- **api/leanApi.ts** - API client for backend communication
- **hooks/useLeanIntegration.ts** - React hook for state management
- **components/LeanConnectionScreen.tsx** - UI component for bank linking and data sync
- **index.ts** - Feature exports

## Prerequisites

### 1. Lean Technologies Sandbox Account
1. Go to https://dev.leantech.me
2. Create a developer account
3. Create a new application
4. Note down:
   - App Token
   - Client ID (from Integration tab)
   - Client Secret (from Integration tab)

### 2. Database Setup
- PostgreSQL 15+ installed and running
- Create database: `createdb space_money`

### 3. Python Environment
- Python 3.11+
- pip or uv for package management

### 4. Node.js Environment (for mobile)
- Node.js 18+
- npm or yarn

## Setup Instructions

### Backend Setup

#### Step 1: Install Dependencies
```bash
cd space-money/backend
pip install -r requirements.txt
```

#### Step 2: Configure Environment Variables
Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/space_money

# Lean Technologies Sandbox
LEAN_APP_TOKEN=your_app_token_from_lean_dashboard
LEAN_CLIENT_ID=your_client_id_from_lean_dashboard
LEAN_CLIENT_SECRET=your_client_secret_from_lean_dashboard
LEAN_BASE_URL=https://sandbox.leantech.me
LEAN_AUTH_URL=https://auth.leantech.me

# AWS S3 (for production, can use dummy values for sandbox testing)
AWS_REGION=me-central-1
AWS_ACCESS_KEY_ID=dummy_key_for_sandbox
AWS_SECRET_ACCESS_KEY=dummy_secret_for_sandbox
S3_BUCKET_NAME=space-money-sandbox

# Security
SECRET_KEY=your_secret_key_min_32_chars_long_random_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
ENVIRONMENT=development
DATA_DIR=./data
```

#### Step 3: Run Database Migrations
```bash
cd space-money/backend

# Initialize Alembic (if not done)
# alembic init alembic  # Skip this - already done

# Run migrations to create tables
alembic upgrade head
```

#### Step 4: Create Data Directory
```bash
mkdir -p data/raw data/metadata
```

#### Step 5: Start the Backend Server
```bash
# From backend/ directory
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Mobile Setup

#### Step 1: Install Dependencies
```bash
cd space-money/mobile
npm install
# or
yarn install
```

#### Step 2: Configure Environment
Create a `.env` file in the `mobile/` directory:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000
```

For testing on physical device, use your computer's IP address:
```env
EXPO_PUBLIC_API_URL=http://192.168.1.XXX:8000
```

#### Step 3: Start the Mobile App
```bash
# Using Expo
npx expo start

# Or React Native CLI
npx react-native start
```

## Testing the Implementation

### Test 1: Backend API Health Check

```bash
# Test basic health endpoint
curl http://localhost:8000/health

# Test Lean-specific health endpoint
curl http://localhost:8000/api/v1/lean/health
```

Expected response:
```json
{"status": "healthy"}
```

### Test 2: Run Integration Test Script

```bash
cd space-money/backend
python test_lean_integration.py
```

This script will:
1. Test OAuth authentication with Lean API
2. Create a test customer
3. Optionally test data extraction (requires valid entity_id)
4. Test individual API endpoints

**Expected Output:**
```
============================================================
Lean Technologies Integration Test Suite
============================================================

Configuration:
  Base URL: https://sandbox.leantech.me
  Auth URL: https://auth.leantech.me
  Data Directory: ./data

=== Testing Authentication ===
✓ Authentication successful
  Token: eyJhbGciOiJSUzI1Ni...

=== Testing Customer Creation ===
✓ Customer created successfully
  Customer ID: cust_xxxxxxxxxxxxx
  App User ID: test_user_1234567890
```

### Test 3: API Endpoints via cURL

#### Create a Customer
```bash
curl -X POST http://localhost:8000/api/v1/lean/customers \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_123"}'
```

Expected response:
```json
{
  "id": "uuid",
  "user_id": "test_user_123",
  "customer_id": "cust_xxxxx",
  "app_user_id": "user_test_user_123",
  "created_at": "2026-01-22T..."
}
```

#### Get Customer
```bash
curl http://localhost:8000/api/v1/lean/customers/test_user_123
```

#### Link an Entity (Sandbox Test)
```bash
curl -X POST http://localhost:8000/api/v1/lean/entities/link \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "YOUR_CUSTOMER_ID_FROM_ABOVE",
    "bank_identifier": "LEAN_MB1",
    "permissions": ["identity", "accounts", "balance", "transactions"]
  }'
```

Expected response:
```json
{
  "id": "uuid",
  "customer_id": "customer_uuid",
  "entity_id": "entity_cust_xxxxx_LEAN_MB1",
  "bank_identifier": "LEAN_MB1",
  "status": "ACTIVE",
  "permissions": ["identity", "accounts", "balance", "transactions"],
  "created_at": "2026-01-22T..."
}
```

#### Sync Data for Entity
```bash
curl -X POST http://localhost:8000/api/v1/lean/sync \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "YOUR_ENTITY_ID_FROM_ABOVE",
    "sync_types": ["identity", "accounts", "balance", "transactions"]
  }'
```

**Note:** In sandbox mode, this may fail if you haven't completed the actual bank linking flow through Lean Link SDK. The error is expected - the endpoint demonstrates the full flow.

### Test 4: Verify Data Files Created

After successful sync, check the data directory:

```bash
ls -la data/raw/
ls -la data/metadata/
```

You should see JSON files like:
- `identity_{entity_id}.json`
- `accounts_{entity_id}.json`
- `balance_{account_id}.json`
- `transactions_{account_id}.json`
- `sync_{entity_id}_{timestamp}.json` (in metadata/)

### Test 5: Mobile App Testing

1. Start the backend server (if not already running)
2. Start the mobile app
3. Navigate to the Lean Connection screen
4. Pass a test `userId` prop to the component
5. Observe:
   - Customer initialization
   - "Link Bank Account" button appears
   - Tap to link a bank (creates sandbox entity)
   - Tap "Sync Data" to fetch and save data
   - View synced accounts

### Test 6: Database Verification

Connect to PostgreSQL and verify data:

```sql
-- Check users (if any created)
SELECT * FROM transactions.users;

-- Check Lean customers
SELECT * FROM transactions.lean_customers;

-- Check linked entities
SELECT * FROM transactions.lean_entities;

-- Check accounts
SELECT * FROM transactions.lean_accounts;

-- Check sync logs
SELECT * FROM transactions.lean_sync_logs ORDER BY created_at DESC;
```

## Testing with Real Lean Sandbox Bank

For more realistic testing, use Lean's sandbox bank:

1. Go to https://sandbox.leantech.me
2. Use Lean's test credentials (from their documentation)
3. In production, you would integrate Lean Link SDK on mobile
4. The SDK provides the `entity_id` after successful linking
5. Use that `entity_id` to sync data

## Edge Cases Handled

### 1. Token Expiration
- Automatic token refresh when expired
- Tokens cached with expiry time
- 5-minute buffer before expiry

### 2. Retry Logic
- Exponential backoff for network errors
- Maximum 3 retry attempts
- Handles transient failures gracefully

### 3. Async Data Processing
- Some Lean endpoints return `PENDING` status
- Implementation logs status for manual retry
- In production, implement webhook listeners for async updates

### 4. Duplicate Prevention
- Checks for existing customers before creation
- Checks for existing entities before linking
- Returns existing records if found

### 5. Error Handling
- Specific exception types for different errors
- Proper HTTP status codes
- Detailed error messages in logs
- User-friendly error messages in API responses

## Known Limitations

### 1. Sandbox Limitations
- Mock data only, not real bank accounts
- Some endpoints may return empty responses
- Rate limiting may apply differently than production

### 2. Entity Linking
- Current implementation creates mock entities for sandbox testing
- Production requires Lean Link SDK integration on mobile/web
- SDK handles OAuth flow with actual banks

### 3. Webhook Support
- Not implemented in this version
- Recommended for production to handle async data updates
- Would require separate webhook endpoint and processing

### 4. Data Security
- JSON files stored locally for development
- Production should encrypt at rest
- Consider moving to S3 with SSE-KMS as per specs
- Implement file retention policies (7 days per specs)

## Design Decisions

### 1. Separate Schemas
- Used `transactions` schema for PII/sensitive data
- Follows Space Money data architecture rules
- `derived_data` schema would be used for analytics (not in this implementation)

### 2. Async/Await Pattern
- All I/O operations are async
- Better performance for concurrent requests
- Follows FastAPI best practices

### 3. Service Layer Pattern
- Business logic separated from routes
- `LeanClient` handles API communication
- `DataService` handles file operations
- Routes only handle HTTP concerns

### 4. Feature-Based Mobile Structure
- Self-contained feature folder
- Easy to maintain and test
- Follows Space Money mobile architecture

### 5. Error Handling Strategy
- Custom exception types for clarity
- Retry logic for transient errors
- Detailed logging for debugging
- User-friendly error messages

## Production Readiness Checklist

Before moving to production:

- [ ] Replace sandbox credentials with production credentials
- [ ] Integrate Lean Link SDK on mobile for real bank linking
- [ ] Implement webhook endpoints for async data updates
- [ ] Move data files to AWS S3 with SSE-KMS encryption
- [ ] Implement file retention policy (7-day purge)
- [ ] Add proper authentication/authorization middleware
- [ ] Implement rate limiting
- [ ] Add comprehensive logging and monitoring
- [ ] Set up error tracking (e.g., Sentry)
- [ ] Configure proper CORS origins
- [ ] Use mTLS certificates for production Lean API
- [ ] Implement data encryption at rest for database
- [ ] Add database backups
- [ ] Load testing for concurrent users
- [ ] Security audit of API endpoints
- [ ] DIFC compliance review

## Troubleshooting

### Issue: Authentication fails
**Solution:**
- Verify `LEAN_APP_TOKEN`, `LEAN_CLIENT_ID`, and `LEAN_CLIENT_SECRET` in `.env`
- Check credentials in Lean developer dashboard
- Ensure using correct environment (sandbox vs production)

### Issue: Database connection fails
**Solution:**
- Verify PostgreSQL is running: `pg_isready`
- Check `DATABASE_URL` in `.env`
- Ensure database exists: `createdb space_money`
- Verify connection string format: `postgresql+asyncpg://user:pass@host:port/db`

### Issue: Alembic migrations fail
**Solution:**
- Ensure database exists first
- Check if migrations already applied: `alembic current`
- Try downgrade and upgrade: `alembic downgrade base && alembic upgrade head`

### Issue: Data sync returns errors
**Solution:**
- Verify entity_id exists and is valid
- Check if entity was properly linked
- In sandbox, you may need to use Lean's test entities
- Check Lean API status page for outages

### Issue: Mobile app can't connect to backend
**Solution:**
- Ensure backend is running: `curl http://localhost:8000/health`
- Check `EXPO_PUBLIC_API_URL` in mobile `.env`
- If on physical device, use IP address instead of localhost
- Check firewall settings

### Issue: JSON files not created
**Solution:**
- Check `DATA_DIR` in backend `.env`
- Verify directory exists: `mkdir -p data/raw data/metadata`
- Check file permissions
- Review error logs in sync response

## Support and Documentation

- Lean Technologies Docs: https://docs.leantech.me
- Lean Authentication: https://docs.leantech.me/docs/authentication
- Lean Data API: https://docs.leantech.me/docs/getting-started-with-data
- FastAPI Docs: https://fastapi.tiangolo.com
- React Native: https://reactnative.dev

## Maintenance Notes

- Token caching reduces API calls
- Retry logic prevents transient failures
- Database indexes on foreign keys for query performance
- Regular cleanup of old sync logs recommended
- Monitor data directory size growth
