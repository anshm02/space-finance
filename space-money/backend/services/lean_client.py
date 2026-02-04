"""Lean Technologies API client."""
import httpx
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class LeanAPIError(Exception):
    """Base exception for Lean API errors."""
    pass


class LeanAuthError(LeanAPIError):
    """Authentication error with Lean API."""
    pass


class LeanClient:
    """Client for interacting with Lean Technologies API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with app token."""
        return {
            "Authorization": f'Bearer {self.settings.lean_app_token}',
            "Content-Type": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def create_customer(self, app_user_id: str) -> Dict[str, Any]:
        """
        Create a Lean customer entity.
        
        Args:
            app_user_id: Unique identifier for user in your system
        
        Returns:
            Customer data including customer_id
        
        Raises:
            LeanAPIError: If customer creation fails
        """
        try:
            headers = self._get_headers()
            url = f"{self.settings.lean_base_url}/customers/v1"
            logger.info(f"Making request to: {url}")
            logger.info(f"Headers: {dict((k, v[:20] + '...' if len(v) > 20 else v) for k, v in headers.items())}")
            
            response = await self.client.post(
                url,
                json={"app_user_id": app_user_id},
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Created Lean customer: {data.get('customer_id')}")
            return data
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Customer creation failed: {e.response.status_code}")
            logger.error(f"Response body: {error_detail}")
            logger.error(f"Request headers: {dict((k, v[:20] + '...' if len(v) > 20 else v) for k, v in headers.items())}")
            raise LeanAPIError(f"Failed to create customer: {error_detail if error_detail else 'No error details provided'}")
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {str(e)}")
            raise LeanAPIError(f"Error creating customer: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def get_customer_entities(self, customer_id: str) -> list:
        """
        Get all entities for a customer.
        
        Args:
            customer_id: Customer ID from Lean
        
        Returns:
            List of entities for the customer
        
        Raises:
            LeanAPIError: If request fails
        """
        try:
            headers = self._get_headers()
            url = f"{self.settings.lean_base_url}/customers/v1/{customer_id}/entities"
            logger.info(f"Fetching entities for customer: {customer_id}")
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            entities = response.json()
            # Lean API returns a list directly, not wrapped in a dict
            if isinstance(entities, list):
                logger.info(f"Retrieved {len(entities)} entities for customer: {customer_id}")
                return entities
            else:
                logger.warning(f"Unexpected response format: {type(entities)}")
                return []
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Entities fetch failed: {e.response.status_code} - {e.response.text}")
            raise LeanAPIError(f"Failed to get entities: {e.response.text}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def get_identity(self, entity_id: str) -> Dict[str, Any]:
        """
        Get identity data for an entity.
        
        Args:
            entity_id: Entity ID from Lean
        
        Returns:
            Identity data
        """
        try:
            headers = self._get_headers()
            response = await self.client.post(
                f"{self.settings.lean_base_url}/data/v1/identity",
                json={"entity_id": entity_id},
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved identity data for entity: {entity_id}")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Identity fetch failed: {e.response.status_code} - {e.response.text}")
            raise LeanAPIError(f"Failed to get identity: {e.response.text}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def get_accounts(self, entity_id: str) -> Dict[str, Any]:
        """
        Get accounts data for an entity.
        
        Args:
            entity_id: Entity ID from Lean
        
        Returns:
            Accounts data with list of account_ids
        """
        try:
            headers = self._get_headers()
            response = await self.client.post(
                f"{self.settings.lean_base_url}/data/v1/accounts",
                json={"entity_id": entity_id},
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            accounts_count = len(data.get('payload', {}).get('accounts', []))
            logger.info(f"Retrieved {accounts_count} accounts for entity: {entity_id}")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Accounts fetch failed: {e.response.status_code} - {e.response.text}")
            raise LeanAPIError(f"Failed to get accounts: {e.response.text}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def get_balance(self, account_id: str, entity_id: str) -> Dict[str, Any]:
        """
        Get balance data for an account.
        
        Args:
            account_id: Account ID from Lean
            entity_id: Entity ID from Lean
        
        Returns:
            Balance data
        """
        try:
            headers = self._get_headers()
            response = await self.client.post(
                f"{self.settings.lean_base_url}/data/v1/balance",
                json={"entity_id": entity_id, "account_id": account_id},
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved balance for account: {account_id}")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Balance fetch failed: {e.response.status_code} - {e.response.text}")
            raise LeanAPIError(f"Failed to get balance: {e.response.text}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def get_transactions(
        self,
        account_id: str,
        entity_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        insights: bool = True
    ) -> Dict[str, Any]:
        """
        Get transactions data for an account with enrichment.
        
        Args:
            account_id: Account ID from Lean
            entity_id: Entity ID from Lean
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            insights: Enable transaction categorization and enrichment (default: True)
        
        Returns:
            Transactions data with optional insights (categories, merchant names, etc.)
        """
        try:
            headers = self._get_headers()
            payload = {
                "entity_id": entity_id, 
                "account_id": account_id,
                "insights": insights  # Enable categorization and enrichment
            }
            if from_date:
                payload["from"] = from_date
            if to_date:
                payload["to"] = to_date
            
            response = await self.client.post(
                f"{self.settings.lean_base_url}/data/v1/transactions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            transactions_count = len(data.get('payload', {}).get('transactions', []))
            logger.info(f"Retrieved {transactions_count} transactions for account: {account_id} (insights={'enabled' if insights else 'disabled'})")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Transactions fetch failed: {e.response.status_code} - {e.response.text}")
            raise LeanAPIError(f"Failed to get transactions: {e.response.text}")
