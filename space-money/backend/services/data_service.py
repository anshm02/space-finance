"""
Service for managing data extraction and storage with dual persistence.

Implements DIFC-compliant data storage:
- Local file persistence (existing behavior)
- Database persistence (new) with field-level encryption
- Audit logging for all sync operations
"""
import json
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


from services.lean_client import LeanClient, LeanAPIError
from config import get_settings
import logging

# Import new models
from models.user import UserProfile, DataIngestionConfig
from models.accounts import UserAccount, CreditCardDetails, AccountType, AccountStatus
from models.transactions import RawTransaction, TransactionType
from models.system import AuditLog, EventType, EntityType
from services.analytics_service import on_transaction_sync

logger = logging.getLogger(__name__)
settings = get_settings()


class DataService:
    """
    Service for extracting and storing Lean data with dual persistence.
    
    Data is saved to BOTH:
    1. Local JSON files (existing behavior)
    2. AWS RDS PostgreSQL database (new)
    """
    
    def __init__(self, lean_client: LeanClient, db: Optional[AsyncSession] = None):
        """
        Initialize data service.
        
        Args:
            lean_client: Lean API client
            db: Database session (optional, for dual persistence)
        """
        self.lean_client = lean_client
        self.db = db
        self.data_dir = Path(settings.data_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure data directories exist."""
        raw_dir = self.data_dir / "raw"
        metadata_dir = self.data_dir / "metadata"
        raw_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
    
    async def _save_json(self, data: Dict[str, Any], file_path: Path) -> str:
        """
        Save data to JSON file asynchronously.
        
        Args:
            data: Data to save
            file_path: Path to save file
        
        Returns:
            Absolute path to saved file
        """
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(data, indent=2, default=str))
        logger.info(f"Saved data to {file_path}")
        return str(file_path.absolute())
    
    async def _create_audit_log(
        self,
        event_type: EventType,
        user_id: Optional[uuid.UUID] = None,
        entity_type: Optional[EntityType] = None,
        entity_id: Optional[uuid.UUID] = None,
        ip_address: str = "127.0.0.1"
    ):
        """Create audit log entry for DIFC compliance."""
        if not self.db:
            return
        
        try:
            audit_log = AuditLog(
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id
            )
            audit_log.set_ip_address(ip_address)
            
            self.db.add(audit_log)
            await self.db.flush()
            logger.info(f"Created audit log: {event_type.value}")
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
    
    async def _upsert_accounts(
        self,
        user_id: uuid.UUID,
        accounts_data: List[Dict[str, Any]]
    ) -> List[uuid.UUID]:
        """
        Upsert account data to database.
        
        Args:
            user_id: User ID
            accounts_data: List of account data from Lean API
        
        Returns:
            List of account IDs
        """
        if not self.db:
            return []
        
        account_ids = []
        
        for account_data in accounts_data:
            try:
                lean_account_id = account_data.get("account_id")
                if not lean_account_id:
                    continue
                
                # Check if account exists by lean_account_id
                result = await self.db.execute(
                    select(UserAccount).where(UserAccount.lean_account_id == uuid.UUID(lean_account_id))
                )
                existing_account = result.scalar_one_or_none()
                
                # Map account type
                account_type_str = account_data.get("type", "CURRENT").upper()
                try:
                    account_type = AccountType[account_type_str]
                except KeyError:
                    account_type = AccountType.CURRENT
                
                if existing_account:
                    # Update existing account
                    existing_account.institution_name = "Lean Bank"  # Lean doesn't provide institution name
                    existing_account.account_name = account_data.get("name", "Account")
                    existing_account.account_type = account_type
                    existing_account.currency_code = account_data.get("currency_code", "AED")
                    existing_account.last_synced_at = datetime.utcnow()
                    
                    # Update encrypted fields if provided
                    if account_data.get("account_number"):
                        existing_account.account_number = account_data.get("account_number")
                    if account_data.get("iban"):
                        existing_account.iban = account_data.get("iban")
                    
                    account_ids.append(existing_account.account_id)
                    logger.info(f"Updated account {lean_account_id[:8]}... | {account_data.get('name')}")
                else:
                    # Create new account with encrypted PII fields
                    new_account = UserAccount(
                        user_id=user_id,
                        lean_account_id=uuid.UUID(lean_account_id),
                        institution_name="Lean Bank",  # Lean doesn't provide institution name  
                        account_name=account_data.get("name", "Account"),
                        account_number=account_data.get("account_number"),  # Will be encrypted
                        iban=account_data.get("iban"),  # Will be encrypted
                        account_type=account_type,
                        currency_code=account_data.get("currency_code", "AED"),
                        account_status=AccountStatus.ACTIVE,
                        linked_at=datetime.utcnow(),
                        last_synced_at=datetime.utcnow()
                    )
                    self.db.add(new_account)
                    await self.db.flush()
                    account_ids.append(new_account.account_id)
                    logger.info(f"Created account {lean_account_id[:8]}... | {account_data.get('name')} | {account_type.value}")
                
                # Handle credit card details if this is a CREDIT account
                if account_type == AccountType.CREDIT and account_data.get("credit"):
                    account_id = existing_account.account_id if existing_account else new_account.account_id
                    await self._upsert_credit_card_details(account_id, account_data["credit"])
            
            except Exception as e:
                logger.error(f"Failed to upsert account: {str(e)}")
                continue
        
        return account_ids
    
    async def _upsert_credit_card_details(
        self,
        account_id: uuid.UUID,
        credit_data: Dict[str, Any]
    ):
        """
        Upsert credit card details for CREDIT accounts.
        
        Args:
            account_id: Account ID
            credit_data: Credit card data from Lean API
        """
        if not self.db:
            return
        
        try:
            # Check if credit card details already exist
            result = await self.db.execute(
                select(CreditCardDetails).where(CreditCardDetails.account_id == account_id)
            )
            existing_details = result.scalar_one_or_none()
            
            # Parse credit card fields
            card_last_four = credit_data.get("card_number_last_four")
            credit_limit = credit_data.get("limit")
            due_date_str = credit_data.get("next_payment_due_date")
            due_amount = credit_data.get("next_payment_due_amount")
            
            # Parse due date if provided
            next_payment_due_date = None
            if due_date_str:
                try:
                    # Lean API sends dates as YYYY-MM-DD
                    next_payment_due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid date format for next_payment_due_date: {due_date_str}")
            
            if existing_details:
                # Update existing credit card details
                if card_last_four:
                    existing_details.card_last_four = card_last_four
                if credit_limit is not None:
                    existing_details.credit_limit = Decimal(str(credit_limit))
                existing_details.next_payment_due_date = next_payment_due_date
                if due_amount is not None:
                    existing_details.next_payment_due_amount = Decimal(str(due_amount))
                
                logger.info(f"Updated credit card details for account {account_id}")
            else:
                # Create new credit card details
                if credit_limit is None:
                    logger.warning(f"Credit limit is required but missing for account {account_id}")
                    return
                
                new_details = CreditCardDetails(
                    account_id=account_id,
                    card_last_four=card_last_four,  # Will be encrypted
                    credit_limit=Decimal(str(credit_limit)),
                    next_payment_due_date=next_payment_due_date,
                    next_payment_due_amount=Decimal(str(due_amount)) if due_amount is not None else None
                )
                self.db.add(new_details)
                logger.info(f"Created credit card details for account {account_id} | Limit: {credit_limit}")
            
            await self.db.flush()
        
        except Exception as e:
            logger.error(f"Failed to upsert credit card details for {account_id}: {str(e)}")
    
    async def _upsert_balance(
        self,
        account_id: uuid.UUID,
        balance_data: Dict[str, Any]
    ):
        """
        Update balance in user_accounts table.
        
        Args:
            account_id: Account ID
            balance_data: Balance data from Lean API (full response)
        """
        if not self.db:
            return
        
        try:
            payload = balance_data.get("payload", {})
            balance_amount = payload.get("balance")
            
            if balance_amount is None:
                logger.warning(f"No balance found in payload for account {account_id}")
                return
            
            # Update balance directly in user_accounts table
            result = await self.db.execute(
                select(UserAccount).where(UserAccount.account_id == account_id)
            )
            account = result.scalar_one_or_none()
            
            if account:
                account.current_balance = Decimal(str(balance_amount))
                account.balance_updated_at = datetime.utcnow()
                await self.db.flush()
                logger.info(f"Balance updated: {account_id} | {balance_amount} {payload.get('currency_code', 'AED')}")
            else:
                logger.warning(f"Account {account_id} not found for balance update")
        
        except Exception as e:
            logger.error(f"Failed to update balance for {account_id}: {str(e)}")
    
    async def _upsert_transactions(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        transactions_data: List[Dict[str, Any]]
    ):
        """
        Upsert transactions using bulk operations for performance.
        
        Args:
            user_id: User ID
            account_id: Account ID
            transactions_data: List of transaction data from Lean API
        """
        if not self.db or not transactions_data:
            return
        
        try:
            # 1. Get all Lean Transaction IDs from the input data
            lean_txn_ids = [
                uuid.UUID(txn.get("id")) 
                for txn in transactions_data 
                if txn.get("id")
            ]
            
            if not lean_txn_ids:
                return

            # 2. Find existing transactions in one query
            # Optimizes performance by avoiding N queries inside loop
            existing_txns_result = await self.db.execute(
                select(RawTransaction.lean_transaction_id).where(
                    RawTransaction.lean_transaction_id.in_(lean_txn_ids)
                )
            )
            existing_ids = set(existing_txns_result.scalars().all())
            
            # 3. Filter and Prepare New Transactions
            new_transactions = []
            
            for txn_data in transactions_data:
                lean_id_str = txn_data.get("id")
                if not lean_id_str:
                    continue
                    
                lean_uuid = uuid.UUID(lean_id_str)
                
                # Skip if already exists
                if lean_uuid in existing_ids:
                    continue
                
                # Extract amount and determine transaction type
                amount = Decimal(str(txn_data.get("amount", 0)))
                # Negative amount = DEBIT (outgoing), Positive = CREDIT (incoming)
                txn_type = TransactionType.DEBIT if amount < 0 else TransactionType.CREDIT
                
                # Parse timestamp and date
                txn_timestamp_str = txn_data.get("timestamp")
                txn_timestamp = None
                txn_date = date.today()
                
                if txn_timestamp_str:
                    try:
                        # Parse full ISO timestamp
                        txn_timestamp = datetime.fromisoformat(txn_timestamp_str.replace('Z', '+00:00'))
                        txn_date = txn_timestamp.date()
                    except ValueError:
                        logger.warning(f"Invalid timestamp format: {txn_timestamp_str}")
                
                insights = txn_data.get("insights", {})
                
                new_txn = RawTransaction(
                    user_id=user_id,
                    account_id=account_id,
                    lean_transaction_id=lean_uuid,
                    transaction_date=txn_date,
                    transaction_timestamp=txn_timestamp,  # Store full timestamp
                    amount=abs(amount),
                    currency_code=txn_data.get("currency_code", "AED"),
                    # Description - will be encrypted
                    description=txn_data.get("description", ""),
                    # Cleansed description
                    description_cleansed=str(insights.get("description_cleansed", ""))[:255] if insights.get("description_cleansed") else None,
                    transaction_type=txn_type,
                    is_pending=txn_data.get("pending", False),
                    transaction_reference=str(txn_data.get("transaction_reference", ""))[:100] if txn_data.get("transaction_reference") else None,
                    # Lean Insights
                    lean_insights_category=str(insights.get("category", ""))[:50] if insights.get("category") else None,
                    lean_insights_type=str(insights.get("type", ""))[:50] if insights.get("type") else None,
                    lean_category_confidence=Decimal(str(insights.get("category_confidence", 0))) if insights.get("category_confidence") else None
                )
                new_transactions.append(new_txn)
            
            # 4. Bulk Insert
            if new_transactions:
                self.db.add_all(new_transactions)
                await self.db.flush()
                logger.info(f"Bulk inserted {len(new_transactions)} transactions for account {account_id}")
            else:
                logger.info(f"No new transactions to insert for account {account_id}")
                
        except Exception as e:
            logger.error(f"Failed to upsert transactions: {str(e)}")
            # Don't raise, allow sync to continue partial success
    
    async def sync_identity(self, entity_id: str) -> Dict[str, Any]:
        """
        Sync identity data for an entity.
        
        Saves to both file and database (dual persistence).
        
        Args:
            entity_id: Entity ID from Lean
        
        Returns:
            Dict with status and file path
        """
        try:
            data = await self.lean_client.get_identity(entity_id)
            file_path = self.data_dir / "raw" / f"identity_{entity_id}.json"
            saved_path = await self._save_json(data, file_path)
            
            # Database persistence would happen here if we had user_id mapping
            # For now, identity data is primarily in files
            
            return {
                "status": "success",
                "sync_type": "identity",
                "file_path": saved_path,
                "timestamp": datetime.utcnow().isoformat()
            }
        except LeanAPIError as e:
            logger.error(f"Failed to sync identity for {entity_id}: {str(e)}")
            return {
                "status": "error",
                "sync_type": "identity",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def sync_accounts(
        self,
        entity_id: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Sync accounts data for an entity.
        
        Saves to both file and database (dual persistence).
        
        Args:
            entity_id: Entity ID from Lean
            user_id: User ID for database persistence
        
        Returns:
            Dict with status, file path, and account IDs
        """
        try:
            # Fetch from Lean API
            data = await self.lean_client.get_accounts(entity_id)
            
            # Save to file (existing behavior)
            file_path = self.data_dir / "raw" / f"accounts_{entity_id}.json"
            saved_path = await self._save_json(data, file_path)
            
            # Extract accounts from nested payload structure
            payload = data.get("payload", {})
            accounts = payload.get("accounts", [])
            account_ids = [acc.get("account_id") for acc in accounts if acc.get("account_id")]
            
            # Save to database (new behavior)
            db_account_ids = []
            if self.db and user_id:
                db_account_ids = await self._upsert_accounts(user_id, accounts)
                await self._create_audit_log(
                    event_type=EventType.LEAN_SYNC,
                    user_id=user_id,
                    entity_type=EntityType.ACCOUNT
                )
            
            logger.info(f"Extracted {len(account_ids)} account IDs from entity {entity_id}")
            
            return {
                "status": "success",
                "sync_type": "accounts",
                "file_path": saved_path,
                "account_ids": account_ids,
                "db_account_ids": [str(aid) for aid in db_account_ids],
                "count": len(account_ids),
                "timestamp": datetime.utcnow().isoformat()
            }
        except LeanAPIError as e:
            logger.error(f"Failed to sync accounts for {entity_id}: {str(e)}")
            return {
                "status": "error",
                "sync_type": "accounts",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def sync_balance(
        self,
        account_id: str,
        entity_id: str,
        db_account_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Sync balance data for an account.
        
        Saves to both file and database (dual persistence).
        
        Args:
            account_id: Lean Account ID
            entity_id: Entity ID from Lean
            db_account_id: Database account ID for persistence
        
        Returns:
            Dict with status and file path
        """
        try:
            # Fetch from Lean API
            data = await self.lean_client.get_balance(account_id, entity_id)
            
            # Save to file (existing behavior)
            file_path = self.data_dir / "raw" / f"balance_{account_id}.json"
            saved_path = await self._save_json(data, file_path)
            
            # Extract balance info for return
            payload = data.get("payload", {})
            balance_info = {
                "balance": payload.get("balance"),
                "currency_code": payload.get("currency_code"),
                "account_type": payload.get("account_type")
            }
            
            # Save to database (new behavior)
            if self.db and db_account_id:
                await self._upsert_balance(db_account_id, data)
            
            return {
                "status": "success",
                "sync_type": "balance",
                "file_path": saved_path,
                "balance_info": balance_info,
                "timestamp": datetime.utcnow().isoformat()
            }
        except LeanAPIError as e:
            logger.error(f"Failed to sync balance for {account_id}: {str(e)}")
            return {
                "status": "error",
                "sync_type": "balance",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def sync_transactions(
        self,
        account_id: str,
        entity_id: str,
        user_id: Optional[uuid.UUID] = None,
        db_account_id: Optional[uuid.UUID] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync transactions data for an account.
        
        Saves to both file and database (dual persistence).
        
        Args:
            account_id: Lean Account ID
            entity_id: Entity ID from Lean
            user_id: User ID for database persistence
            db_account_id: Database account ID for persistence
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            Dict with status and file path
        """
        try:
            # Fetch from Lean API
            data = await self.lean_client.get_transactions(account_id, entity_id, from_date, to_date)
            
            # Save to file (existing behavior)
            file_path = self.data_dir / "raw" / f"transactions_{account_id}.json"
            saved_path = await self._save_json(data, file_path)
            
            # Extract transactions from nested payload structure
            payload = data.get("payload", {})
            transactions = payload.get("transactions", [])
            transaction_count = len(transactions)
            
            # Save to database (new behavior)
            if self.db and user_id and db_account_id:
                await self._upsert_transactions(user_id, db_account_id, transactions)
                await self._create_audit_log(
                    event_type=EventType.LEAN_SYNC,
                    user_id=user_id,
                    entity_type=EntityType.TRANSACTION
                )
            
            logger.info(f"Extracted {transaction_count} transactions for account {account_id}")
            
            return {
                "status": "success",
                "sync_type": "transactions",
                "file_path": saved_path,
                "count": transaction_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        except LeanAPIError as e:
            logger.error(f"Failed to sync transactions for {account_id}: {str(e)}")
            return {
                "status": "error",
                "sync_type": "transactions",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def sync_all_for_entity(
        self,
        entity_id: str,
        user_id: Optional[uuid.UUID] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync all data types for an entity with dual persistence.
        
        Args:
            entity_id: Entity ID from Lean
            user_id: User ID for database persistence
            from_date: Start date for transactions (YYYY-MM-DD)
            to_date: End date for transactions (YYYY-MM-DD)
        
        Returns:
            Dict with all sync results
        """
        results = {
            "entity_id": entity_id,
            "sync_timestamp": datetime.utcnow().isoformat(),
            "results": {},
            "files_created": []
        }
        
        # Sync identity
        identity_result = await self.sync_identity(entity_id)
        results["results"]["identity"] = identity_result
        if identity_result["status"] == "success":
            results["files_created"].append(identity_result["file_path"])
        
        # Sync accounts
        accounts_result = await self.sync_accounts(entity_id, user_id)
        results["results"]["accounts"] = accounts_result
        if accounts_result["status"] == "success":
            results["files_created"].append(accounts_result["file_path"])
            account_ids = accounts_result.get("account_ids", [])
            db_account_ids = accounts_result.get("db_account_ids", [])
            
            # Create mapping of lean_account_id to db_account_id
            account_id_map = {}
            if len(account_ids) == len(db_account_ids):
                account_id_map = dict(zip(account_ids, db_account_ids))
            
            # Sync balance and transactions for each account
            balance_results = []
            transaction_results = []
            
            for idx, account_id in enumerate(account_ids):
                db_account_id = uuid.UUID(account_id_map.get(account_id)) if account_id in account_id_map else None
                
                # Sync balance
                balance_result = await self.sync_balance(account_id, entity_id, db_account_id)
                balance_results.append(balance_result)
                if balance_result["status"] == "success":
                    results["files_created"].append(balance_result["file_path"])
                
                # Sync transactions
                transaction_result = await self.sync_transactions(
                    account_id, entity_id, user_id, db_account_id, from_date, to_date
                )
                transaction_results.append(transaction_result)
                if transaction_result["status"] == "success":
                    results["files_created"].append(transaction_result["file_path"])
            
            results["results"]["balances"] = balance_results
            results["results"]["transactions"] = transaction_results
        
        # Save metadata
        metadata_path = self.data_dir / "metadata" / f"sync_{entity_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        await self._save_json(results, metadata_path)
        results["files_created"].append(str(metadata_path.absolute()))
        
        # Commit database changes if we have a session
        if self.db:
            try:
                await self.db.commit()
                logger.info(f"Committed database changes for entity {entity_id}")
                
                # Trigger full analytics pipeline
                if user_id:
                    try:
                        logger.info(f"Triggering analytics pipeline for user {user_id}...")
                        pipeline_result = await on_transaction_sync(self.db, str(user_id))
                        if pipeline_result.get("success"):
                            logger.info(f"Analytics pipeline completed: score={pipeline_result.get('composite_score')}")
                        else:
                            logger.warning(f"Analytics pipeline completed with errors: {pipeline_result.get('error')}")
                    except Exception as e:
                        logger.error(f"Failed to run analytics pipeline: {str(e)}")
                        # Don't fail the sync request, just log error
            except Exception as e:
                logger.error(f"Failed to commit database changes: {str(e)}")
                await self.db.rollback()
        
        return results
