/**
 * BudgetScreen — Full budget page with all sections.
 *
 * Design tokens extracted from Figma MCP (miranda-mvp-v1-mockups):
 *  - Background: #F7F8FA
 *  - Card bg: #FFFFFF, borderRadius: 20
 *  - Primary text: #1A1D2E
 *  - Secondary text: #8B8D97
 *  - Muted text: #B0B3BE
 *  - Divider: #F0F1F3
 *  - Progress bar: h=6, bg=#F0F1F3, fill=#6366F1
 *  - Icon circle: bg=#F9FAFB, icon color=#6B7280
 *  - Section header: 13px, weight 600, uppercase, tracking wide
 *
 * Category icons: same filled-SVG approach as Dashboard TransactionsSection.
 * Donut chart: replicated from attached screenshot (NOT Figma).
 */

import React, { useEffect } from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    ActivityIndicator,
    RefreshControl,
    TouchableOpacity,
} from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { useBudget } from '../hooks/useBudget';
import { CategoryBreakdown } from '../types';

interface BudgetScreenProps {
    userId: string;
}

/* ------------------------------------------------------------------ */
/*  Category style map — SAME as Dashboard TransactionsSection        */
/* ------------------------------------------------------------------ */

interface CategoryStyle {
    bg: string;
    icon: string;
    path: string;
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
    FOOD_AND_DINING: {
        bg: '#F5E6D3', icon: '#D97706',
        path: 'M11 9H9V2H7v7H5V2H3v7c0 2.1 1.7 3.8 3.8 4v9h2.5v-9C11.3 12.8 13 11.1 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.8 0-5 2.2-5 4z',
    },
    ENTERTAINMENT: {
        bg: '#F0E7FF', icon: '#7C3AED',
        path: 'M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z',
    },
    ENTERTAINMENT_AND_RECREATION: {
        bg: '#F0E7FF', icon: '#7C3AED',
        path: 'M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z',
    },
    RETAIL: {
        bg: '#FFF4E6', icon: '#EA580C',
        path: 'M18 6h-2c0-2.2-1.8-4-4-4S8 3.8 8 6H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-2c1.1 0 2 .9 2 2h-4c0-1.1.9-2 2-2zm6 14H6V8h12v10z',
    },
    SHOPPING: {
        bg: '#FFF4E6', icon: '#EA580C',
        path: 'M18 6h-2c0-2.2-1.8-4-4-4S8 3.8 8 6H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-2c1.1 0 2 .9 2 2h-4c0-1.1.9-2 2-2zm6 14H6V8h12v10z',
    },
    HEALTH_AND_WELLBEING: {
        bg: '#E6F7F7', icon: '#0D9488',
        path: 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z',
    },
    HEALTH_AND_WELLNESS: {
        bg: '#E6F7F7', icon: '#0D9488',
        path: 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z',
    },
    TRANSPORT: {
        bg: '#E6F0FF', icon: '#2563EB',
        path: 'M18.9 6c-.2-.6-.8-1-1.4-1H6.5c-.7 0-1.2.4-1.4 1L3 12v8c0 .6.4 1 1 1h1c.6 0 1-.4 1-1v-1h12v1c0 .6.4 1 1 1h1c.6 0 1-.4 1-1v-8l-2.1-6zM6.5 16c-.8 0-1.5-.7-1.5-1.5S5.7 13 6.5 13s1.5.7 1.5 1.5S7.3 16 6.5 16zm11 0c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z',
    },
    AUTO_AND_TRANSPORT: {
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
    BILLS_AND_UTILITIES: {
        bg: '#FEF3C7', icon: '#D97706',
        path: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
    },
    PERSONAL_CARE: {
        bg: '#FCE7F3', icon: '#DB2777',
        path: 'M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z',
    },
    INSURANCE: {
        bg: '#E0F2FE', icon: '#0EA5E9',
        path: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
    },
    LOAN_PAYMENT: {
        bg: '#FEE2E2', icon: '#DC2626',
        path: 'M4 10h3v7H4v-7zm6.5-5h3v12h-3V5zM17 8h3v9h-3V8zM2 19h20v2H2v-2z',
    },
    FINANCIAL_SERVICES: {
        bg: '#F3F4F6', icon: '#6B7280',
        path: 'M21 18v1c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V5c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5z',
    },
    FEES_AND_CHARGES: {
        bg: '#FED7D7', icon: '#E53E3E',
        path: 'M7.5 11C9.4 11 11 9.4 11 7.5S9.4 4 7.5 4 4 5.6 4 7.5 5.6 11 7.5 11zm9 2c-1.9 0-3.5 1.6-3.5 3.5s1.6 3.5 3.5 3.5 3.5-1.6 3.5-3.5-1.6-3.5-3.5-3.5zM5.6 19.8l13-13 1.4 1.4-13 13-1.4-1.4z',
    },
    GIFTS_AND_DONATIONS: {
        bg: '#E9D5FF', icon: '#A855F7',
        path: 'M20 6h-2.18c.11-.31.18-.65.18-1 0-1.66-1.34-3-3-3-1.05 0-1.96.54-2.5 1.35l-.5.67-.5-.68C10.96 2.54 10.05 2 9 2 7.34 2 6 3.34 6 5c0 .35.07.69.18 1H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-5-2c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zM9 4c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm11 15H4v-2h16v2zm0-5H4V8h5.08L7 10.83 8.62 12 11 8.76l1-1.36 1 1.36L15.38 12 17 10.83 14.92 8H20v6z',
    },
    CASH_AND_CHECKS: {
        bg: '#D1FAE5', icon: '#10B981',
        path: 'M21 18v1c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V5c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5z',
    },
    HOME_IMPROVEMENT: {
        bg: '#D1FAE5', icon: '#059669',
        path: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
    },
    BUSINESS_SERVICES: {
        bg: '#E0F2FE', icon: '#0EA5E9',
        path: 'M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z',
    },
};

const DEFAULT_STYLE: CategoryStyle = {
    bg: '#F3F4F6', icon: '#6B7280',
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
};

function getCatStyle(leanCategory: string): CategoryStyle {
    return CATEGORY_STYLES[leanCategory] || DEFAULT_STYLE;
}

/* ------------------------------------------------------------------ */
/*  Filled SVG icon (same rendering as Dashboard TransactionsSection) */
/* ------------------------------------------------------------------ */

const CatIcon: React.FC<{
    leanCategory: string;
    size?: number;
    bgOverride?: string;
    iconOverride?: string;
}> = ({ leanCategory, size = 32, bgOverride, iconOverride }) => {
    const style = getCatStyle(leanCategory);
    const iconSize = size * 0.55;
    return (
        <View
            style={{
                width: size,
                height: size,
                borderRadius: size * 0.3,
                backgroundColor: bgOverride || style.bg,
                alignItems: 'center',
                justifyContent: 'center',
            }}
        >
            <Svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill={iconOverride || style.icon}>
                <Path d={style.path} />
            </Svg>
        </View>
    );
};

/* Bucket header icons (grey filled, same as Dashboard) */
const BUCKET_PATHS: Record<string, string> = {
    receipt: 'M4 10h3v7H4v-7zm6.5-5h3v12h-3V5zM17 8h3v9h-3V8zM2 19h20v2H2v-2z',
    'shopping-bag': 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-9 14l-5-5 1.4-1.4L10 14.2l7.6-7.6L19 8l-9 9z',
    'piggy-bank': 'M11.8 10.9c-2.3-.5-3-1.2-3-2.2 0-1.1 1-1.9 2.7-1.9 1.8 0 2.4.8 2.5 2h2.2c-.1-1.7-1.1-3.2-3.2-3.6V3h-3v2.1c-1.9.4-3.5 1.6-3.5 3.5 0 2.3 1.9 3.4 4.6 4 2.4.6 2.9 1.4 2.9 2.3 0 .7-.5 1.7-2.5 1.7-1.9 0-2.7-.9-2.8-2H6.4c.1 2 1.6 3.1 3.4 3.5V21h3v-2.1c1.9-.4 3.5-1.5 3.5-3.6 0-2.8-2.4-3.8-4.5-4.4z',
};

const BucketIcon: React.FC<{ name: string }> = ({ name }) => (
    <View style={styles.iconCircle}>
        <Svg width={18} height={18} viewBox="0 0 24 24" fill="#6B7280">
            <Path d={BUCKET_PATHS[name] || BUCKET_PATHS.receipt} />
        </Svg>
    </View>
);

/* ------------------------------------------------------------------ */
/*  Donut Chart (replicated from attached screenshot exactly)         */
/*  Thick ring, colored segments, floating category icons             */
/* ------------------------------------------------------------------ */

const DonutChart: React.FC<{
    categories: CategoryBreakdown[];
    totalSpend: number;
    monthName: string;
}> = ({ categories, totalSpend, monthName }) => {
    const size = 260;
    const center = size / 2;
    const outerR = 112;
    const innerR = 88;
    const iconR = outerR + 2;

    const displayedTotal = categories.reduce((sum, c) => sum + c.spent, 0);
    const safeTotal = displayedTotal > 0 ? displayedTotal : 1;

    const polarToCart = (cx: number, cy: number, r: number, deg: number) => ({
        x: cx + r * Math.cos((deg * Math.PI) / 180),
        y: cy + r * Math.sin((deg * Math.PI) / 180),
    });

    const arcPath = (startDeg: number, endDeg: number) => {
        const s1 = polarToCart(center, center, outerR, startDeg);
        const e1 = polarToCart(center, center, outerR, endDeg);
        const s2 = polarToCart(center, center, innerR, endDeg);
        const e2 = polarToCart(center, center, innerR, startDeg);
        const sweep = endDeg - startDeg;
        const largeArc = sweep > 180 ? 1 : 0;
        return [
            `M ${s1.x} ${s1.y}`,
            `A ${outerR} ${outerR} 0 ${largeArc} 1 ${e1.x} ${e1.y}`,
            `L ${s2.x} ${s2.y}`,
            `A ${innerR} ${innerR} 0 ${largeArc} 0 ${e2.x} ${e2.y}`,
            'Z',
        ].join(' ');
    };

    let cumulativeDeg = -90;
    const segments = categories.map((cat, i) => {
        const fraction = cat.spent / safeTotal;
        const isLast = i === categories.length - 1;
        const sweepDeg = isLast ? (270 - cumulativeDeg) : fraction * 360;
        const startDeg = cumulativeDeg;
        const endDeg = cumulativeDeg + sweepDeg;
        const midDeg = startDeg + sweepDeg / 2;
        const catStyle = getCatStyle(cat.lean_category);

        const seg = {
            ...cat,
            startDeg,
            endDeg,
            midDeg,
            d: arcPath(startDeg, endDeg),
            fillColor: catStyle.icon,
            fillBg: catStyle.bg,
        };
        cumulativeDeg = endDeg;
        return seg;
    });

    return (
        <View style={donutStyles.container}>
            <Svg width={size} height={size}>
                {segments.map((seg, i) => (
                    <Path key={i} d={seg.d} fill={seg.fillColor} />
                ))}
            </Svg>

            {/* Center label */}
            <View style={donutStyles.centerLabel}>
                <Text style={donutStyles.centerSubtext}>Total spend</Text>
                <Text style={donutStyles.centerSubtext}>in {monthName}</Text>
                <Text
                    style={donutStyles.centerAmount}
                    adjustsFontSizeToFit
                    numberOfLines={1}
                >
                    {Math.round(totalSpend).toLocaleString()}
                </Text>
            </View>

            {/* Floating category icons at segment midpoints */}
            {segments.map((seg, i) => {
                const midRad = (seg.midDeg * Math.PI) / 180;
                const x = center + iconR * Math.cos(midRad);
                const y = center + iconR * Math.sin(midRad);
                return (
                    <View
                        key={`icon-${i}`}
                        style={[
                            donutStyles.floatingIcon,
                            {
                                left: x - 18,
                                top: y - 18,
                                backgroundColor: seg.fillBg,
                            },
                        ]}
                    >
                        <CatIcon
                            leanCategory={seg.lean_category}
                            size={28}
                            bgOverride="transparent"
                            iconOverride={seg.fillColor}
                        />
                    </View>
                );
            })}
        </View>
    );
};

const donutStyles = StyleSheet.create({
    container: {
        width: 260,
        height: 260,
        alignSelf: 'center',
        marginTop: 20,
        marginBottom: 30,
        overflow: 'visible',
    },
    centerLabel: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        justifyContent: 'center',
        alignItems: 'center',
    },
    centerSubtext: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '500',
        color: '#8B8D97',
        lineHeight: 17,
    },
    centerAmount: {
        fontFamily: 'Inter',
        fontSize: 36,
        fontWeight: '700',
        color: '#1A1D2E',
        marginTop: 4,
        letterSpacing: -0.5,
        maxWidth: 140,
        textAlign: 'center',
    },
    floatingIcon: {
        position: 'absolute',
        width: 36,
        height: 36,
        borderRadius: 18,
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
        elevation: 3,
    },
});

