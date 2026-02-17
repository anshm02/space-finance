/**
 * TransactionsSection — Budget-bucket grouped expandable transaction list.
 * Redesigned to match Figma node 2:3166 with category-colored icons.
 */

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, LayoutAnimation, Platform, UIManager } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { TransactionsResponse, BucketGroup, TransactionEntry } from '../types';

// Enable LayoutAnimation on Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
    UIManager.setLayoutAnimationEnabledExperimental(true);
}

interface TransactionsSectionProps {
    transactions: TransactionsResponse | null;
}

// ---------- Category color + icon mappings ----------

interface CategoryStyle {
    bg: string;       // light tinted background
    icon: string;     // darker icon stroke color
    path: string;     // SVG path(s)
}

const CATEGORY_STYLES: Record<string, CategoryStyle> = {
    GROCERIES: {
        bg: '#E6F9F0', icon: '#059669',
        path: 'M7 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm10 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zM7.2 14.8l.1-.4L8.5 12h7c.8 0 1.5-.4 1.8-1.1l3.4-6.2c.2-.3.1-.7-.2-.9-.3-.2-.7-.1-.9.2L16.3 10H8.5L4.3 2H1v2h2l3.6 7.6-1.4 2.5c-.7 1.3.2 2.9 1.7 2.9H19v-2H7.2z',
    },
    RESTAURANTS_DINING: {
        bg: '#F5E6D3', icon: '#D97706',
        path: 'M11 9H9V2H7v7H5V2H3v7c0 2.1 1.7 3.8 3.8 4v9h2.5v-9C11.3 12.8 13 11.1 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.8 0-5 2.2-5 4z',
    },
    ENTERTAINMENT: {
        bg: '#F0E7FF', icon: '#7C3AED',
        path: 'M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z',
    },
    RETAIL: {
        bg: '#FFF4E6', icon: '#EA580C',
        path: 'M18 6h-2c0-2.2-1.8-4-4-4S8 3.8 8 6H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-2c1.1 0 2 .9 2 2h-4c0-1.1.9-2 2-2zm6 14H6V8h12v10z',
    },
    HEALTH_AND_WELLBEING: {
        bg: '#E6F7F7', icon: '#0D9488',
        path: 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z',
    },
    TRANSPORT: {
        bg: '#E6F0FF', icon: '#2563EB',
        path: 'M18.9 6c-.2-.6-.8-1-1.4-1H6.5c-.7 0-1.2.4-1.4 1L3 12v8c0 .6.4 1 1 1h1c.6 0 1-.4 1-1v-1h12v1c0 .6.4 1 1 1h1c.6 0 1-.4 1-1v-8l-2.1-6zM6.5 16c-.8 0-1.5-.7-1.5-1.5S5.7 13 6.5 13s1.5.7 1.5 1.5S7.3 16 6.5 16zm11 0c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z',
    },
    TRAVEL: {
        bg: '#EDE9FE', icon: '#6366F1',
        path: 'M21 16v-2l-8-5V3.5c0-.8-.7-1.5-1.5-1.5S10 2.7 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z',
    },
    EDUCATION: {
        bg: '#FEF9C3', icon: '#CA8A04',
        path: 'M12 3L1 9l4 2.2v6L12 21l7-3.8v-6l2-1.1V17h2V9L12 3zm6.8 6L12 12.7 5.2 9 12 5.3 18.8 9zM17 15.7l-5 2.7-5-2.7v-3.5l5 2.7 5-2.7v3.5z',
    },
    GOVERNMENT: {
        bg: '#F3F4F6', icon: '#6B7280',
        path: 'M12 2L2 7v1h20V7L12 2zM4 10v7h3v-7H4zm5 0v7h3v-7H9zm5 0v7h3v-7h-3zm5 0v7h0V10zM2 19v2h20v-2H2z',
    },
    RENT_AND_SERVICES: {
        bg: '#E6EBF5', icon: '#1E40AF',
        path: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
    },
    LOANS_AND_INVESTMENTS: {
        bg: '#FEE2E2', icon: '#DC2626',
        path: 'M4 10h3v7H4v-7zm6.5-5h3v12h-3V5zM17 8h3v9h-3V8zM2 19h20v2H2v-2z',
    },
    BANK_FEES_AND_CHARGES: {
        bg: '#F1F1F1', icon: '#4B5563',
        path: 'M7.5 11C9.4 11 11 9.4 11 7.5S9.4 4 7.5 4 4 5.6 4 7.5 5.6 11 7.5 11zm9 2c-1.9 0-3.5 1.6-3.5 3.5s1.6 3.5 3.5 3.5 3.5-1.6 3.5-3.5-1.6-3.5-3.5-3.5zM5.6 19.8l13-13 1.4 1.4-13 13-1.4-1.4z',
    },
};

