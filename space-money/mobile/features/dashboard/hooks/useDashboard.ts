/**
 * Custom hook for dashboard data management.
 * Handles polling for analytics pipeline completion and fetching all dashboard data.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    DashboardSummary,
    SubscriptionsResponse,
    TransactionsResponse,
    SpendingTrendResponse,
} from '../types';
import {
    getDashboardSummary,
    getSubscriptions,
    getTransactions,
    getSpendingTrend,
} from '../api/dashboardApi';

interface DashboardState {
    summary: DashboardSummary | null;
    subscriptions: SubscriptionsResponse | null;
    transactions: TransactionsResponse | null;
    spendingTrend: SpendingTrendResponse | null;
    isPolling: boolean;
    isLoading: boolean;
    isReady: boolean;
    error: string | null;
}

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_DURATION_MS = 30000;

export function useDashboard(userId: string) {
    const [state, setState] = useState<DashboardState>({
        summary: null,
        subscriptions: null,
        transactions: null,
        spendingTrend: null,
        isPolling: false,
        isLoading: false,
        isReady: false,
        error: null,
    });

    const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollStartRef = useRef<number>(0);
    const isMountedRef = useRef(true);

    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
            if (pollTimerRef.current) {
                clearTimeout(pollTimerRef.current);
            }
        };
    }, []);

    /**
     * Fetch all dashboard data once summary is available.
     */
    const fetchAllData = useCallback(async () => {
        if (!userId) return;

        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        try {
            const [summary, subs, txns, trend] = await Promise.all([
                getDashboardSummary(userId),
                getSubscriptions(userId),
                getTransactions(userId),
                getSpendingTrend(userId),
            ]);

            if (isMountedRef.current) {
                setState({
                    summary,
                    subscriptions: subs,
                    transactions: txns,
                    spendingTrend: trend,
                    isPolling: false,
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
                    error: err.message || 'Failed to load dashboard data',
                }));
            }
        }
    }, [userId]);

    /**
     * Start polling for derived data after sync completes.
     * Polls getDashboardSummary every 2s until has_data is true or timeout.
     */
    const startPolling = useCallback(() => {
        if (!userId) return;

        setState((prev) => ({ ...prev, isPolling: true, error: null }));
        pollStartRef.current = Date.now();

        const poll = async () => {
            if (!isMountedRef.current) return;

            const elapsed = Date.now() - pollStartRef.current;
            if (elapsed >= MAX_POLL_DURATION_MS) {
                // Timeout — try to load whatever is available
                setState((prev) => ({ ...prev, isPolling: false }));
                fetchAllData();
                return;
            }

            try {
                const summary = await getDashboardSummary(userId);
                if (summary.has_data) {
                    // Data is ready — fetch everything
                    setState((prev) => ({ ...prev, isPolling: false }));
                    fetchAllData();
                    return;
                }
            } catch {
                // Keep polling on error
            }

            if (isMountedRef.current) {
                pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
            }
        };

        poll();
    }, [userId, fetchAllData]);

    /**
     * Refresh all dashboard data (manual pull to refresh).
     */
    const refresh = useCallback(() => {
        fetchAllData();
    }, [fetchAllData]);

    return {
        ...state,
        startPolling,
        refresh,
        fetchAllData,
    };
}