/* ------------------------------------------------------------------ */
/*  Main Budget Screen                                                */
/* ------------------------------------------------------------------ */

export const BudgetScreen: React.FC<BudgetScreenProps> = ({ userId }) => {
    const { summary, isLoading, isReady, error, fetchData, refresh } =
        useBudget(userId);

    useEffect(() => {
        fetchData();
    }, []);

    if (isLoading && !isReady) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#6366F1" />
                <Text style={styles.loadingText}>Loading budget...</Text>
            </View>
        );
    }

    if (error && !isReady) {
        return (
            <View style={styles.loadingContainer}>
                <Text style={{ fontSize: 48 }}>😕</Text>
                <Text style={styles.errorText}>{error}</Text>
            </View>
        );
    }

    if (!summary) {
        return (
            <View style={styles.loadingContainer}>
                <Text style={{ fontSize: 48 }}>📊</Text>
                <Text style={styles.loadingText}>No budget data yet</Text>
            </View>
        );
    }

    const topCategories = summary.categories.slice(0, 5);

    return (
        <ScrollView
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            refreshControl={
                <RefreshControl
                    refreshing={isLoading && isReady}
                    onRefresh={() => refresh()}
                    tintColor="#6366F1"
                />
            }
        >
            {/* Section 1: Month Header */}
            <Text style={styles.sectionHeader}>
                {summary.month_name.toUpperCase()} BUDGET
            </Text>

            {/* Section 2: Left for Spending Card */}
            <View style={styles.card}>
                <View style={styles.cardInner}>
                    <Text style={styles.leftLabel}>LEFT FOR SPENDING</Text>
                    <View style={styles.amountRow}>
                        <Text style={styles.bigAmount}>
                            {Math.round(summary.left_for_spending).toLocaleString()}
                        </Text>
                        <Text style={styles.currencyLabel}>AED</Text>
                    </View>
                    <View style={styles.progressBarBg}>
                        <View
                            style={[
                                styles.progressBarFill,
                                { width: `${Math.min(summary.budget_progress, 100)}%` },
                            ]}
                        />
                    </View>
                </View>
            </View>

            {/* Section 3: Fixed / Flexible / Savings Breakdown */}
            <View style={styles.card}>
                <View style={styles.breakdownInner}>
                    <BucketRow
                        iconName="receipt"
                        label={summary.fixed.label}
                        status={summary.fixed.status}
                        amount={Math.round(summary.fixed.spent)}
                        subtitle={summary.fixed.subtitle}
                        progress={summary.fixed.progress}
                    />
                    <View style={styles.divider} />
                    <BucketRow
                        iconName="shopping-bag"
                        label={summary.flexible.label}
                        status={summary.flexible.status}
                        amount={Math.round(summary.flexible.spent)}
                        subtitle={`of ${Math.round(summary.flexible.budget).toLocaleString()} spent`}
                        progress={summary.flexible.progress}
                    />
                    <View style={styles.divider} />
                    <BucketRow
                        iconName="piggy-bank"
                        label={summary.savings.label}
                        status={summary.savings.status}
                        amount={Math.round(summary.savings.remaining ?? summary.savings.budget)}
                        subtitle={summary.savings.subtitle}
                        progress={summary.savings.progress}
                    />
                </View>
            </View>

            {/* Section 4: Update Your Budget CTA */}
            <TouchableOpacity style={styles.updateCard} activeOpacity={0.7}>
                <View style={styles.updateInner}>
                    <View style={styles.updateLeft}>
                        <View style={styles.editIconBox}>
                            <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
                                <Path
                                    d="M17 3a2.828 2.828 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"
                                    stroke="#1A1D2E"
                                    strokeWidth={2}
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                />
                            </Svg>
                        </View>
                        <View style={styles.updateTextWrap}>
                            <Text style={styles.updateTitle}>Update Your Budget</Text>
                            <Text style={styles.updateSubtitle}>
                                Adjust your spending plan and goals for this month
                            </Text>
                        </View>
                    </View>
                    <View style={styles.chevronBox}>
                        <Svg width={16} height={16} viewBox="0 0 24 24" fill="none">
                            <Path
                                d="M9 18l6-6-6-6"
                                stroke="#8B8D97"
                                strokeWidth={2.5}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                        </Svg>
                    </View>
                </View>
            </TouchableOpacity>

            {/* Section 5: Breakdown (donut + category list) */}
            <Text style={styles.sectionHeader}>BREAKDOWN</Text>

            <View style={styles.card}>
                <View style={styles.breakdownChartInner}>
                    {topCategories.length > 0 && (
                        <DonutChart
                            categories={topCategories}
                            totalSpend={summary.total_category_spend}
                            monthName={summary.month_name}
                        />
                    )}

                    <View style={styles.divider} />

                    {topCategories.map((cat, i) => (
                        <View key={cat.lean_category} style={i > 0 ? { marginTop: 16 } : undefined}>
                            <CategoryRow category={cat} />
                        </View>
                    ))}
                </View>
            </View>

            <View style={{ height: 24 }} />
        </ScrollView>
    );
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                    */
/* ------------------------------------------------------------------ */

