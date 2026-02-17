/**
 * SpendingCard — Spending total card with area chart and status banner.
 * Design tokens extracted from Figma node 2:2975 & 2:2991.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, {
    Path,
    Line,
    Text as SvgText,
    Defs,
    LinearGradient,
    Stop,
} from 'react-native-svg';
import { DashboardSummary, SpendingTrendResponse } from '../types';

interface SpendingCardProps {
    summary: DashboardSummary;
    spendingTrend: SpendingTrendResponse | null;
}

function formatAmount(val: number): string {
    return Math.round(val).toLocaleString('en-US');
}

// Month abbreviation lookup
const MONTH_ABBR = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function getMonthAbbr(displayMonth: string): string {
    // displayMonth = "January 2026" → month index → "Jan"
    const months: Record<string, number> = { january: 1, february: 2, march: 3, april: 4, may: 5, june: 6, july: 7, august: 8, september: 9, october: 10, november: 11, december: 12 };
    const name = (displayMonth || '').split(' ')[0].toLowerCase();
    return MONTH_ABBR[months[name] || 1];
}

export const SpendingCard: React.FC<SpendingCardProps> = ({
    summary,
    spendingTrend,
}) => {
    const isOverBudget = summary.is_over_budget;
    const monthAbbr = getMonthAbbr(summary.display_month);

    return (
        <View style={styles.card}>
            {/* Heading section */}
            <View style={styles.headingContainer}>
                <View style={styles.amountRow}>
                    <Text style={styles.amountText}>{formatAmount(summary.total_expenses)}</Text>
                    <Text style={styles.currencyText}>AED</Text>
                </View>
                <View style={styles.subRow}>
                    <Text style={styles.budgetText}>
                        <Text style={styles.budgetAmount}>{formatAmount(summary.budget)}</Text>
                        <Text style={styles.budgetLabel}> budget</Text>
                    </Text>
                    <Text style={styles.dotSeparator}>•</Text>
                    <Text style={styles.dayText}>
                        {monthAbbr} {summary.day_of_month} of {summary.days_in_month}
                    </Text>
                </View>
            </View>

            {/* Chart */}
            <View style={styles.chartContainer}>
                <SpendingChart
                    dataPoints={spendingTrend?.data_points || []}
                    budgetTotal={summary.budget}
                    totalSpending={summary.total_expenses}
                    daysInMonth={summary.days_in_month}
                    currentDay={summary.day_of_month}
                />
            </View>

            {/* Status banner */}
            <View style={[styles.statusBanner, isOverBudget ? styles.statusWarning : styles.statusGood]}>
                <View style={styles.statusIconContainer}>
                    <View style={styles.statusIcon}>
                        <Text style={[styles.statusIconText, isOverBudget ? styles.warningIconColor : styles.greenIconColor]}>
                            {isOverBudget ? '!' : '✓'}
                        </Text>
                    </View>
                </View>
                <View style={styles.statusContent}>
                    <View style={styles.statusTopRow}>
                        <Text style={[styles.statusTitle, isOverBudget ? styles.warningText : styles.greenText]}>
                            {isOverBudget ? 'Over budget' : 'Great progress!'}
                        </Text>
                        <Text style={[styles.statusDetails, isOverBudget ? styles.warningText : styles.greenText]}>
                            Details →
                        </Text>
                    </View>
                    <Text style={[styles.statusSubtext, isOverBudget ? styles.warningText : styles.greenText]}>
                        {summary.status_text}
                    </Text>
                </View>
            </View>
        </View>
    );
};

/**
 * SVG Line chart for cumulative daily spending.
 */
