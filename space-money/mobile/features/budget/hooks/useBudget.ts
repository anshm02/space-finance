/**
 * Custom hook for budget page data management.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { BudgetSummary, LargestPurchasesResponse } from '../types';
import { getBudgetSummary, getLargestPurchases } from '../api/budgetApi';

interface BudgetState {
    summary: BudgetSummary | null;
    largestPurchases: LargestPurchasesResponse | null;
    isLoading: boolean;
    isReady: boolean;
    error: string | null;
}

export function useBudget(userId: string) {
    const [state, setState] = useState<BudgetState>({
        summary: null,
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

    const fetchData = useCallback(async (month?: string) => {
        if (!userId) return;
        setState((prev) => ({ ...prev, isLoading: true, error: null }));
        try {
            const [summary, purchases] = await Promise.all([
                getBudgetSummary(userId, month),
                getLargestPurchases(userId, month),
            ]);
            if (isMountedRef.current) {
                setState({
                    summary,
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
                    error: err.message || 'Failed to load budget data',
                }));
            }
        }
    }, [userId]);

    const refresh = useCallback((month?: string) => {
        fetchData(month);
    }, [fetchData]);

    return { ...state, fetchData, refresh };
}
