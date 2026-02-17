"""Lean Technologies API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from database import get_db
from models import LeanCustomer, LeanEntity, LeanAccount, LeanSyncLog
from schemas import (
    LeanCustomerCreate,
    LeanCustomerResponse,
    EntityLinkRequest,
    EntityLinkResponse,
    DataSyncRequest,
    DataSyncResponse,
    LeanAccountResponse
)
from services.lean_client import LeanClient, LeanAPIError
from services.data_service import DataService

router = APIRouter(prefix="/api/v1/lean", tags=["lean"])
logger = logging.getLogger(__name__)


async def _run_pipeline_bg(user_id: str):
    """Run analytics pipeline in background after sync."""
    from database import AsyncSessionLocal
    from services.analytics_service import run_health_checkup_pipeline
    async with AsyncSessionLocal() as session:
        try:
            result = await run_health_checkup_pipeline(session, user_id)
            await session.commit()
            logger.info(f"Analytics pipeline completed for {user_id}: {result}")
        except Exception as e:
            logger.error(f"Analytics pipeline failed for {user_id}: {e}")


async def get_lean_client():
    """Dependency for getting Lean client."""
    async with LeanClient() as client:
        yield client


@router.post("/customers", response_model=LeanCustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    request: LeanCustomerCreate,
    db: AsyncSession = Depends(get_db),
    lean_client: LeanClient = Depends(get_lean_client)
):
    """
    Create a Lean customer for a user.
    
    This creates a customer entity in Lean that can be used to link bank accounts.
    """
    try:
        # Check if customer already exists for this user
        result = await db.execute(
            select(LeanCustomer).where(LeanCustomer.user_id == request.user_id)
        )
        existing_customer = result.scalar_one_or_none()
        
        if existing_customer:
            logger.info(f"Customer already exists for user: {request.user_id}")
            return existing_customer
        
        # Check if user exists in DIFC schema, if not create it
        from models.user import UserProfile, AccountStatus
        import uuid
        
        # Try to find user profile by username (using user_id as username)
        result = await db.execute(
            select(UserProfile).where(UserProfile.username == request.user_id)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            # Create new DIFC UserProfile
            new_uuid = uuid.uuid4()
            user_profile = UserProfile(
                user_id=new_uuid,
                username=request.user_id,
                email=f"{request.user_id}@temp.spacemoney.app",  # Will be encrypted
                password_hash="temp_migrated",
                country_code="AE",
                account_status=AccountStatus.ACTIVE
            )
            db.add(user_profile)
            await db.flush()
            logger.info(f"Created new DIFC UserProfile: {new_uuid}")
        
        # Check if legacy user exists (for FK constraints in legacy tables)
        from models import User
        result = await db.execute(
            select(User).where(User.id == request.user_id)
        )
        legacy_user = result.scalar_one_or_none()
        
        if not legacy_user:
            # Create basic user record for legacy FK constraint
            legacy_user = User(
                id=request.user_id,
                email=f"{request.user_id}@temp.spacemoney.app",
                hashed_password="temp_will_be_set_later",
                full_name=f"User {request.user_id}"
            )
            db.add(legacy_user)
            await db.flush()
        
        # Create customer in Lean
        app_user_id = f"user_{request.user_id}"
        lean_response = await lean_client.create_customer(app_user_id)
        
        # Save to database (Legacy LeanCustomer table)
        customer = LeanCustomer(
            user_id=request.user_id,
            customer_id=lean_response["customer_id"],
            app_user_id=app_user_id
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        
        logger.info(f"Created Lean customer: {customer.customer_id}")
        return customer
        
    except LeanAPIError as e:
        logger.error(f"Lean API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Lean API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating customer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer"
        )


@router.get("/customers/{user_id}", response_model=LeanCustomerResponse)
async def get_customer(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get Lean customer for a user."""
    result = await db.execute(
        select(LeanCustomer).where(LeanCustomer.user_id == user_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.get("/customers/{customer_id}/entities-from-lean")
async def get_customer_entities_from_lean(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    lean_client: LeanClient = Depends(get_lean_client)
):
    """
    Fetch entities from Lean API for a customer.
    
    This retrieves the actual entities from Lean after a bank connection.
    """
    try:
        # Verify customer exists in our database
        result = await db.execute(
            select(LeanCustomer).where(LeanCustomer.customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Fetch entities from Lean API (returns list directly)
        entities = await lean_client.get_customer_entities(customer_id)
        
        # Return in format expected by mobile app
        return {"entities": entities}
        
    except LeanAPIError as e:
        logger.error(f"Failed to fetch entities from Lean: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Lean API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching entities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch entities"
        )


@router.post("/entities/link", response_model=EntityLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_entity(
    request: EntityLinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Save entity after Lean Link SDK connection.
    
    The entity_id comes from Lean Link SDK after user successfully links their bank.
    """
    try:
        # Verify customer exists
        result = await db.execute(
            select(LeanCustomer).where(LeanCustomer.id == request.customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Use entity_id from request (provided by Link SDK or Lean API)
        if request.entity_id:
            entity_id = request.entity_id
            logger.info(f"Received entity_id: {entity_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entity_id is required from Lean Link SDK"
            )
        
        # Check if entity already exists
        result = await db.execute(
            select(LeanEntity).where(LeanEntity.entity_id == entity_id)
        )
        existing_entity = result.scalar_one_or_none()
        
        if existing_entity:
            logger.info(f"Entity already exists: {entity_id}")
            return existing_entity
        
        # Create entity record
        entity = LeanEntity(
            customer_id=request.customer_id,
            entity_id=entity_id,
            bank_identifier=request.bank_identifier,
            status="ACTIVE",
            permissions=request.permissions
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
        
        logger.info(f"Linked entity: {entity.entity_id}")
        return entity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking entity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link entity"
        )


@router.get("/entities/{customer_id}", response_model=List[EntityLinkResponse])
async def get_entities(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all linked entities for a customer."""
    result = await db.execute(
        select(LeanEntity).where(LeanEntity.customer_id == customer_id)
    )
    entities = result.scalars().all()
    
    return entities


@router.post("/sync", response_model=DataSyncResponse)
async def sync_data(
    request: DataSyncRequest,
    db: AsyncSession = Depends(get_db),
    lean_client: LeanClient = Depends(get_lean_client)
):
    """
    Sync data from Lean for an entity.
    
    This fetches identity, accounts, balances, and transactions data
    and saves them to BOTH JSON files AND database (dual persistence).
    """
    try:
        # Verify entity exists in old schema (for backward compatibility)
        result = await db.execute(
            select(LeanEntity).where(LeanEntity.entity_id == request.entity_id)
        )
        entity = result.scalar_one_or_none()
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entity not found"
            )
        
        # Get user_id from entity's customer
        result = await db.execute(
            select(LeanCustomer).where(LeanCustomer.id == entity.customer_id)
        )
        customer = result.scalar_one_or_none()
        
        # Resolve to DIFC UserProfile UUID
        db_user_id = None
        if customer:
            from models.user import UserProfile, AccountStatus
            import uuid
            
            # Find UserProfile by username (matches customer.user_id)
            result = await db.execute(
                select(UserProfile).where(UserProfile.username == customer.user_id)
            )
            user_profile = result.scalar_one_or_none()
            
            if not user_profile:
                # Create profile if missing (auto-migration)
                new_uuid = uuid.uuid4()
                user_profile = UserProfile(
                    user_id=new_uuid,
                    username=customer.user_id,
                    email=f"{customer.user_id}@temp.spacemoney.app",  # Encrypted
                    password_hash="temp_migrated",
                    country_code="AE",
                    account_status=AccountStatus.ACTIVE
                )
                db.add(user_profile)
                await db.flush()
                logger.info(f"Created missing DIFC UserProfile for sync: {new_uuid}")
            
            db_user_id = user_profile.user_id
        
        # Sync data using data service with dual persistence
        data_service = DataService(lean_client, db)
        sync_results = await data_service.sync_all_for_entity(
            request.entity_id,
            user_id=db_user_id,  # Pass DIFC UserProfile UUID
            from_date=request.from_date,
            to_date=request.to_date
        )
        
        # Update entity last sync time
        from datetime import datetime
        entity.last_synced_at = datetime.utcnow()
        
        # Backward compatibility: Save accounts to old schema
        accounts_result = sync_results["results"].get("accounts", {})
        if accounts_result.get("status") == "success":
            for account_id in accounts_result.get("account_ids", []):
                # Check if account already exists
                result = await db.execute(
                    select(LeanAccount).where(LeanAccount.account_id == account_id)
                )
                existing_account = result.scalar_one_or_none()
                
                if not existing_account:
                    account = LeanAccount(
                        entity_id=entity.id,
                        account_id=account_id
                    )
                    db.add(account)
        
        # Log sync operation
        for sync_type, result_data in sync_results["results"].items():
            if isinstance(result_data, list):
                for item in result_data:
                    log = LeanSyncLog(
                        entity_id=entity.id,
                        sync_type=sync_type,
                        status=item.get("status", "unknown"),
                        file_path=item.get("file_path"),
                        error_message=item.get("error")
                    )
                    db.add(log)
            else:
                log = LeanSyncLog(
                    entity_id=entity.id,
                    sync_type=sync_type,
                    status=result_data.get("status", "unknown"),
                    file_path=result_data.get("file_path"),
                    error_message=result_data.get("error")
                )
                db.add(log)
        
        # Save balance history to old schema for backward compatibility
        from models import BalanceHistory
        balance_results = sync_results["results"].get("balances", [])
        for balance_result in balance_results:
            if balance_result.get("status") == "success":
                balance_info = balance_result.get("balance_info", {})
                # Extract account_id from file path (balance_{account_id}.json)
                file_path = balance_result.get("file_path", "")
                account_id = file_path.split("balance_")[-1].replace(".json", "") if "balance_" in file_path else None
                
                if account_id and balance_info.get("balance") is not None:
                    balance_history = BalanceHistory(
                        account_id=account_id,
                        entity_id=entity.id,
                        balance=str(balance_info.get("balance")),
                        currency_code=balance_info.get("currency_code"),
                        account_type=balance_info.get("account_type")
                    )
                    db.add(balance_history)
        
        await db.commit()
        
        # Trigger analytics pipeline in background (non-blocking)
        import asyncio
        if db_user_id:
            asyncio.create_task(_run_pipeline_bg(str(db_user_id)))
        
        return DataSyncResponse(
            entity_id=request.entity_id,
            sync_results=sync_results["results"],
            files_created=sync_results["files_created"]
        )
        
    except HTTPException:
        raise
    except LeanAPIError as e:
        logger.error(f"Lean API error during sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Lean API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error syncing data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync data"
        )


@router.get("/accounts/{entity_id}", response_model=List[LeanAccountResponse])
async def get_accounts(
    entity_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all accounts for an entity."""
    # Get entity
    result = await db.execute(
        select(LeanEntity).where(LeanEntity.entity_id == entity_id)
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )
    
    # Get accounts
    result = await db.execute(
        select(LeanAccount).where(LeanAccount.entity_id == entity.id)
    )
    accounts = result.scalars().all()
    
    return accounts


@router.post("/customer-token/{customer_id}")
async def get_customer_access_token(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer-specific access token for Lean Link SDK.
    """
    try:
        # Verify customer exists
        result = await db.execute(
            select(LeanCustomer).where(LeanCustomer.customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        from config import get_settings
        import httpx
        settings = get_settings()
        
        # Get customer-specific token from Lean
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.lean_auth_url}/oauth2/token",
                data={
                    "client_id": settings.lean_client_id,
                    "client_secret": settings.lean_client_secret,
                    "grant_type": "client_credentials",
                    "scope": f"customer.{customer_id}"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "expires_in": data.get("expires_in", 3600)
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get customer token: {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get customer token: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error getting customer token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get customer token"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "lean-integration"}