const DEFAULT_STYLE: CategoryStyle = {
    bg: '#F3F4F6', icon: '#6B7280',
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
};

function getCategoryStyle(leanCategory: string): CategoryStyle {
    return CATEGORY_STYLES[leanCategory] || DEFAULT_STYLE;
}

// ---------- Helper functions ----------

function formatAmount(val: number): string {
    return Math.round(val).toLocaleString('en-US');
}

function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

const bucketColors: { [key: string]: string } = {
    Fixed: '#6366F1',
    Flexible: '#F59E0B',
    Savings: '#0DB88A',
};

// SVG icon paths for bucket headers (grey icons in light grey circles)
const BUCKET_HEADER_ICONS: Record<string, string> = {
    Fixed: 'M4 10h3v7H4v-7zm6.5-5h3v12h-3V5zM17 8h3v9h-3V8zM2 19h20v2H2v-2z',
    Flexible: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-9 14l-5-5 1.4-1.4L10 14.2l7.6-7.6L19 8l-9 9z',
    Savings: 'M11.8 10.9c-2.3-.5-3-1.2-3-2.2 0-1.1 1-1.9 2.7-1.9 1.8 0 2.4.8 2.5 2h2.2c-.1-1.7-1.1-3.2-3.2-3.6V3h-3v2.1c-1.9.4-3.5 1.6-3.5 3.5 0 2.3 1.9 3.4 4.6 4 2.4.6 2.9 1.4 2.9 2.3 0 .7-.5 1.7-2.5 1.7-1.9 0-2.7-.9-2.8-2H6.4c.1 2 1.6 3.1 3.4 3.5V21h3v-2.1c1.9-.4 3.5-1.5 3.5-3.6 0-2.8-2.4-3.8-4.5-4.4z',
};

// ---------- Inline SVG components ----------

