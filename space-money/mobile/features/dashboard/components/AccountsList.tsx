/**
 * AccountsList — Connected accounts with expandable Checking, Credit Card groups,
 * Net Cash, and Savings rows.
 * Design tokens from Figma node 2:3026 & 2:3092.
 */

import React, { useState, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    LayoutAnimation,
    Platform,
    UIManager,
} from 'react-native';
import Svg, { Path, Rect, Circle as SvgCircle } from 'react-native-svg';
import { DashboardSummary, AccountInfo } from '../types';

// Enable LayoutAnimation on Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
    UIManager.setLayoutAnimationEnabledExperimental(true);
}

interface AccountsListProps {
    summary: DashboardSummary;
}

function formatBalance(val: number): string {
    return Math.round(val).toLocaleString('en-US');
}

/**
 * Generate initials from institution name (e.g. "Emirates NBD" → "EN")
 */
function getInitials(name: string): string {
    const words = name.split(' ').filter(Boolean);
    if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

/**
 * Deterministic color from institution name
 */
const BADGE_COLORS = ['#0066CC', '#E50914', '#1DB954', '#FF6B35', '#8B5CF6', '#059669', '#DC2626', '#2563EB'];
function getBadgeColor(name: string): string {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return BADGE_COLORS[Math.abs(hash) % BADGE_COLORS.length];
}

/**
 * Extract last 4 digits for display.
 * Priority: account_number → account_name → fallback
 * Looks for patterns like "****1234" or standalone 4-digit suffix.
 */
function getAccountSubtitle(accountNumber?: string | null, accountName?: string): string {
    // Try account_number first
    if (accountNumber) {
        // If it already contains "****", use as-is
        if (accountNumber.includes('****')) return accountNumber;
        // Try to extract last 4 digits
        const numMatch = accountNumber.match(/(\d{4})\s*$/);
        if (numMatch) return `****${numMatch[1]}`;
        // Return the value truncated if needed
        return accountNumber.length > 16 ? accountNumber.substring(0, 16) + '…' : accountNumber;
    }
    // Fall back to account_name
    if (accountName) {
        const nameMatch = accountName.match(/(\d{4})\s*$/);
        if (nameMatch) return `****${nameMatch[1]}`;
        return accountName.length > 16 ? accountName.substring(0, 16) + '…' : accountName;
    }
    return '';
}

// Icon components
const CheckingIcon = () => (
    <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
        <Rect x={2} y={5} width={20} height={14} rx={2} stroke="#6B7280" strokeWidth={1.5} />
        <Path d="M2 10h20" stroke="#6B7280" strokeWidth={1.5} />
    </Svg>
);

const CreditCardIcon = () => (
    <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
        <Rect x={2} y={5} width={20} height={14} rx={2} stroke="#6B7280" strokeWidth={1.5} />
        <Path d="M2 10h20" stroke="#6B7280" strokeWidth={1.5} />
        <Rect x={6} y={14} width={4} height={2} rx={0.5} fill="#6B7280" />
    </Svg>
);

const NetCashIcon = () => (
    <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
        <Path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" stroke="#6B7280" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
);

const SavingsIcon = () => (
    <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
        <Path d="M19 5c-1.5 0-2.8 1.4-3 2-3.5-1.5-11-.3-11 5 0 1.8 0 3 2 4.5V20h4v-2h3v2h4v-4c1-.5 1.7-1 2-2h2v-4h-2c0-1-.5-1.5-1-2" stroke="#6B7280" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
        <SvgCircle cx={14} cy={10} r={1} fill="#6B7280" />
    </Svg>
);

const ChevronDown = ({ rotated }: { rotated?: boolean }) => (
    <Svg width={16} height={16} viewBox="0 0 24 24" fill="none" style={rotated ? { transform: [{ rotate: '180deg' }] } : undefined}>
        <Path d="M6 9l6 6 6-6" stroke="#9CA3AF" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
);

const InfoIcon = () => (
    <Svg width={12} height={12} viewBox="0 0 24 24" fill="none">
        <SvgCircle cx={12} cy={12} r={10} stroke="#9CA3AF" strokeWidth={2} />
        <Path d="M12 16v-4M12 8h.01" stroke="#9CA3AF" strokeWidth={2} strokeLinecap="round" />
    </Svg>
);

/**
 * Sub-account row with colored badge, institution name, account ID, and balance
 */
const SubAccountRow: React.FC<{ account: AccountInfo }> = ({ account }) => {
    const initials = getInitials(account.institution_name || 'BA');
    const badgeColor = getBadgeColor(account.institution_name || 'Bank');
    const displayName = account.institution_name || 'Bank Account';
    const subtitle = getAccountSubtitle(account.account_number, account.account_name);

    return (
        <View style={styles.subAccountRow}>
            {/* Colored circular badge */}
            <View style={[styles.badge, { backgroundColor: badgeColor }]}>
                <Text style={styles.badgeText}>{initials}</Text>
            </View>
            <View style={styles.subAccountInfo}>
                <Text style={styles.subAccountName}>{displayName}</Text>
                {subtitle ? <Text style={styles.subAccountId}>{subtitle}</Text> : null}
            </View>
            <Text style={styles.subAccountBalance}>
                {formatBalance(account.current_balance)}
            </Text>
        </View>
    );
};

export const AccountsList: React.FC<AccountsListProps> = ({ summary }) => {
    const [checkingExpanded, setCheckingExpanded] = useState(false);
    const [creditExpanded, setCreditExpanded] = useState(false);

    // Group accounts by type
    const checkingAccounts = summary.accounts.filter(
        (a) => a.account_type === 'CURRENT'
    );
    const creditAccounts = summary.accounts.filter(
        (a) => a.account_type === 'CREDIT'
    );
    const savingsAccounts = summary.accounts.filter(
        (a) => a.account_type === 'SAVINGS'
    );

    const toggleChecking = useCallback(() => {
        LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
        setCheckingExpanded((prev) => !prev);
    }, []);

    const toggleCredit = useCallback(() => {
        LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
        setCreditExpanded((prev) => !prev);
    }, []);

    return (
        <View style={styles.container}>
            {/* Section Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>ACCOUNTS</Text>
                <TouchableOpacity>
                    <Text style={styles.addAccountLink}>Add Account</Text>
                </TouchableOpacity>
            </View>

            {/* Accounts Card */}
            <View style={styles.card}>
                {/* Checking Group */}
                <TouchableOpacity
                    style={[styles.row, styles.borderBottom]}
                    onPress={toggleChecking}
                    activeOpacity={0.7}
                >
                    <View style={styles.iconCircle}>
                        <CheckingIcon />
                    </View>
                    <Text style={styles.accountName}>Checking</Text>
                    <View style={styles.balanceContainer}>
                        <Text style={styles.balanceText}>
                            {formatBalance(summary.checking_balance)}
                        </Text>
                        <ChevronDown rotated={checkingExpanded} />
                    </View>
                </TouchableOpacity>

                {/* Checking sub-accounts (expanded) */}
                {checkingExpanded && checkingAccounts.map((acct) => (
                    <View key={acct.account_id} style={styles.borderBottom}>
                        <SubAccountRow account={acct} />
                    </View>
                ))}

                {/* Credit Card Group */}
                <TouchableOpacity
                    style={[styles.row, styles.borderBottom]}
                    onPress={toggleCredit}
                    activeOpacity={0.7}
                >
                    <View style={styles.iconCircle}>
                        <CreditCardIcon />
                    </View>
                    <Text style={styles.accountName}>Credit Card</Text>
                    <View style={styles.balanceContainer}>
                        <Text style={styles.balanceText}>
                            {formatBalance(summary.credit_balance)}
                        </Text>
                        <ChevronDown rotated={creditExpanded} />
                    </View>
                </TouchableOpacity>

                {/* Credit sub-accounts (expanded) */}
                {creditExpanded && creditAccounts.map((acct) => (
                    <View key={acct.account_id} style={styles.borderBottom}>
                        <SubAccountRow account={acct} />
                    </View>
                ))}

                {/* Net Cash (non-expandable) */}
                <View style={[styles.row, savingsAccounts.length > 0 || summary.savings_balance === 0 ? styles.borderBottom : undefined]}>
                    <View style={styles.iconCircle}>
                        <NetCashIcon />
                    </View>
                    <Text style={styles.accountName}>Net Cash</Text>
                    <View style={styles.balanceContainer}>
                        <Text style={styles.netCashText}>{formatBalance(summary.net_cash)}</Text>
                        <View style={styles.infoCircle}>
                            <InfoIcon />
                        </View>
                    </View>
                </View>

                {/* Savings */}
                <View style={styles.row}>
                    <View style={styles.iconCircle}>
                        <SavingsIcon />
                    </View>
                    <Text style={styles.accountName}>Savings</Text>
                    <View style={styles.balanceContainer}>
                        {summary.savings_balance > 0 ? (
                            <Text style={styles.balanceText}>
                                {formatBalance(summary.savings_balance)}
                            </Text>
                        ) : (
                            <TouchableOpacity style={styles.startButton}>
                                <Text style={styles.startButtonLabel}>Start</Text>
                                <View style={styles.plusBadge}>
                                    <Text style={styles.plusText}>+</Text>
                                </View>
                            </TouchableOpacity>
                        )}
                    </View>
                </View>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        gap: 14,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 2,
    },
    headerTitle: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        lineHeight: 19.5,
        color: '#1A1D2E',
        letterSpacing: 0.325,
        textTransform: 'uppercase',
    },
    addAccountLink: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '500',
        lineHeight: 21,
        color: '#1A1D2E',
        textDecorationLine: 'underline',
    },
    card: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
        elevation: 3,
        overflow: 'hidden',
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 20,
        height: 77,
        gap: 14,
    },
    borderBottom: {
        borderBottomWidth: 1,
        borderBottomColor: '#F3F4F6',
    },
    iconCircle: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: '#F9FAFB',
        justifyContent: 'center',
        alignItems: 'center',
    },
    accountName: {
        flex: 1,
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        lineHeight: 22.5,
        color: '#1A1D2E',
    },
    balanceContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    balanceText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        lineHeight: 22.5,
        color: '#1A1D2E',
    },
    netCashText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        lineHeight: 22.5,
        color: '#0DB88A',
    },
    infoCircle: {
        width: 20,
        height: 20,
        borderRadius: 10,
        borderWidth: 1.5,
        borderColor: '#9CA3AF',
        justifyContent: 'center',
        alignItems: 'center',
    },
    // Sub-account row styles
    subAccountRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingLeft: 38,
        height: 66,
        gap: 12,
        backgroundColor: '#FAFBFC',
    },
    badge: {
        width: 40,
        height: 40,
        borderRadius: 14,
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
        elevation: 2,
    },
    badgeText: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '700',
        color: '#FFFFFF',
    },
    subAccountInfo: {
        flex: 1,
        gap: 2,
    },
    subAccountName: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '500',
        lineHeight: 21,
        color: '#1A1D2E',
    },
    subAccountId: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '400',
        lineHeight: 18,
        color: '#8B8D97',
    },
    subAccountBalance: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        lineHeight: 22.5,
        color: '#1A1D2E',
    },
    // Savings start button
    startButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    startButtonLabel: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        lineHeight: 22.5,
        color: '#1A1D2E',
    },
    plusBadge: {
        width: 18,
        height: 18,
        borderRadius: 4,
        backgroundColor: '#1A1D2E',
        justifyContent: 'center',
        alignItems: 'center',
    },
    plusText: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '400',
        color: '#FFFFFF',
        lineHeight: 14,
    },
});