const SpendingChart: React.FC<{
    dataPoints: Array<{ day: number; cumulative: number }>;
    budgetTotal: number;
    totalSpending: number;
    daysInMonth: number;
    currentDay: number;
}> = ({ dataPoints, budgetTotal, totalSpending, daysInMonth, currentDay }) => {
    const chartWidth = 260;
    const chartHeight = 90;
    const paddingLeft = 2;
    const paddingRight = 2;
    const paddingTop = 18;   // Extra space so Budget label is never clipped
    const paddingBottom = 16;

    const drawWidth = chartWidth - paddingLeft - paddingRight;
    const drawHeight = chartHeight - paddingTop - paddingBottom;

    if (dataPoints.length === 0) {
        return (
            <View style={{ height: chartHeight, justifyContent: 'center', alignItems: 'center' }}>
                <Text style={{ color: '#9CA3AF', fontSize: 10, fontFamily: 'Inter' }}>No data yet</Text>
            </View>
        );
    }

    // Ensure final data point reflects the actual total spending
    // (trend API cumulative may differ from summary total_expenses)
    const adjustedPoints = dataPoints.map((d, i) => {
        if (i === dataPoints.length - 1 && totalSpending > d.cumulative) {
            return { ...d, cumulative: totalSpending };
        }
        return d;
    });

    // Y-axis: 0 at bottom, max(final cumulative, budget) × 1.1 at top
    const maxCumulative = Math.max(...adjustedPoints.map((d) => d.cumulative), 0);
    const rawMax = Math.max(maxCumulative, budgetTotal);
    const maxVal = rawMax > 0 ? rawMax * 1.1 : 1;

    // Debug — verify chart scaling values
    console.log('[SpendingChart] yAxis debug:', {
        budgetTotal,
        totalSpending,
        trendMaxCumulative: Math.max(...dataPoints.map((d) => d.cumulative), 0),
        adjustedMax: maxCumulative,
        rawMax,
        yMax: maxVal,
        budgetYPct: ((budgetTotal / maxVal) * 100).toFixed(1) + '%',
        spendingYPct: ((maxCumulative / maxVal) * 100).toFixed(1) + '%',
    });

    const xScale = (day: number) => paddingLeft + ((day - 1) / Math.max(daysInMonth - 1, 1)) * drawWidth;
    const yScale = (val: number) => paddingTop + drawHeight - (val / maxVal) * drawHeight;

    // Build spending line path
    const linePath = adjustedPoints
        .map((d, i) => {
            const x = xScale(d.day);
            const y = yScale(d.cumulative);
            return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
        })
        .join(' ');

    // Build area fill path (close to bottom)
    const lastPoint = adjustedPoints[adjustedPoints.length - 1];
    const firstPoint = adjustedPoints[0];
    const bottomY = paddingTop + drawHeight;
    const areaPath = `${linePath} L ${xScale(lastPoint.day).toFixed(1)} ${bottomY.toFixed(1)} L ${xScale(firstPoint.day).toFixed(1)} ${bottomY.toFixed(1)} Z`;

    // Budget line y position
    const budgetY = yScale(budgetTotal);
    // Budget label sits 4px above the line, but never above paddingTop
    const labelY = Math.max(budgetY - 4, paddingTop + 2);

    // FIX 3: Hide end-of-month label if within 3 days of current day
    const lastDataDay = lastPoint.day;
    const showEndLabel = daysInMonth - lastDataDay > 3;

    return (
        <Svg width={chartWidth} height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
            <Defs>
                <LinearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <Stop offset="0%" stopColor="#6366F1" stopOpacity={0.15} />
                    <Stop offset="100%" stopColor="#6366F1" stopOpacity={0.02} />
                </LinearGradient>
            </Defs>

            {/* Area fill */}
            <Path d={areaPath} fill="url(#areaGrad)" />

            {/* Spending line */}
            <Path d={linePath} stroke="#6366F1" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />

            {/* Budget dashed line */}
            <Line
                x1={paddingLeft}
                y1={budgetY}
                x2={chartWidth - paddingRight}
                y2={budgetY}
                stroke="#9CA3AF"
                strokeWidth={1}
                strokeDasharray="4,3"
            />

            {/* Budget label — positioned so it never clips */}
            <SvgText
                x={chartWidth - paddingRight - 4}
                y={labelY}
                fill="#9CA3AF"
                fontSize={10}
                fontWeight="700"
                textAnchor="end"
            >
                Budget
            </SvgText>

            {/* X-axis labels */}
            {dataPoints.length > 0 && (
                <>
                    {/* Current day marker — clamped so it never goes off-frame */}
                    {(() => {
                        const rawX = xScale(lastDataDay);
                        const minX = paddingLeft + 4;
                        const maxX = chartWidth - paddingRight - 4;
                        const clampedX = Math.min(Math.max(rawX, minX), maxX);
                        // Anchor right if near the right edge, left if near left edge
                        const anchor = clampedX >= maxX - 8 ? 'end' : clampedX <= minX + 8 ? 'start' : 'middle';
                        return (
                            <SvgText
                                x={clampedX}
                                y={chartHeight - 2}
                                fill="#9CA3AF"
                                fontSize={10}
                                textAnchor={anchor}
                            >
                                {lastDataDay}
                            </SvgText>
                        );
                    })()}

                    {/* End-of-month marker — hidden when too close to current day */}
                    {showEndLabel && (
                        <SvgText
                            x={chartWidth - paddingRight}
                            y={chartHeight - 2}
                            fill="#9CA3AF"
                            fontSize={10}
                            textAnchor="end"
                        >
                            {daysInMonth}
                        </SvgText>
                    )}
                </>
            )}
        </Svg>
    );
};

