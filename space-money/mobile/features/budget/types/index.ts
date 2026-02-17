/**
 * Budget feature TypeScript types
 */

export interface BudgetBucketInfo {
    label: string;
    status: string;
    spent: number;
    budget: number;
    remaining?: number;
    subtitle: string;
    progress: number;
}

export interface CategoryBreakdown {
    lean_category: string;
    display_name: string;
    bucket: string;
    spent: number;
    budget: number;
    percentage_of_spend: number;
    color: string;
    bgColor: string;
    icon: string;
}

export interface BudgetSummary {
    period_month: string;
    display_month: string;
    month_name: string;
    left_for_spending: number;
    budget: number;
    total_expenses: number;
    budget_progress: number;
    fixed: BudgetBucketInfo;
    flexible: BudgetBucketInfo;
    savings: BudgetBucketInfo;
    safe_to_spend: number;
    monthly_income: number;
    expected_bills: number;
    savings_allocation: number;
    categories: CategoryBreakdown[];
    total_category_spend: number;
}

export interface CategoryBreakdownItem {
    lean_category: string;
    display_name: string;
    bucket: string;
    spent: number;
    budget: number;
    remaining: number;
    percentage: number;
    transaction_count: number;
    color: string;
    bgColor: string;
    icon: string;
}

export interface BreakdownResponse {
    period_month: string;
    breakdown: CategoryBreakdownItem[];
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
