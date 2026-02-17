/**
 * API client for Transactions endpoints.
 * Supports date-range filtering via start_date/end_date params.
 */

import {
    UpcomingResponse,
    AllTransactionsResponse,
    TopMerchantsResponse,
    LargestPurchasesResponse,
    DateRange,
} from '../types';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

class TransactionsAPIError extends Error {
    status?: number;
    detail?: string;
    constructor(message: string, status?: number, detail?: string) {
        super(message);
        this.name = 'TransactionsAPIError';
        this.status = status;
        this.detail = detail;
    }
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new TransactionsAPIError(
            error.detail || 'API request failed',
            response.status,
            error.detail
        );
    }
    return response.json();
}

export async function getUpcomingTransactions(
    userId: string
): Promise<UpcomingResponse> {
    const response = await fetch(
        `${API_BASE_URL}/api/v1/transactions/upcoming/${userId}`,
        { method: 'GET', headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse<UpcomingResponse>(response);
}

export async function getAllTransactions(
    userId: string,
    dateRange?: DateRange,
    search?: string
): Promise<AllTransactionsResponse> {
    const params = new URLSearchParams();
    if (dateRange) {
        params.append('start_date', dateRange.startDate);
        params.append('end_date', dateRange.endDate);
    }
    if (search) params.append('search', search);
    const qs = params.toString();
    const url = `${API_BASE_URL}/api/v1/transactions/all/${userId}${qs ? `?${qs}` : ''}`;
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<AllTransactionsResponse>(response);
}

export async function getTopMerchants(
    userId: string,
    dateRange?: DateRange
): Promise<TopMerchantsResponse> {
    const params = new URLSearchParams();
    if (dateRange) {
        params.append('start_date', dateRange.startDate);
        params.append('end_date', dateRange.endDate);
    }
    const qs = params.toString();
    const url = `${API_BASE_URL}/api/v1/transactions/top-merchants/${userId}${qs ? `?${qs}` : ''}`;
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<TopMerchantsResponse>(response);
}

export async function getLargestPurchases(
    userId: string,
    dateRange?: DateRange
): Promise<LargestPurchasesResponse> {
    const params = new URLSearchParams();
    if (dateRange) {
        params.append('start_date', dateRange.startDate);
        params.append('end_date', dateRange.endDate);
    }
    const qs = params.toString();
    const url = `${API_BASE_URL}/api/v1/transactions/largest-purchases/${userId}${qs ? `?${qs}` : ''}`;
    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<LargestPurchasesResponse>(response);
}
