/**
 * API client for Dashboard endpoints
 * Follows the same fetch + handleResponse pattern as leanApi.ts
 */

import {
    DashboardSummary,
    SubscriptionsResponse,
    TransactionsResponse,
    SpendingTrendResponse,
} from '../types';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

class DashboardAPIError extends Error {
    status?: number;
    detail?: string;

    constructor(message: string, status?: number, detail?: string) {
        super(message);
        this.name = 'DashboardAPIError';
        this.status = status;
        this.detail = detail;
    }
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new DashboardAPIError(
            error.detail || 'API request failed',
            response.status,
            error.detail
        );
    }
    return response.json();
}

/**
 * Get dashboard summary (monthly totals, accounts, budgets, safe-to-spend)
 */
export async function getDashboardSummary(
    userId: string
): Promise<DashboardSummary> {
    const response = await fetch(
        `${API_BASE_URL}/api/v1/dashboard/summary/${userId}`,
        {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        }
    );
    return handleResponse<DashboardSummary>(response);
}

/**
 * Get active subscriptions
 */
export async function getSubscriptions(
    userId: string
): Promise<SubscriptionsResponse> {
    const response = await fetch(
        `${API_BASE_URL}/api/v1/dashboard/subscriptions/${userId}`,
        {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        }
    );
    return handleResponse<SubscriptionsResponse>(response);
}

/**
 * Get transactions grouped by bucket for a given month
 */
export async function getTransactions(
    userId: string,
    month?: string
): Promise<TransactionsResponse> {
    let url = `${API_BASE_URL}/api/v1/dashboard/transactions/${userId}`;
    if (month) {
        url += `?month=${month}`;
    }
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<TransactionsResponse>(response);
}

/**
 * Get daily cumulative spending trend for the chart
 */
export async function getSpendingTrend(
    userId: string,
    month?: string
): Promise<SpendingTrendResponse> {
    let url = `${API_BASE_URL}/api/v1/dashboard/spending-trend/${userId}`;
    if (month) {
        url += `?month=${month}`;
    }
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<SpendingTrendResponse>(response);
}
