/**
 * API client for Lean integration endpoints
 */

import {
  LeanCustomer,
  LeanEntity,
  LeanAccount,
  DataSyncRequest,
  DataSyncResponse,
  EntityLinkRequest,
  LeanError,
} from '../types';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

class LeanAPIError extends Error {
  status?: number;
  detail?: string;

  constructor(message: string, status?: number, detail?: string) {
    super(message);
    this.name = 'LeanAPIError';
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new LeanAPIError(
      error.detail || 'API request failed',
      response.status,
      error.detail
    );
  }
  return response.json();
}

/**
 * Create a Lean customer for a user
 */
export async function createCustomer(userId: string): Promise<LeanCustomer> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lean/customers`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_id: userId }),
  });

  return handleResponse<LeanCustomer>(response);
}

/**
 * Get customer by user ID
 */
export async function getCustomer(userId: string): Promise<LeanCustomer> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/lean/customers/${userId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  return handleResponse<LeanCustomer>(response);
}

/**
 * Link a bank entity to a customer
 */
export async function linkEntity(
  request: EntityLinkRequest
): Promise<LeanEntity> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lean/entities/link`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<LeanEntity>(response);
}

/**
 * Get all entities for a customer
 */
export async function getEntities(customerId: string): Promise<LeanEntity[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/lean/entities/${customerId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  return handleResponse<LeanEntity[]>(response);
}

/**
 * Sync data for an entity
 */
export async function syncData(
  request: DataSyncRequest
): Promise<DataSyncResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lean/sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<DataSyncResponse>(response);
}

/**
 * Get all accounts for an entity
 */
export async function getAccounts(entityId: string): Promise<LeanAccount[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/lean/accounts/${entityId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  return handleResponse<LeanAccount[]>(response);
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lean/health`, {
    method: 'GET',
  });

  return handleResponse<{ status: string }>(response);
}

/**
 * Get customer access token for Link SDK
 */
export async function getCustomerAccessToken(customerId: string): Promise<{
  access_token: string;
  expires_in: number;
}> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/lean/customer-token/${customerId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  return handleResponse<{ access_token: string; expires_in: number }>(response);
}

/**
 * Save entity after Lean Link SDK connection
 */
export async function saveEntity(
  customerId: string,
  entityId: string,
  bankIdentifier?: string
): Promise<LeanEntity> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lean/entities/link`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      customer_id: customerId,
      entity_id: entityId,
      bank_identifier: bankIdentifier,
      permissions: ['identity', 'accounts', 'balance', 'transactions'],
    }),
  });

  return handleResponse<LeanEntity>(response);
}

/**
 * Fetch entities from Lean API for a customer
 */
export async function fetchEntitiesFromLean(leanCustomerId: string): Promise<{
  entities: Array<{
    id: string;
    entity_id?: string; // Keep for backwards compatibility
    bank_identifier: string;
    bank_type: string;
    customer_id: string;
    created_at: string;
    permissions: {
      accounts: boolean;
      balance: boolean;
      identity: boolean;
      transactions: boolean;
      [key: string]: boolean;
    };
  }>;
}> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/lean/customers/${leanCustomerId}/entities-from-lean`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  return handleResponse<{
    entities: Array<{
      id: string;
      entity_id?: string;
      bank_identifier: string;
      bank_type: string;
      customer_id: string;
      created_at: string;
      permissions: {
        accounts: boolean;
        balance: boolean;
        identity: boolean;
        transactions: boolean;
        [key: string]: boolean;
      };
    }>;
  }>(response);
}