const styles = StyleSheet.create({
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
    headingContainer: {
        paddingTop: 20,
        paddingHorizontal: 20,
        gap: 10,
    },
    amountRow: {
        flexDirection: 'row',
        alignItems: 'flex-end',
    },
    amountText: {
        fontFamily: 'Inter',
        fontSize: 44,
        fontWeight: '600',
        lineHeight: 44,
        color: '#1A1D2E',
        letterSpacing: -1.32,
    },
    currencyText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        lineHeight: 22.5,
        color: '#B0B3BE',
        marginLeft: 8,
        marginBottom: 4,
    },
    subRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    budgetText: {
        fontSize: 13,
        lineHeight: 19.5,
    },
    budgetAmount: {
        fontFamily: 'Inter',
        fontWeight: '500',
        color: '#1A1D2E',
    },
    budgetLabel: {
        fontFamily: 'Inter',
        fontWeight: '400',
        color: '#8B8D97',
    },
    dotSeparator: {
        fontFamily: 'Inter',
        fontSize: 16,
        color: '#E5E7EB',
        lineHeight: 24,
    },
    dayText: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '400',
        lineHeight: 19.5,
        color: '#8B8D97',
    },
    chartContainer: {
        marginHorizontal: 20,
        marginTop: 6,
        backgroundColor: '#FAFBFC',
        borderRadius: 14,
        paddingTop: 4,
        paddingHorizontal: 10,
        height: 120,
        justifyContent: 'center',
        alignItems: 'center',
    },
    statusBanner: {
        marginHorizontal: 20,
        marginTop: 16,
        marginBottom: 20,
        borderRadius: 14,
        paddingTop: 14,
        paddingHorizontal: 14,
        paddingBottom: 14,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    statusGood: {
        backgroundColor: '#ECFDF5',
    },
    statusWarning: {
        backgroundColor: '#FEF2F2',
    },
    statusIconContainer: {
        width: 20,
        height: 20,
        borderRadius: 10,
        backgroundColor: '#FFFFFF',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
        elevation: 2,
        justifyContent: 'center',
        alignItems: 'center',
    },
    statusIcon: {
        width: 10,
        height: 10,
        justifyContent: 'center',
        alignItems: 'center',
    },
    statusIconText: {
        fontSize: 8,
        fontWeight: '700',
    },
    greenIconColor: {
        color: '#059669',
    },
    warningIconColor: {
        color: '#DC2626',
    },
    statusContent: {
        flex: 1,
        gap: 2,
    },
    statusTopRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    statusTitle: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '600',
        lineHeight: 18,
    },
    statusDetails: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '600',
        lineHeight: 16.5,
    },
    statusSubtext: {
        fontFamily: 'Inter',
        fontSize: 10.5,
        fontWeight: '400',
        lineHeight: 13.125,
    },
    greenText: {
        color: '#059669',
    },
    warningText: {
        color: '#DC2626',
    },
});
