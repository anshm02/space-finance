/**
 * BudgetCard — "Safe to spend" amount with 3 SVG progress circles.
 * Design tokens from Figma node 72:991.
 *
 * All circles use the same indigo stroke color.
 * Status labels: ON TRACK (0-50%), WATCH IT (51-80%), TIGHT (81-100%), OVER (>100%).
 * Fixed circle = % of bills paid.
 * Flexible circle = % of safe-to-spend used.
 * Savings circle = overspend into savings (0% if under budget).
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import Svg, { Circle as SvgCircle, Path } from 'react-native-svg';
import { DashboardSummary } from '../types';

interface BudgetCardProps {
    summary: DashboardSummary;
    onPressBudgetTab?: () => void;
}

function formatAmount(val: number): string {
    return Math.round(val).toLocaleString('en-US');
}

/** Derive status label from a percentage value */
function getStatusLabel(pct: number): string {
    if (pct > 100) return 'OVER';
    if (pct > 80) return 'TIGHT';
    if (pct > 50) return 'WATCH IT';
    return 'ON TRACK';
}

// ---------------------------------------------------------------------------
//  ProgressCircle — SVG ring with centered percentage
// ---------------------------------------------------------------------------

interface CircleProps {
    label: string;
    pct: number;
    statusLabel: string;
}

const CIRCLE_SIZE = 76;
const STROKE_WIDTH = 6;
const RADIUS = (CIRCLE_SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const PROGRESS_COLOR = '#6366F1'; // indigo-500 — matches Figma ring icon
const TRACK_COLOR = '#F9FAFB';

const ProgressCircle: React.FC<CircleProps> = ({ label, pct, statusLabel }) => {
    const progress = Math.min(pct / 100, 1); // cap visual fill at 100%
    const strokeDashoffset = CIRCUMFERENCE * (1 - progress);
    const displayPct = Math.round(pct);

    return (
        <View style={circleStyles.container}>
            {/* Status label above circle */}
            <Text style={circleStyles.statusLabel}>{statusLabel}</Text>

            {/* SVG circle */}
            <View style={circleStyles.circleWrapper}>
                <Svg width={CIRCLE_SIZE} height={CIRCLE_SIZE}>
                    {/* Track (background ring) */}
                    <SvgCircle
                        cx={CIRCLE_SIZE / 2}
                        cy={CIRCLE_SIZE / 2}
                        r={RADIUS}
                        stroke={TRACK_COLOR}
                        strokeWidth={STROKE_WIDTH}
                        fill="none"
                    />
                    {/* Progress arc — starts at 12 o'clock, fills clockwise */}
                    <SvgCircle
                        cx={CIRCLE_SIZE / 2}
                        cy={CIRCLE_SIZE / 2}
                        r={RADIUS}
                        stroke={PROGRESS_COLOR}
                        strokeWidth={STROKE_WIDTH}
                        fill="none"
                        strokeLinecap="round"
                        strokeDasharray={CIRCUMFERENCE}
                        strokeDashoffset={strokeDashoffset}
                        transform={`rotate(-90 ${CIRCLE_SIZE / 2} ${CIRCLE_SIZE / 2})`}
                    />
                </Svg>
                {/* Percentage text centered */}
                <View style={circleStyles.percentContainer}>
                    <Text style={circleStyles.percentText}>{displayPct}%</Text>
                </View>
            </View>

            {/* Label below circle */}
            <Text style={circleStyles.label}>{label}</Text>
        </View>
    );
};

const circleStyles = StyleSheet.create({
    container: {
        alignItems: 'center',
        gap: 8,
        flex: 1,
    },
    statusLabel: {
        fontFamily: 'Inter',
        fontSize: 10,
        fontWeight: '600',
        lineHeight: 15,
        color: '#8B8D97',
        letterSpacing: 0.25,
        textTransform: 'uppercase',
    },
    circleWrapper: {
        width: CIRCLE_SIZE,
        height: CIRCLE_SIZE,
        justifyContent: 'center',
        alignItems: 'center',
    },
    percentContainer: {
        position: 'absolute',
        justifyContent: 'center',
        alignItems: 'center',
    },
    percentText: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '600',
        lineHeight: 21,
        color: '#1A1D2E',
    },
    label: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        lineHeight: 19.5,
        color: '#1A1D2E',
    },
});

