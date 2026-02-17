/**
 * Transactions feature TypeScript types
 */

export interface DateWithTransactions {
    date: string;
    day: number;
    count: number;
}

export interface UpcomingPayment {
    id: string;
    merchant_name: string;
    amount: number;
    category: string;
    lean_category: string;
    classification: string;
    recurrence_type: string;
    next_expected_date: string | null;
    typical_day_of_month: number | null;
    days_until_due: number | null;
    color: string;
    bgColor: string;
    icon: string;
}

export interface UpcomingResponse {
    period_month: string;
    display_month: string;
    month_name: string;
    year: number;
    days_in_month: number;
    first_day_offset: number;
    today_day: number | null;
    dates_with_transactions: DateWithTransactions[];
    upcoming_payments: UpcomingPayment[];
    upcoming_count: number;
    upcoming_total: number;
}

export interface TransactionEntry {
    transaction_id: string;
    merchant_name: string;
    category: string;
    lean_category: string;
    bucket: string;
    amount: number;
    date: string;
    date_iso: string;
    currency_code: string;
    color: string;
    bgColor: string;
    icon: string;
}

export interface TransactionGroup {
    label: string;
    count: number;
    total: number;
    transactions: TransactionEntry[];
}

export interface AllTransactionsResponse {
    period_month: string;
    period_start: string;
    period_end: string;
    total_count: number;
    groups: {
        all: TransactionGroup;
        flexible: TransactionGroup;
        fixed: TransactionGroup;
    };
}

export interface TopMerchant {
    merchant_name: string;
    lean_category: string;
    total_spent: number;
    payments: number;
    color: string;
    bgColor: string;
    icon: string;
}

export interface TopMerchantsResponse {
    period_month: string;
    merchants: TopMerchant[];
}

export interface LargestPurchase {
    transaction_id: string;
    merchant_name: string;
    category: string;
    lean_category: string;
    amount: number;
    date: string;
    date_iso: string;
    color: string;
    bgColor: string;
    icon: string;
}

export interface LargestPurchasesResponse {
    period_month: string;
    purchases: LargestPurchase[];
}

export interface DateRange {
    startDate: string;
    endDate: string;
}
