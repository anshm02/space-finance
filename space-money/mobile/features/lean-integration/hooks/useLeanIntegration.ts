/**
 * Custom hook for Lean integration operations
 */

import { useState, useCallback } from 'react';
import {
  LeanCustomer,
  LeanEntity,
  LeanAccount,
  DataSyncRequest,
  DataSyncResponse,
  EntityLinkRequest,
} from '../types';
import * as leanApi from '../api/leanApi';

interface UseLeanIntegrationReturn {
  customer: LeanCustomer | null;
  entities: LeanEntity[];
  accounts: LeanAccount[];
  isLoading: boolean;
  error: string | null;
  createCustomer: (userId: string) => Promise<void>;
  getCustomer: (userId: string) => Promise<void>;
  linkEntity: (request: EntityLinkRequest) => Promise<LeanEntity | null>;
  getEntities: (customerId: string) => Promise<void>;
  syncData: (request: DataSyncRequest) => Promise<DataSyncResponse | null>;
  getAccounts: (entityId: string) => Promise<void>;
  getCustomerAccessToken: (customerId: string) => Promise<string | null>;
  saveEntity: (customerId: string, entityId: string, bankIdentifier?: string) => Promise<LeanEntity | null>;
  clearError: () => void;
}

export function useLeanIntegration(): UseLeanIntegrationReturn {
  const [customer, setCustomer] = useState<LeanCustomer | null>(null);
  const [entities, setEntities] = useState<LeanEntity[]>([]);
  const [accounts, setAccounts] = useState<LeanAccount[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const createCustomer = useCallback(async (userId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await leanApi.createCustomer(userId);
      setCustomer(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create customer';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getCustomer = useCallback(async (userId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await leanApi.getCustomer(userId);
      setCustomer(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get customer';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const linkEntity = useCallback(
    async (request: EntityLinkRequest): Promise<LeanEntity | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await leanApi.linkEntity(request);
        setEntities((prev) => [...prev, result]);
        return result;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to link entity';
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const getEntities = useCallback(async (customerId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await leanApi.getEntities(customerId);
      setEntities(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get entities';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const syncData = useCallback(
    async (request: DataSyncRequest): Promise<DataSyncResponse | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await leanApi.syncData(request);
        return result;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to sync data';
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const getAccounts = useCallback(async (entityId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await leanApi.getAccounts(entityId);
      setAccounts(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get accounts';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getCustomerAccessToken = useCallback(
    async (customerId: string): Promise<string | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await leanApi.getCustomerAccessToken(customerId);
        return result.access_token;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to get customer token';
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const saveEntity = useCallback(
    async (
      customerId: string,
      entityId: string,
      bankIdentifier?: string
    ): Promise<LeanEntity | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await leanApi.saveEntity(customerId, entityId, bankIdentifier);
        setEntities((prev) => [...prev, result]);
        return result;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to save entity';
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return {
    customer,
    entities,
    accounts,
    isLoading,
    error,
    createCustomer,
    getCustomer,
    linkEntity,
    getEntities,
    syncData,
    getAccounts,
    getCustomerAccessToken,
    saveEntity,
    clearError,
  };
}
