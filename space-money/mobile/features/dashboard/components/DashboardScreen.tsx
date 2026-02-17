/**
 * DashboardScreen — Main scrollable dashboard composing all sections.
 * Top-level container with loading, error, and data states.
 */

import React, { useEffect } from 'react';
import {
    View,
    ScrollView,
    StyleSheet,
    ActivityIndicator,
    Text,
    RefreshControl,
} from 'react-native';
import { useDashboard } from '../hooks/useDashboard';
import { TopBar } from './TopBar';
import { SpendingCard } from './SpendingCard';
import { AccountsList } from './AccountsList';
import { SubscriptionsRow } from './SubscriptionsRow';
import { BudgetCard } from './BudgetCard';
import { TransactionsSection } from './TransactionsSection';

interface DashboardScreenProps {
    userId: string;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({ userId }) => {
    const {
        summary,
        subscriptions,
        transactions,
        spendingTrend,
        isPolling,
        isLoading,
        isReady,
        error,
        fetchAllData,
        refresh,
    } = useDashboard(userId);

    // Fetch data on mount
    useEffect(() => {
        fetchAllData();
    }, []);

    // Polling / Loading state
    if (isPolling || (isLoading && !isReady)) {
        return (
            <View style={styles.outerContainer}>
                <TopBar />
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#6366F1" />
                    <Text style={styles.loadingTitle}>
                        {isPolling ? 'Analyzing your finances...' : 'Loading dashboard...'}
                    </Text>
                    <Text style={styles.loadingSubtitle}>
                        {isPolling
                            ? 'This may take a few moments after syncing'
                            : 'Fetching your financial data'}
                    </Text>
                </View>
            </View>
        );
    }

    // Error state
    if (error && !isReady) {
        return (
            <View style={styles.outerContainer}>
                <TopBar />
                <View style={styles.loadingContainer}>
                    <Text style={styles.errorEmoji}>😕</Text>
                    <Text style={styles.errorTitle}>Something went wrong</Text>
                    <Text style={styles.errorDetail}>{error}</Text>
                </View>
            </View>
        );
    }

    // Empty state (no data yet)
    if (!summary || !summary.has_data) {
        return (
            <View style={styles.outerContainer}>
                <TopBar />
                <View style={styles.loadingContainer}>
                    <Text style={styles.emptyEmoji}>🏦</Text>
                    <Text style={styles.emptyTitle}>No financial data yet</Text>
                    <Text style={styles.emptySubtitle}>
                        Connect a bank account and sync your data to see your dashboard
                    </Text>
                </View>
            </View>
        );
    }

    return (
        <View style={styles.outerContainer}>
            <TopBar />
            <ScrollView
                style={styles.scrollView}
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                refreshControl={
                    <RefreshControl
                        refreshing={isLoading && isReady}
                        onRefresh={refresh}
                        tintColor="#6366F1"
                    />
                }
            >
                {/* Spending Card */}
                <SpendingCard summary={summary} spendingTrend={spendingTrend} />

                {/* Accounts */}
                <AccountsList summary={summary} />

                {/* Subscriptions */}
                {subscriptions && subscriptions.subscriptions.length > 0 && (
                    <SubscriptionsRow
                        subscriptions={subscriptions.subscriptions}
                        totalMonthlyCost={subscriptions.total_monthly_cost}
                    />
                )}

                {/* Budget */}
                {(() => {
                    console.log('[DashboardScreen] summary for BudgetCard:', JSON.stringify({
                        safe_to_spend: summary.safe_to_spend,
                        budget: summary.budget,
                        flexible_pct: summary.flexible_pct,
                        fixed_pct: summary.fixed_pct,
                        savings_pct: summary.savings_pct,
                    }));
                    return null;
                })()}
                <BudgetCard summary={summary} />

                {/* Transactions */}
                <TransactionsSection transactions={transactions} />

                {/* Bottom padding */}
                <View style={styles.bottomPad} />
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    outerContainer: {
        flex: 1,
        backgroundColor: '#F5F5F7',
    },
    scrollView: {
        flex: 1,
    },
    scrollContent: {
        paddingHorizontal: 20,
        paddingTop: 8,
        gap: 24,
    },
    bottomPad: {
        height: 20,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    loadingTitle: {
        fontFamily: 'Inter',
        fontSize: 18,
        fontWeight: '600',
        color: '#1A1D2E',
        marginTop: 20,
        textAlign: 'center',
    },
    loadingSubtitle: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '400',
        color: '#8B8D97',
        marginTop: 8,
        textAlign: 'center',
        lineHeight: 20,
    },
    errorEmoji: {
        fontSize: 48,
    },
    errorTitle: {
        fontFamily: 'Inter',
        fontSize: 18,
        fontWeight: '600',
        color: '#1A1D2E',
        marginTop: 16,
    },
    errorDetail: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '400',
        color: '#EF4444',
        marginTop: 8,
        textAlign: 'center',
        lineHeight: 20,
    },
    emptyEmoji: {
        fontSize: 48,
    },
    emptyTitle: {
        fontFamily: 'Inter',
        fontSize: 18,
        fontWeight: '600',
        color: '#1A1D2E',
        marginTop: 16,
    },
    emptySubtitle: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '400',
        color: '#8B8D97',
        marginTop: 8,
        textAlign: 'center',
        lineHeight: 20,
    },
});