// ---------------------------------------------------------------------------
//  Chevron icon (right-pointing arrow for navigation)
// ---------------------------------------------------------------------------

const ChevronRight: React.FC = () => (
    <Svg width={20} height={20} viewBox="0 0 20 20" fill="none">
        <Path
            d="M7.5 5L12.5 10L7.5 15"
            stroke="#9CA3AF"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    </Svg>
);

// ---------------------------------------------------------------------------
//  BudgetCard component
// ---------------------------------------------------------------------------

export const BudgetCard: React.FC<BudgetCardProps> = ({ summary, onPressBudgetTab }) => {
    const fixedPct = summary.fixed_pct ?? 0;
    const flexiblePct = summary.flexible_pct ?? 0;
    const savingsPct = summary.savings_pct ?? 0;

    // Debug logging — verify API response values
    console.log('[BudgetCard] API values:', {
        monthly_income: summary.monthly_income,
        expected_fixed_bills: summary.expected_fixed_bills,
        savings_allocation: summary.savings_allocation,
        safe_to_spend: summary.safe_to_spend,
        budget: summary.budget,
        flexible_spent: summary.flexible_spent,
        fixed_pct: fixedPct,
        flexible_pct: flexiblePct,
        savings_pct: savingsPct,
        fixed_bills_paid: summary.fixed_bills_paid_count,
        fixed_bills_total: summary.fixed_bills_total_count,
    });

    return (
        <View style={styles.wrapper}>
            {/* Section header — "BUDGET" only, no right-side text */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>BUDGET</Text>
            </View>

            {/* Card */}
            <View style={styles.card}>
                {/* Safe to spend section */}
                <View style={styles.safeSection}>
                    <View style={styles.safeLabelRow}>
                        <Text style={styles.safeLabel}>SAFE TO SPEND</Text>
                    </View>
                    <View style={styles.amountRow}>
                        <Text style={styles.safeAmount}>
                            {formatAmount(summary.safe_to_spend)}
                        </Text>
                        <Text style={styles.safeCurrency}> AED</Text>
                    </View>
                </View>

                {/* Chevron button — top right corner */}
                <TouchableOpacity
                    style={styles.chevronButton}
                    onPress={onPressBudgetTab}
                    activeOpacity={0.6}
                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                    <ChevronRight />
                </TouchableOpacity>

                {/* 3 Progress circles */}
                <View style={styles.circlesRow}>
                    <ProgressCircle
                        label="Fixed"
                        pct={fixedPct}
                        statusLabel={summary.fixed_status_label ?? 'ALL PAID'}
                    />
                    <ProgressCircle
                        label="Flexible"
                        pct={flexiblePct}
                        statusLabel={getStatusLabel(flexiblePct)}
                    />
                    <ProgressCircle
                        label="Savings"
                        pct={savingsPct}
                        statusLabel={getStatusLabel(savingsPct)}
                    />
                </View>
            </View>
        </View>
    );
};

// ---------------------------------------------------------------------------
//  Styles — Figma node 72:991 tokens
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
    wrapper: {
        gap: 14,
    },
    header: {
        flexDirection: 'row',
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
    card: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
        elevation: 3,
        paddingHorizontal: 20,
        paddingTop: 20,
        paddingBottom: 24,
        gap: 24,
    },
    safeSection: {
        gap: 6,
        paddingRight: 32, // space for chevron
    },
    safeLabelRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    safeLabel: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '400',
        lineHeight: 16.5,
        color: '#8B8D97',
        letterSpacing: 0.275,
        textTransform: 'uppercase',
    },
    amountRow: {
        flexDirection: 'row',
        alignItems: 'flex-end',
    },
    safeAmount: {
        fontFamily: 'Inter',
        fontSize: 44,
        fontWeight: '600',
        lineHeight: 44,
        color: '#1A1D2E',
        letterSpacing: -1.32,
    },
    safeCurrency: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        lineHeight: 22.5,
        color: '#B0B3BE',
        marginBottom: 4,
    },
    chevronButton: {
        position: 'absolute',
        top: 16,
        right: 16,
        width: 32,
        height: 32,
        borderRadius: 16,
        justifyContent: 'center',
        alignItems: 'center',
    },
    circlesRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
});