const BucketRow: React.FC<{
    iconName: string;
    label: string;
    status: string;
    amount: number;
    subtitle: string;
    progress: number;
}> = ({ iconName, label, status, amount, subtitle, progress }) => (
    <View>
        <View style={styles.bucketHeader}>
            <View style={styles.bucketLeft}>
                <BucketIcon name={iconName} />
                <View>
                    <Text style={styles.bucketLabel}>{label}</Text>
                    <Text style={styles.bucketStatus}>{status}</Text>
                </View>
            </View>
            <View style={styles.bucketRight}>
                <Text style={styles.bucketAmount}>{amount.toLocaleString()}</Text>
                <Text style={styles.bucketSubtitle}>{subtitle}</Text>
            </View>
        </View>
        <View style={styles.progressBarBgSmall}>
            <View
                style={[
                    styles.progressBarFillIndigo,
                    { width: `${Math.min(progress, 100)}%` },
                ]}
            />
        </View>
    </View>
);

const CategoryRow: React.FC<{ category: CategoryBreakdown }> = ({ category }) => {
    const pctUsed = category.budget > 0
        ? (category.spent / category.budget) * 100
        : 0;
    const remaining = Math.max(category.budget - category.spent, 0);
    const catStyle = getCatStyle(category.lean_category);
    return (
        <View>
            <View style={styles.catHeader}>
                <View style={styles.catLeft}>
                    <CatIcon leanCategory={category.lean_category} size={32} />
                    <Text style={styles.catName}>{category.display_name}</Text>
                </View>
                <Text style={styles.catAmount}>
                    AED {Math.round(category.spent).toLocaleString()}
                </Text>
            </View>
            <View style={styles.catBarBg}>
                <View
                    style={[
                        styles.catBarFill,
                        {
                            width: `${Math.min(pctUsed, 100)}%`,
                            backgroundColor: catStyle.icon,
                        },
                    ]}
                />
            </View>
            <View style={styles.catInfo}>
                <Text style={styles.catInfoText}>
                    {Math.round(pctUsed)}% of AED {Math.round(category.budget).toLocaleString()}
                </Text>
                <Text style={styles.catInfoText}>
                    AED {Math.round(remaining).toLocaleString()} left
                </Text>
            </View>
        </View>
    );
};

