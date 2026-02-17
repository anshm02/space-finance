/**
 * Dashboard feature TypeScript types
 */

export interface AccountInfo {
    account_id: string;
    account_name: string;
    account_number?: string | null;
    account_type: 'CURRENT' | 'SAVINGS' | 'CREDIT' | null;
    institution_name: string;
    current_balance: number;
    currency_code: string;
}

export interface DashboardSummary {
    has_data: boolean;
    period_month: string;
    day_of_month: number;
    days_in_month: number;
    display_month: string;
    total_income: number;
    total_expenses: number;
    net_savings: number;
    savings_rate: number;
    total_fixed_spent: number;
    total_flexible_spent: number;
    projected_savings: number;
    // Budget (5-step calculation)
    monthly_income: number;
    expected_fixed_bills: number;
    expected_bills: number;
    savings_allocation: number;
    budget: number;
    safe_to_spend: number;
    is_over_budget: boolean;
    status_text: string;
    // Budget card circle data
    fixed_bills_paid_count: number;
    fixed_bills_total_count: number;
    fixed_pct: number;
    fixed_status_label: string;
    flexible_spent: number;
    flexible_pct: number;
    savings_pct: number;
    // Accounts
    accounts: AccountInfo[];
    checking_balance: number;
    credit_balance: number;
    savings_balance: number;
    net_cash: number;
    // Legacy budgets
    total_budget: number;
    fixed_budget: number;
    fixed_actual: number;
    flexible_budget: number;
    flexible_actual: number;
    savings_budget: number;
    savings_actual: number;
    bills_due_count: number;
    is_on_track: boolean;
}

export interface Subscription {
    id: string;
    merchant_name: string;
    amount: number;
    next_expected_date: string | null;
    days_until_next: number | null;
    logo_url: string | null;
    recurrence_type: string;
}

export interface SubscriptionsResponse {
    subscriptions: Subscription[];
    total_monthly_cost: number;
}

export interface TransactionEntry {
    transaction_id: string;
    merchant_name: string;
    category: string;
    lean_category: string;
    amount: number;
    date: string;
    currency_code: string;
}

export interface BucketGroup {
    label: string;
    total: number;
    transactions: TransactionEntry[];
}

export interface TransactionsResponse {
    period_month: string;
    buckets: {
        fixed: BucketGroup;
        flexible: BucketGroup;
        savings: BucketGroup;
    };
}

export interface SpendingDataPoint {
    day: number;
    date: string;
    daily_amount: number;
    cumulative: number;
}

export interface SpendingTrendResponse {
    period_month: string;
    days_in_month: number;
    data_points: SpendingDataPoint[];
}
