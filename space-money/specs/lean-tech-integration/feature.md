# Feature: Lean Technologies Sandbox Integration

## Objective
Integrate Lean Technologies Open Finance API in sandbox mode to authenticate users and extract their financial data to local JSON files.

## Resources
- Lean Technologies Documentation: https://docs.leantech.me
- Authentication Guide: https://docs.leantech.me/docs/authentication
- Data API Reference: https://docs.leantech.me/docs/getting-started-with-data
- Sandbox Environment: https://sandbox.leantech.me

## Implementation Requirements

### 1. Environment Setup
Set up environment variables for Lean Technologies sandbox credentials:
- `LEAN_APP_TOKEN` - Application token from dev.leantech.me dashboard
- `LEAN_CLIENT_ID` - Application ID from Integration tab
- `LEAN_CLIENT_SECRET` - Client secret from Integration tab

### 2. OAuth Authentication Flow
Implement OAuth 2.0 client credentials flow to obtain access tokens:
- Endpoint: `POST https://auth.leantech.me/oauth2/token` (adjust domain for region)
- Request body (application/x-www-form-urlencoded):
  - `client_id`: LEAN_CLIENT_ID
  - `client_secret`: LEAN_CLIENT_SECRET  
  - `grant_type`: "client_credentials"
  - `scope`: "api" for backend API access
- Store the returned JWT access token for API calls

### 3. Customer Creation
Create a customer entity to associate bank connections:
- Endpoint: `POST https://sandbox.leantech.me/customers/v1`
- Headers:
  - `Authorization`: Bearer {JWT_TOKEN}
  - `Content-Type`: application/json
- Request body:
  - `app_user_id`: Unique identifier for the user in your system
- Save the returned `customer_id` for subsequent operations

### 4. Entity Connection (Bank Account Linking)
Implement bank account connection flow using Lean's LinkSDK or API:
- Initialize connection with sandbox bank (use test credentials from Lean docs)
- Required permissions: `["identity", "accounts", "balance", "transactions"]`
- Connection creates an `entity_id` representing the linked bank account
- For testing, use sandbox mode: `sandbox: true`
- Save the returned `entity_id`

### 5. Data Extraction to JSON Files
Once entity is connected and data is ready, fetch and save data to JSON files in `/data` directory:

**5.1 Identity Data**
- Endpoint: `GET https://sandbox.leantech.me/data/v2/identity?entity_id={entity_id}`
- Headers: `Authorization: Bearer {JWT_TOKEN}`
- Save to: `data/identity_{entity_id}.json`
- Contains: User identity information from the bank

**5.2 Accounts Data**  
- Endpoint: `GET https://sandbox.leantech.me/data/v2/accounts?entity_id={entity_id}`
- Headers: `Authorization: Bearer {JWT_TOKEN}`
- Save to: `data/accounts_{entity_id}.json`
- Contains: List of bank accounts with account_id for each account

**5.3 Balance Data**
- Endpoint: `GET https://sandbox.leantech.me/data/v2/balance?account_id={account_id}`
- Headers: `Authorization: Bearer {JWT_TOKEN}`
- Save to: `data/balance_{account_id}.json`
- Call for each account_id retrieved from accounts endpoint
- Contains: Current balance and available balance

**5.4 Transactions Data**
- Endpoint: `GET https://sandbox.leantech.me/data/v2/transactions?account_id={account_id}`
- Headers: `Authorization: Bearer {JWT_TOKEN}`
- Optional query params:
  - `from`: Start date (YYYY-MM-DD)
  - `to`: End date (YYYY-MM-DD)
- Save to: `data/transactions_{account_id}.json`
- Call for each account_id retrieved from accounts endpoint
- Contains: Transaction history with categories and amounts

### 6. Error Handling
Handle common scenarios:
- Token expiration: Refresh JWT token when receiving 401 responses
- Async data processing: Some endpoints return `PENDING` status - implement retry logic
- Rate limiting: Respect API rate limits
- Connection failures: Log errors and retry with exponential backoff

### 7. File Organization
Create directory structure:
```
/data
  /raw
    - identity_{entity_id}.json
    - accounts_{entity_id}.json
    - balance_{account_id}.json
    - transactions_{account_id}.json
  /metadata
    - customer_info.json (customer_id, entity_id mappings)
    - last_sync.json (timestamp of last successful sync)
```

## Testing with Sandbox
Use Lean's sandbox environment for testing:
- No need for mTLS certificates in sandbox
- Use test bank credentials provided in Lean documentation
- Mock data is returned for all API endpoints
- Test the full flow end-to-end before moving to production

## Success Criteria
- Successfully authenticate with Lean sandbox API
- Create test customer
- Link test bank account (entity)
- Extract all data types (identity, accounts, balances, transactions) to JSON files
- Data files are properly structured and readable
- Error handling works for common failure scenarios