/* ------------------------------------------------------------------ */
/*  Styles                                                            */
/* ------------------------------------------------------------------ */

const styles = StyleSheet.create({
    scrollView: {
        flex: 1,
        backgroundColor: '#F7F8FA',
    },
    scrollContent: {
        paddingHorizontal: 20,
        paddingTop: 8,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#F7F8FA',
        paddingHorizontal: 40,
    },
    loadingText: {
        fontFamily: 'Inter',
        fontSize: 16,
        fontWeight: '600',
        color: '#1A1D2E',
        marginTop: 16,
    },
    errorText: {
        fontFamily: 'Inter',
        fontSize: 14,
        color: '#EF4444',
        marginTop: 12,
        textAlign: 'center',
    },

    sectionHeader: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
        letterSpacing: 0.8,
        marginBottom: 14,
        marginTop: 24,
        paddingHorizontal: 2,
    },

    card: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.04,
        shadowRadius: 4,
        elevation: 2,
        marginBottom: 16,
        overflow: 'hidden',
    },
    cardInner: {
        paddingHorizontal: 20,
        paddingTop: 16,
        paddingBottom: 16,
    },

    leftLabel: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '500',
        color: '#8B8D97',
        letterSpacing: 0.8,
        marginBottom: 6,
        textTransform: 'uppercase',
    },
    amountRow: {
        flexDirection: 'row',
        alignItems: 'baseline',
        gap: 8,
        marginBottom: 12,
    },
    bigAmount: {
        fontFamily: 'Inter',
        fontSize: 36,
        fontWeight: '600',
        color: '#1A1D2E',
        letterSpacing: -1,
    },
    currencyLabel: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '500',
        color: '#B0B3BE',
        marginBottom: 4,
    },

    progressBarBg: {
        width: '100%',
        height: 6,
        backgroundColor: '#F0F1F3',
        borderRadius: 3,
        overflow: 'hidden',
    },
    progressBarFill: {
        height: '100%',
        backgroundColor: '#6366F1',
        borderRadius: 3,
    },
    progressBarBgSmall: {
        width: '100%',
        height: 6,
        backgroundColor: '#F7F8FA',
        borderRadius: 3,
        overflow: 'hidden',
    },
    progressBarFillIndigo: {
        height: '100%',
        backgroundColor: '#6366F1',
        borderRadius: 3,
    },

    breakdownInner: {
        paddingHorizontal: 20,
        paddingVertical: 20,
    },
    breakdownChartInner: {
        paddingHorizontal: 20,
        paddingVertical: 20,
    },
    divider: {
        height: 1,
        backgroundColor: '#F0F1F3',
        marginVertical: 20,
    },

    bucketHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    bucketLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    iconCircle: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: '#F9FAFB',
        justifyContent: 'center',
        alignItems: 'center',
    },
    bucketLabel: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '600',
        color: '#1A1D2E',
    },
    bucketStatus: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '500',
        color: '#8B8D97',
        marginTop: 1,
    },
    bucketRight: {
        alignItems: 'flex-end',
    },
    bucketAmount: {
        fontFamily: 'Inter',
        fontSize: 20,
        fontWeight: '700',
        color: '#1A1D2E',
    },
    bucketSubtitle: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '500',
        color: '#8B8D97',
        marginTop: 1,
    },

    updateCard: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        borderWidth: 2,
        borderStyle: 'dashed',
        borderColor: '#3F4451',
        marginBottom: 8,
        overflow: 'hidden',
    },
    updateInner: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        paddingVertical: 16,
        gap: 16,
    },
    updateLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        flex: 1,
    },
    editIconBox: {
        width: 44,
        height: 44,
        borderRadius: 12,
        backgroundColor: '#F3F4F6',
        justifyContent: 'center',
        alignItems: 'center',
    },
    updateTextWrap: {
        flex: 1,
    },
    updateTitle: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '600',
        color: '#1A1D2E',
        marginBottom: 4,
    },
    updateSubtitle: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '500',
        color: '#8B8D97',
        lineHeight: 16,
    },
    chevronBox: {
        width: 32,
        height: 32,
        borderRadius: 8,
        backgroundColor: '#F7F8FA',
        justifyContent: 'center',
        alignItems: 'center',
    },

    catHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    catLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    catName: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        color: '#1A1D2E',
    },
    catAmount: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
    },
    catBarBg: {
        width: '100%',
        height: 6,
        backgroundColor: '#F0F1F3',
        borderRadius: 3,
        overflow: 'hidden',
        marginBottom: 6,
    },
    catBarFill: {
        height: '100%',
        borderRadius: 3,
    },
    catInfo: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    catInfoText: {
        fontFamily: 'Inter',
        fontSize: 10,
        fontWeight: '500',
        color: '#8B8D97',
    },
});