const ChevronIcon: React.FC<{ expanded: boolean }> = ({ expanded }) => (
    <Svg width={16} height={16} viewBox="0 0 24 24" fill="none">
        <Path
            d={expanded ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'}
            stroke="#9CA3AF"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    </Svg>
);

const CategoryIcon: React.FC<{ leanCategory: string }> = ({ leanCategory }) => {
    const style = getCategoryStyle(leanCategory);
    return (
        <View style={[txStyles.iconContainer, { backgroundColor: style.bg }]}>
            <Svg width={18} height={18} viewBox="0 0 24 24" fill={style.icon}>
                <Path d={style.path} />
            </Svg>
        </View>
    );
};

// ---------- Transaction Row ----------

const TransactionRow: React.FC<{
    tx: TransactionEntry;
    showBorder: boolean;
}> = ({ tx, showBorder }) => (
    <View style={[txStyles.row, showBorder && txStyles.rowBorder]}>
        <CategoryIcon leanCategory={tx.lean_category} />
        <View style={txStyles.rowContent}>
            <Text style={txStyles.merchantName} numberOfLines={1}>
                {tx.merchant_name}
            </Text>
            <Text style={txStyles.categoryLabel}>{tx.category}</Text>
        </View>
        <View style={txStyles.rowRight}>
            <Text style={txStyles.amountText}>{formatAmount(tx.amount)} AED</Text>
            <Text style={txStyles.dateText}>{formatDate(tx.date)}</Text>
        </View>
    </View>
);

// ---------- Bucket Section ----------

const BucketSection: React.FC<{
    bucket: BucketGroup;
    color: string;
}> = ({ bucket, color }) => {
    const [expanded, setExpanded] = useState(false);
    const displayTransactions = expanded ? bucket.transactions : bucket.transactions.slice(0, 3);

    const toggle = () => {
        LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
        setExpanded(!expanded);
    };

    if (bucket.transactions.length === 0) {
        return null;
    }

    return (
        <View style={sectionStyles.container}>
            {/* Bucket header */}
            <TouchableOpacity style={sectionStyles.header} onPress={toggle}>
                <View style={sectionStyles.headerLeft}>
                    <View style={sectionStyles.headerIconCircle}>
                        <Svg width={16} height={16} viewBox="0 0 24 24" fill="#6B7280">
                            <Path d={BUCKET_HEADER_ICONS[bucket.label] || BUCKET_HEADER_ICONS.Flexible} />
                        </Svg>
                    </View>
                    <Text style={sectionStyles.bucketLabel}>{bucket.label}</Text>
                    <Text style={sectionStyles.countBadge}>{bucket.transactions.length}</Text>
                </View>
                <View style={sectionStyles.headerRight}>
                    <Text style={sectionStyles.totalText}>{formatAmount(bucket.total)} AED</Text>
                    <ChevronIcon expanded={expanded} />
                </View>
            </TouchableOpacity>

            {/* Transaction rows */}
            <View style={sectionStyles.txListContainer}>
                {displayTransactions.map((tx, index) => (
                    <TransactionRow
                        key={tx.transaction_id}
                        tx={tx}
                        showBorder={index < displayTransactions.length - 1}
                    />
                ))}
            </View>

            {/* Show more / Show less */}
            {bucket.transactions.length > 3 && (
                <TouchableOpacity style={sectionStyles.showMore} onPress={toggle}>
                    <Text style={sectionStyles.showMoreText}>
                        {expanded
                            ? 'Show less'
                            : `Show ${bucket.transactions.length - 3} more`}
                    </Text>
                </TouchableOpacity>
            )}
        </View>
    );
};

// ---------- Transaction row styles ----------

const txStyles = StyleSheet.create({
    iconContainer: {
        width: 36,
        height: 36,
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
        paddingVertical: 14,
        paddingHorizontal: 20,
    },
    rowBorder: {
        borderBottomWidth: 1,
        borderBottomColor: '#EEEFF1',
    },
    rowContent: {
        flex: 1,
        gap: 2,
    },
    merchantName: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '500',
        lineHeight: 21,
        color: '#1A1D2E',
    },
    categoryLabel: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '400',
        lineHeight: 18,
        color: '#8B8D97',
    },
    rowRight: {
        alignItems: 'flex-end',
    },
    amountText: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '600',
        lineHeight: 21,
        color: '#1A1D2E',
    },
    dateText: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '400',
        lineHeight: 18,
        color: '#8B8D97',
        marginTop: 1,
    },
});

// ---------- Section styles ----------

const sectionStyles = StyleSheet.create({
    container: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        overflow: 'hidden',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
        elevation: 2,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 18,
        borderBottomWidth: 1,
        borderBottomColor: '#F3F4F6',
    },
    headerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    headerIconCircle: {
        width: 32,
        height: 32,
        borderRadius: 16,
        backgroundColor: '#F3F4F6',
        alignItems: 'center',
        justifyContent: 'center',
    },
    bucketLabel: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        lineHeight: 22.5,
        color: '#1A1D2E',
    },
    countBadge: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '500',
        color: '#8B8D97',
        backgroundColor: '#F3F4F6',
        borderRadius: 8,
        paddingHorizontal: 6,
        paddingVertical: 2,
        overflow: 'hidden',
    },
    headerRight: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    totalText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        lineHeight: 22.5,
        color: '#1A1D2E',
    },
    txListContainer: {
        backgroundColor: '#FAFBFC',
    },
    showMore: {
        alignItems: 'center',
        paddingVertical: 14,
        borderTopWidth: 1,
        borderTopColor: '#F3F4F6',
    },
    showMoreText: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        lineHeight: 19.5,
        color: '#9CA3AF',
    },
});

// ---------- Main component ----------

export const TransactionsSection: React.FC<TransactionsSectionProps> = ({
    transactions,
}) => {
    if (!transactions) return null;

    const buckets = [
        { data: transactions.buckets.fixed, color: bucketColors.Fixed },
        { data: transactions.buckets.flexible, color: bucketColors.Flexible },
        { data: transactions.buckets.savings, color: bucketColors.Savings },
    ];

    const hasAny = buckets.some((b) => b.data.transactions.length > 0);
    if (!hasAny) return null;

    return (
        <View style={styles.wrapper}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>TRANSACTIONS</Text>
            </View>
            <View style={styles.bucketsContainer}>
                {buckets.map((b) => (
                    <BucketSection key={b.data.label} bucket={b.data} color={b.color} />
                ))}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    wrapper: {
        gap: 14,
    },
    header: {
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
    bucketsContainer: {
        gap: 10,
    },
});
