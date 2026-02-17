/**
 * API client for Budget endpoints
 */

import { BudgetSummary, BreakdownResponse, LargestPurchasesResponse } from '../types';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

class BudgetAPIError extends Error {
    status?: number;
    detail?: string;
    constructor(message: string, status?: number, detail?: string) {
        super(message);
        this.name = 'BudgetAPIError';
        this.status = status;
        this.detail = detail;
    }
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new BudgetAPIError(
            error.detail || 'API request failed',
            response.status,
            error.detail
        );
    }
    return response.json();
}

export async function getBudgetSummary(
    userId: string,
    month?: string
): Promise<BudgetSummary> {
    let url = `${API_BASE_URL}/api/v1/budget/summary/${userId}`;
    if (month) url += `?month=${month}`;
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<BudgetSummary>(response);
}

export async function getBudgetBreakdown(
    userId: string,
    month?: string
): Promise<BreakdownResponse> {
    let url = `${API_BASE_URL}/api/v1/budget/breakdown/${userId}`;
    if (month) url += `?month=${month}`;
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<BreakdownResponse>(response);
}

export async function getLargestPurchases(
    userId: string,
    month?: string
): Promise<LargestPurchasesResponse> {
    let url = `${API_BASE_URL}/api/v1/budget/largest-purchases/${userId}`;
    if (month) url += `?month=${month}`;
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<LargestPurchasesResponse>(response);
}
