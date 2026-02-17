/**
 * Custom hook for transactions page data management.
 * Supports date-range filtering for all/merchants/purchases.
 * Upcoming always uses current month (no date filter).
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
    UpcomingResponse,
    AllTransactionsResponse,
    TopMerchantsResponse,
    LargestPurchasesResponse,
    DateRange,
} from '../types';
import {
    getUpcomingTransactions,
    getAllTransactions,
    getTopMerchants,
    getLargestPurchases,
} from '../api/transactionsApi';

interface TransactionsState {
    upcoming: UpcomingResponse | null;
    allTransactions: AllTransactionsResponse | null;
    topMerchants: TopMerchantsResponse | null;
    largestPurchases: LargestPurchasesResponse | null;
    isLoading: boolean;
    isReady: boolean;
    error: string | null;
}

export function useTransactions(userId: string) {
    const [state, setState] = useState<TransactionsState>({
        upcoming: null,
        allTransactions: null,
        topMerchants: null,
        largestPurchases: null,
        isLoading: false,
        isReady: false,
        error: null,
    });
    const isMountedRef = useRef(true);

    useEffect(() => {
        isMountedRef.current = true;
        return () => { isMountedRef.current = false; };
    }, []);

    const fetchData = useCallback(async (dateRange?: DateRange, search?: string) => {
        if (!userId) return;
        setState((prev) => ({ ...prev, isLoading: true, error: null }));
        try {
            const [upcoming, all, merchants, purchases] = await Promise.all([
                getUpcomingTransactions(userId),
                getAllTransactions(userId, dateRange, search),
                getTopMerchants(userId, dateRange),
                getLargestPurchases(userId, dateRange),
            ]);
            if (isMountedRef.current) {
                setState({
                    upcoming,
                    allTransactions: all,
                    topMerchants: merchants,
                    largestPurchases: purchases,
                    isLoading: false,
                    isReady: true,
                    error: null,
                });
            }
        } catch (err: any) {
            if (isMountedRef.current) {
                setState((prev) => ({
                    ...prev,
                    isLoading: false,
                    error: err.message || 'Failed to load transactions',
                }));
            }
        }
    }, [userId]);

    const fetchFiltered = useCallback(async (dateRange?: DateRange, search?: string) => {
        if (!userId) return;
        try {
            const [all, merchants, purchases] = await Promise.all([
                getAllTransactions(userId, dateRange, search),
                getTopMerchants(userId, dateRange),
                getLargestPurchases(userId, dateRange),
            ]);
            if (isMountedRef.current) {
                setState((prev) => ({
                    ...prev,
                    allTransactions: all,
                    topMerchants: merchants,
                    largestPurchases: purchases,
                }));
            }
        } catch {
            // Swallow filter errors
        }
    }, [userId]);

    const searchTransactions = useCallback(async (search: string, dateRange?: DateRange) => {
        if (!userId) return;
        try {
            const all = await getAllTransactions(userId, dateRange, search);
            if (isMountedRef.current) {
                setState((prev) => ({ ...prev, allTransactions: all }));
            }
        } catch {
            // Swallow search errors
        }
    }, [userId]);

    const refresh = useCallback((dateRange?: DateRange) => {
        fetchData(dateRange);
    }, [fetchData]);

    return { ...state, fetchData, fetchFiltered, refresh, searchTransactions };
}
