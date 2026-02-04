# Space Money Database - Quick Reference

## 🚀 Quick Start (5 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate Encryption Key
```bash
python generate_encryption_key.py
```
Copy the output to your `.env` file.

### 3. Configure `.env`
```env
DATABASE_URL=postgresql+asyncpg://USER:PASS@ENDPOINT:5432/spacemoney-db-dev?ssl=require
ENCRYPTION_KEY=your-generated-key-here
AWS_REGION=me-central-1
```

### 4. Run Migration
```bash
alembic upgrade head
```

### 5. Verify Setup
```bash
python test_db_connection.py
python verify_data_upsert.py
```

## 📊 Database Schema

**4 Schemas:**
- `user` - User profiles, demographics, consent, data config
- `accounts` - Bank accounts, balances, credit cards
- `transactions` - Transaction history with Lean Insights
- `system` - Audit logs for DIFC compliance

**9 Tables Total**

## 🔒 Encrypted Fields (AES-256)

- `user.user_profiles.email`
- `user.data_ingestion_config.lean_access_token`
- `accounts.user_accounts.account_number`
- `accounts.user_accounts.iban`
- `accounts.credit_card_details.card_last_four`
- `transactions.raw_transactions.description`

## 🔐 Hashed Fields (SHA-256)

- `user.consent_records.ip_address`
- `system.audit_log.ip_address`

## 📝 Common Queries

### Get User Accounts
```sql
SELECT account_id, institution_name, account_type, currency_code
FROM accounts.user_accounts
WHERE user_id = ?;
```

### Get Recent Transactions
```sql
SELECT transaction_date, amount, description_cleansed, transaction_type
FROM transactions.raw_transactions
WHERE account_id = ?
ORDER BY transaction_date DESC
LIMIT 20;
```

### Check Audit Logs
```sql
SELECT timestamp, event_type, entity_type
FROM system.audit_log
ORDER BY timestamp DESC
LIMIT 50;
```

## 🧪 Testing

```bash
# Test connection
python test_db_connection.py

# Verify dual persistence
python verify_data_upsert.py

# Generate new encryption key
python generate_encryption_key.py
```

## 🔄 Dual Persistence

Data is now saved to **BOTH**:
1. ✅ **Local JSON files** (existing) → `./data/raw/`
2. ✅ **AWS RDS Database** (new) → All schemas

## 📁 Helper Scripts

| Script | Purpose |
|--------|---------|
| `generate_encryption_key.py` | Generate AES-256 key |
| `test_db_connection.py` | Test AWS RDS connection |
| `verify_data_upsert.py` | Verify dual persistence |

## 📖 Full Documentation

See [`DATABASE_SETUP.md`](./DATABASE_SETUP.md) for complete guide.

## ⚠️ Important Notes

1. **Backup encryption key** - If lost, encrypted data cannot be recovered
2. **AWS RDS SSL required** - Connection string must include `?ssl=require`
3. **Run migrations** - Use `alembic upgrade head` to create schemas
4. **DIFC compliant** - Encryption at rest, in transit, field-level, and audit logging

## 🎯 Next Steps

1. Update `.env` with AWS RDS credentials
2. Generate encryption key
3. Run `alembic upgrade head`
4. Test with `python test_db_connection.py`
5. Trigger Lean sync to populate database
6. Verify with `python verify_data_upsert.py`
