/**
 * Type definitions for Lean integration
 */

export interface LeanCustomer {
  id: string;
  user_id: string;
  customer_id: string;
  app_user_id: string;
  created_at: string;
}

export interface LeanEntity {
  id: string;
  customer_id: string;
  entity_id: string;
  bank_identifier?: string;
  status: 'PENDING' | 'ACTIVE' | 'ERROR';
  permissions: string[];
  created_at: string;
  last_synced_at?: string;
}

export interface LeanAccount {
  id: string;
  entity_id: string;
  account_id: string;
  account_number?: string;
  account_type?: string;
  currency?: string;
  balance?: string;
  available_balance?: string;
}

export interface DataSyncRequest {
  entity_id: string;
  sync_types?: string[];
  from_date?: string;
  to_date?: string;
}

export interface DataSyncResponse {
  entity_id: string;
  sync_results: Record<string, any>;
  files_created: string[];
}

export interface EntityLinkRequest {
  customer_id: string;
  entity_id?: string;
  bank_identifier?: string;
  permissions?: string[];
}

export interface LeanError {
  message: string;
  status?: number;
  detail?: string;
}
