/**
 * TransactionsScreen — Full transactions page.
 *
 * Sections:
 * 1. UPCOMING TRANSACTIONS — full-month calendar + upcoming payments
 * 2. TRANSACTION HISTORY — date-filtered, grouped (All / Flexible / Fixed)
 * 3. TOP MERCHANTS — top 5 merchants by spend
 * 4. LARGEST PURCHASES — top 5 individual transactions
 *
 * Uses shared CatIcon from mobile/shared/categoryStyles.tsx
 * for consistent icons across the entire app.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    ActivityIndicator,
    RefreshControl,
    TouchableOpacity,
    TextInput,
    Modal,
} from 'react-native';
import Svg, { Path, Circle as SvgCircle } from 'react-native-svg';
import { CatIcon } from '../../../shared/categoryStyles';
import { useTransactions } from '../hooks/useTransactions';
import {
    TransactionEntry,
    TransactionGroup,
    UpcomingPayment,
    TopMerchant,
    LargestPurchase,
    DateRange,
} from '../types';

interface TransactionsScreenProps {
    userId: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

const MONTHS = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December',
];
const DAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

function getDaysInMonth(year: number, month: number): number {
    return new Date(year, month + 1, 0).getDate();
}
function getFirstDayOffset(year: number, month: number): number {
    return new Date(year, month, 1).getDay();
}
function pad2(n: number): string {
    return n < 10 ? `0${n}` : `${n}`;
}
function formatDateStr(y: number, m: number, d: number): string {
    return `${y}-${pad2(m + 1)}-${pad2(d)}`;
}
function shortMonth(m: number): string {
    return MONTHS[m].slice(0, 3);
}

function getDefaultDateRange(): DateRange {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth();
    const dim = getDaysInMonth(y, m);
    return {
        startDate: formatDateStr(y, m, 1),
        endDate: formatDateStr(y, m, dim),
    };
}

function formatRangeLabel(range: DateRange): string {
    const sd = new Date(range.startDate);
    const ed = new Date(range.endDate);
    const sm = shortMonth(sd.getMonth());
    const em = shortMonth(ed.getMonth());
    if (sd.getFullYear() === ed.getFullYear() && sd.getMonth() === ed.getMonth()) {
        return `${sm} ${sd.getDate()} – ${em} ${ed.getDate()}, ${sd.getFullYear()}`;
    }
    return `${sm} ${sd.getDate()} – ${em} ${ed.getDate()}, ${ed.getFullYear()}`;
}

/* ------------------------------------------------------------------ */
/*  Full-Month Calendar Component                                     */
/* ------------------------------------------------------------------ */

const FullMonthCalendar: React.FC<{
    upcoming: {
        display_month: string;
        days_in_month: number;
        first_day_offset: number;
        today_day: number | null;
        upcoming_count: number;
        upcoming_total: number;
    };
    datesWithTx: Set<number>;
    upcomingDays: Set<number>;
    onExpandUpcoming: () => void;
    upcomingExpanded: boolean;
}> = ({ upcoming, datesWithTx, upcomingDays, onExpandUpcoming, upcomingExpanded }) => {
    const now = new Date();
    const [calYear, setCalYear] = useState(now.getFullYear());
    const [calMonth, setCalMonth] = useState(now.getMonth());

    const daysInMonth = getDaysInMonth(calYear, calMonth);
    const firstOffset = getFirstDayOffset(calYear, calMonth);
    const isCurrentMonth = calYear === now.getFullYear() && calMonth === now.getMonth();
    const todayDay = isCurrentMonth ? now.getDate() : null;

    const cells: (number | null)[] = [];
    for (let i = 0; i < firstOffset; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);

    const prevMonth = () => {
        if (calMonth === 0) { setCalYear(calYear - 1); setCalMonth(11); }
        else { setCalMonth(calMonth - 1); }
    };
    const nextMonth = () => {
        if (calMonth === 11) { setCalYear(calYear + 1); setCalMonth(0); }
        else { setCalMonth(calMonth + 1); }
    };

    const txCount = isCurrentMonth ? upcoming.upcoming_count : 0;
    const txTotal = isCurrentMonth ? upcoming.upcoming_total : 0;

    return (
        <View>
            <View style={calStyles.header}>
                <View>
                    <Text style={calStyles.monthTitle}>
                        {MONTHS[calMonth]} {calYear}
                    </Text>
                    {isCurrentMonth && (
                        <Text style={calStyles.subtitle}>
                            {txCount} payment{txCount !== 1 ? 's' : ''} {'\u2022'} AED{' '}
                            {Math.round(txTotal).toLocaleString()}
                        </Text>
                    )}
                </View>
                <View style={calStyles.arrows}>
                    <TouchableOpacity style={calStyles.arrowBtn} onPress={prevMonth}>
                        <Svg width={16} height={16} viewBox="0 0 24 24" fill="none">
                            <Path d="M15 18l-6-6 6-6" stroke="#8B8D97" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                        </Svg>
                    </TouchableOpacity>
                    <TouchableOpacity style={calStyles.arrowBtn} onPress={nextMonth}>
                        <Svg width={16} height={16} viewBox="0 0 24 24" fill="none">
                            <Path d="M9 18l6-6-6-6" stroke="#8B8D97" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                        </Svg>
                    </TouchableOpacity>
                </View>
            </View>

            <View style={calStyles.dayRow}>
                {DAY_LABELS.map((d, i) => (
                    <View key={i} style={calStyles.dayCell}>
                        <Text style={calStyles.dayLabel}>{d}</Text>
                    </View>
                ))}
            </View>

            <View style={calStyles.grid}>
                {cells.map((day, idx) => {
                    const isToday = day === todayDay;
                    const hasTx = day !== null && isCurrentMonth && (datesWithTx.has(day) || upcomingDays.has(day));
                    const isPast = day !== null && todayDay !== null && day < todayDay;
                    return (
                        <View key={idx} style={calStyles.gridCell}>
                            {day !== null ? (
                                <View
                                    style={[
                                        calStyles.dateBtn,
                                        isToday && calStyles.todayBtn,
                                    ]}
                                >
                                    <Text
                                        style={[
                                            calStyles.dateText,
                                            isToday && calStyles.todayText,
                                            isPast && !isToday && calStyles.pastText,
                                        ]}
                                    >
                                        {day}
                                    </Text>
                                    {hasTx && (
                                        <View
                                            style={[
                                                calStyles.dot,
                                                isToday && calStyles.dotWhite,
                                            ]}
                                        />
                                    )}
                                </View>
                            ) : (
                                <View style={calStyles.dateBtn} />
                            )}
                        </View>
                    );
                })}
            </View>
        </View>
    );
};

const calStyles = StyleSheet.create({
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 16,
    },
    monthTitle: {
        fontFamily: 'Inter',
        fontSize: 16,
        fontWeight: '600',
        color: '#1A1D2E',
        marginBottom: 4,
    },
    subtitle: {
        fontFamily: 'Inter',
        fontSize: 12,
        color: '#8B8D97',
    },
    arrows: {
        flexDirection: 'row',
        gap: 4,
    },
    arrowBtn: {
        width: 32,
        height: 32,
        borderRadius: 8,
        backgroundColor: '#F9FAFB',
        justifyContent: 'center',
        alignItems: 'center',
    },
    dayRow: {
        flexDirection: 'row',
        marginBottom: 4,
    },
    dayCell: {
        flex: 1,
        alignItems: 'center',
        paddingVertical: 4,
    },
    dayLabel: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '600',
        color: '#8B8D97',
    },
    grid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
    },
    gridCell: {
        width: '14.28%',
        aspectRatio: 1,
        padding: 2,
    },
    dateBtn: {
        flex: 1,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    todayBtn: {
        backgroundColor: '#4F6BFF',
    },
    dateText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        color: '#1A1D2E',
    },
    todayText: {
        color: '#FFFFFF',
        fontWeight: '700',
    },
    pastText: {
        color: '#C4C7CF',
    },
    dot: {
        position: 'absolute',
        bottom: 5,
        width: 5,
        height: 5,
        borderRadius: 2.5,
        backgroundColor: '#4F6BFF',
    },
    dotWhite: {
        backgroundColor: '#FFFFFF',
    },
});

/* ------------------------------------------------------------------ */
/*  Chevron Down Icon                                                 */
/* ------------------------------------------------------------------ */

const ChevronDown: React.FC<{ rotated?: boolean }> = ({ rotated }) => (
    <Svg
        width={16}
        height={16}
        viewBox="0 0 24 24"
        fill="none"
        style={rotated ? { transform: [{ rotate: '180deg' }] } : undefined}
    >
        <Path
            d="M6 9l6 6 6-6"
            stroke="#8B8D97"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    </Svg>
);

/* ------------------------------------------------------------------ */
/*  Expandable Transaction Group                                      */
/* ------------------------------------------------------------------ */

const TransactionGroupSection: React.FC<{
    group: TransactionGroup;
    defaultExpanded?: boolean;
    isLast?: boolean;
}> = ({ group, defaultExpanded = false, isLast = false }) => {
    const [expanded, setExpanded] = useState(defaultExpanded);

    return (
        <View>
            <TouchableOpacity
                style={[styles.groupHeader, !isLast && styles.groupHeaderBorder]}
                onPress={() => setExpanded(!expanded)}
                activeOpacity={0.7}
            >
                <View style={styles.groupLeft}>
                    <Text style={styles.groupLabel}>{group.label}</Text>
                    <Text style={styles.groupCount}>{group.count}</Text>
                </View>
                <View style={styles.groupRight}>
                    <Text style={styles.groupTotal}>
                        AED {Math.round(group.total).toLocaleString()}
                    </Text>
                    <ChevronDown rotated={expanded} />
                </View>
            </TouchableOpacity>

            {expanded && group.transactions.map((tx, i) => (
                <View
                    key={tx.transaction_id}
                    style={[
                        styles.txRow,
                        i < group.transactions.length - 1 && styles.txRowBorder,
                    ]}
                >
                    <CatIcon leanCategory={tx.lean_category} size={40} />
                    <View style={styles.txInfo}>
                        <Text style={styles.txName} numberOfLines={1}>{tx.merchant_name}</Text>
                        <Text style={styles.txSub}>
                            {tx.category} {'\u00B7'} {tx.date}
                        </Text>
                    </View>
                    <Text style={styles.txAmount}>
                        AED {Math.round(tx.amount).toLocaleString()}
                    </Text>
                </View>
            ))}
        </View>
    );
};

/* ------------------------------------------------------------------ */
/*  Date Range Picker Modal                                           */
/* ------------------------------------------------------------------ */

const DateRangePicker: React.FC<{
    visible: boolean;
    onClose: () => void;
    onApply: (range: DateRange) => void;
    initialRange: DateRange;
}> = ({ visible, onClose, onApply, initialRange }) => {
    const now = new Date();
    const [pickerYear, setPickerYear] = useState(now.getFullYear());
    const [pickerMonth, setPickerMonth] = useState(now.getMonth());
    const [startDate, setStartDate] = useState<string | null>(initialRange.startDate);
    const [endDate, setEndDate] = useState<string | null>(initialRange.endDate);

    const daysInMonth = getDaysInMonth(pickerYear, pickerMonth);
    const firstOffset = getFirstDayOffset(pickerYear, pickerMonth);
    const cells: (number | null)[] = [];
    for (let i = 0; i < firstOffset; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);

    const prevMonth = () => {
        if (pickerMonth === 0) { setPickerYear(pickerYear - 1); setPickerMonth(11); }
        else { setPickerMonth(pickerMonth - 1); }
    };
    const nextMonth = () => {
        if (pickerMonth === 11) { setPickerYear(pickerYear + 1); setPickerMonth(0); }
        else { setPickerMonth(pickerMonth + 1); }
    };

    const onDayPress = (day: number) => {
        const dateStr = formatDateStr(pickerYear, pickerMonth, day);
        if (!startDate || (startDate && endDate)) {
            setStartDate(dateStr);
            setEndDate(null);
        } else {
            if (dateStr < startDate) {
                setEndDate(startDate);
                setStartDate(dateStr);
            } else {
                setEndDate(dateStr);
            }
        }
    };

    const isInRange = (day: number): boolean => {
        if (!startDate || !endDate) return false;
        const d = formatDateStr(pickerYear, pickerMonth, day);
        return d > startDate && d < endDate;
    };
    const isStart = (day: number): boolean => {
        return formatDateStr(pickerYear, pickerMonth, day) === startDate;
    };
    const isEnd = (day: number): boolean => {
        return formatDateStr(pickerYear, pickerMonth, day) === endDate;
    };

    const handleApply = () => {
        if (startDate && endDate) {
            onApply({ startDate, endDate });
        } else if (startDate) {
            onApply({ startDate, endDate: startDate });
        }
    };

    const handleReset = () => {
        const def = getDefaultDateRange();
        setStartDate(def.startDate);
        setEndDate(def.endDate);
        onApply(def);
    };

    return (
        <Modal visible={visible} transparent animationType="slide">
            <View style={pickerStyles.overlay}>
                <View style={pickerStyles.sheet}>
                    <View style={pickerStyles.handle} />
                    <Text style={pickerStyles.title}>Select Date Range</Text>

                    <View style={pickerStyles.navRow}>
                        <TouchableOpacity onPress={prevMonth}>
                            <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
                                <Path d="M15 18l-6-6 6-6" stroke="#1A1D2E" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                            </Svg>
                        </TouchableOpacity>
                        <Text style={pickerStyles.navTitle}>
                            {MONTHS[pickerMonth]} {pickerYear}
                        </Text>
                        <TouchableOpacity onPress={nextMonth}>
                            <Svg width={20} height={20} viewBox="0 0 24 24" fill="none">
                                <Path d="M9 18l6-6-6-6" stroke="#1A1D2E" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                            </Svg>
                        </TouchableOpacity>
                    </View>

                    <View style={pickerStyles.dayHeaderRow}>
                        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d, i) => (
                            <View key={i} style={pickerStyles.dayHeaderCell}>
                                <Text style={pickerStyles.dayHeaderText}>{d}</Text>
                            </View>
                        ))}
                    </View>

                    <View style={pickerStyles.grid}>
                        {cells.map((day, idx) => {
                            if (day === null) {
                                return <View key={idx} style={pickerStyles.gridCell} />;
                            }
                            const start = isStart(day);
                            const end = isEnd(day);
                            const inRange = isInRange(day);
                            return (
                                <TouchableOpacity
                                    key={idx}
                                    style={[
                                        pickerStyles.gridCell,
                                        inRange && pickerStyles.inRangeCell,
                                        start && pickerStyles.startRangeCell,
                                        end && pickerStyles.endRangeCell,
                                    ]}
                                    onPress={() => onDayPress(day)}
                                    activeOpacity={0.6}
                                >
                                    <View
                                        style={[
                                            pickerStyles.dayBtn,
                                            (start || end) && pickerStyles.selectedDayBtn,
                                        ]}
                                    >
                                        <Text
                                            style={[
                                                pickerStyles.dayText,
                                                (start || end) && pickerStyles.selectedDayText,
                                            ]}
                                        >
                                            {day}
                                        </Text>
                                    </View>
                                </TouchableOpacity>
                            );
                        })}
                    </View>

                    <View style={pickerStyles.actions}>
                        <TouchableOpacity style={pickerStyles.resetBtn} onPress={handleReset}>
                            <Text style={pickerStyles.resetText}>Reset</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={pickerStyles.applyBtn} onPress={handleApply}>
                            <Text style={pickerStyles.applyText}>Apply</Text>
                        </TouchableOpacity>
                    </View>

                    <TouchableOpacity style={pickerStyles.closeBtn} onPress={onClose}>
                        <Text style={pickerStyles.closeText}>Cancel</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </Modal>
    );
};

const pickerStyles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.4)',
        justifyContent: 'flex-end',
    },
    sheet: {
        backgroundColor: '#FFFFFF',
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        padding: 20,
        paddingBottom: 40,
    },
    handle: {
        width: 40,
        height: 4,
        borderRadius: 2,
        backgroundColor: '#D1D5DB',
        alignSelf: 'center',
        marginBottom: 16,
    },
    title: {
        fontFamily: 'Inter',
        fontSize: 18,
        fontWeight: '600',
        color: '#1A1D2E',
        textAlign: 'center',
        marginBottom: 20,
    },
    navRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
        paddingHorizontal: 4,
    },
    navTitle: {
        fontFamily: 'Inter',
        fontSize: 16,
        fontWeight: '600',
        color: '#1A1D2E',
    },
    dayHeaderRow: {
        flexDirection: 'row',
        marginBottom: 8,
    },
    dayHeaderCell: {
        flex: 1,
        alignItems: 'center',
    },
    dayHeaderText: {
        fontFamily: 'Inter',
        fontSize: 12,
        fontWeight: '600',
        color: '#8B8D97',
    },
    grid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
    },
    gridCell: {
        width: '14.28%',
        height: 44,
        justifyContent: 'center',
        alignItems: 'center',
    },
    inRangeCell: {
        backgroundColor: '#EBF0FF',
    },
    startRangeCell: {
        backgroundColor: '#EBF0FF',
        borderTopLeftRadius: 22,
        borderBottomLeftRadius: 22,
    },
    endRangeCell: {
        backgroundColor: '#EBF0FF',
        borderTopRightRadius: 22,
        borderBottomRightRadius: 22,
    },
    dayBtn: {
        width: 36,
        height: 36,
        borderRadius: 18,
        justifyContent: 'center',
        alignItems: 'center',
    },
    selectedDayBtn: {
        backgroundColor: '#4F6BFF',
    },
    dayText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '500',
        color: '#1A1D2E',
    },
    selectedDayText: {
        color: '#FFFFFF',
        fontWeight: '700',
    },
    actions: {
        flexDirection: 'row',
        gap: 12,
        marginTop: 20,
    },
    resetBtn: {
        flex: 1,
        height: 48,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#D1D5DB',
        justifyContent: 'center',
        alignItems: 'center',
    },
    resetText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        color: '#6B7280',
    },
    applyBtn: {
        flex: 1,
        height: 48,
        borderRadius: 12,
        backgroundColor: '#4F6BFF',
        justifyContent: 'center',
        alignItems: 'center',
    },
    applyText: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        color: '#FFFFFF',
    },
    closeBtn: {
        marginTop: 12,
        alignItems: 'center',
    },
    closeText: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '500',
        color: '#8B8D97',
    },
});

/* ------------------------------------------------------------------ */
/*  Main Transactions Screen                                          */
/* ------------------------------------------------------------------ */

export const TransactionsScreen: React.FC<TransactionsScreenProps> = ({ userId }) => {
    const {
        upcoming,
        allTransactions,
        topMerchants,
        largestPurchases,
        isLoading,
        isReady,
        error,
        fetchData,
        fetchFiltered,
        refresh,
        searchTransactions,
    } = useTransactions(userId);

    const [searchQuery, setSearchQuery] = useState('');
    const [upcomingExpanded, setUpcomingExpanded] = useState(false);
    const [dateRange, setDateRange] = useState<DateRange>(getDefaultDateRange);
    const [pickerVisible, setPickerVisible] = useState(false);
    const searchTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        fetchData(dateRange);
    }, []);

    const handleSearch = useCallback(
        (text: string) => {
            setSearchQuery(text);
            if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
            searchTimerRef.current = setTimeout(() => {
                searchTransactions(text, dateRange);
            }, 300);
        },
        [searchTransactions, dateRange]
    );

    const handleDateRangeApply = useCallback(
        (range: DateRange) => {
            setDateRange(range);
            setPickerVisible(false);
            setSearchQuery('');
            fetchFiltered(range);
        },
        [fetchFiltered]
    );

    if (isLoading && !isReady) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#6366F1" />
                <Text style={styles.loadingText}>Loading transactions...</Text>
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

    const datesWithTx = new Set(
        (upcoming?.dates_with_transactions ?? []).map((d) => d.day)
    );
    const upcomingDays = new Set(
        (upcoming?.upcoming_payments ?? [])
            .map((p) => p.typical_day_of_month)
            .filter((d): d is number => d !== null)
    );

    return (
        <ScrollView
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            refreshControl={
                <RefreshControl
                    refreshing={isLoading && isReady}
                    onRefresh={() => refresh(dateRange)}
                    tintColor="#6366F1"
                />
            }
        >
            {/* Section 1: Upcoming Transactions */}
            <Text style={styles.sectionHeader}>UPCOMING TRANSACTIONS</Text>

            <View style={styles.card}>
                {upcoming && (
                    <View style={styles.calendarInner}>
                        <FullMonthCalendar
                            upcoming={{
                                display_month: upcoming.display_month,
                                days_in_month: upcoming.days_in_month,
                                first_day_offset: upcoming.first_day_offset,
                                today_day: upcoming.today_day,
                                upcoming_count: upcoming.upcoming_count,
                                upcoming_total: upcoming.upcoming_total,
                            }}
                            datesWithTx={datesWithTx}
                            upcomingDays={upcomingDays}
                            onExpandUpcoming={() => setUpcomingExpanded(!upcomingExpanded)}
                            upcomingExpanded={upcomingExpanded}
                        />
                    </View>
                )}

                <TouchableOpacity
                    style={styles.upcomingToggle}
                    onPress={() => setUpcomingExpanded(!upcomingExpanded)}
                    activeOpacity={0.7}
                >
                    <Text style={styles.upcomingToggleText}>
                        {upcoming?.upcoming_count ?? 0} upcoming payment
                        {(upcoming?.upcoming_count ?? 0) !== 1 ? 's' : ''}
                    </Text>
                    <ChevronDown rotated={upcomingExpanded} />
                </TouchableOpacity>

                {upcomingExpanded && (
                    <View style={styles.upcomingList}>
                        {(upcoming?.upcoming_payments ?? []).map((payment, i) => (
                            <View key={payment.id}>
                                <UpcomingRow payment={payment} />
                                {i < (upcoming?.upcoming_payments.length ?? 0) - 1 && (
                                    <View style={styles.dividerThin} />
                                )}
                            </View>
                        ))}
                    </View>
                )}
            </View>

            {/* Section 2: Transaction History */}
            <View style={styles.sectionHeaderRow}>
                <View>
                    <Text style={styles.sectionHeader2}>TRANSACTION HISTORY</Text>
                    <Text style={styles.dateRangeLabel}>{formatRangeLabel(dateRange)}</Text>
                </View>
                <TouchableOpacity
                    style={styles.filterBtn}
                    onPress={() => setPickerVisible(true)}
                    activeOpacity={0.7}
                >
                    <Svg width={18} height={18} viewBox="0 0 24 24" fill="none">
                        <Path
                            d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"
                            stroke="#1A1D2E"
                            strokeWidth={2}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </Svg>
                </TouchableOpacity>
            </View>

            <View style={styles.card}>
                <View style={styles.searchContainer}>
                    <View style={styles.searchBar}>
                        <Svg width={16} height={16} viewBox="0 0 24 24" fill="none" style={{ marginRight: 8 }}>
                            <SvgCircle cx={11} cy={11} r={8} stroke="#8B8D97" strokeWidth={2} />
                            <Path d="M21 21l-4.35-4.35" stroke="#8B8D97" strokeWidth={2} strokeLinecap="round" />
                        </Svg>
                        <TextInput
                            style={styles.searchInput}
                            placeholder="Search transactions"
                            placeholderTextColor="#8B8D97"
                            value={searchQuery}
                            onChangeText={handleSearch}
                        />
                        {searchQuery.length > 0 && (
                            <TouchableOpacity onPress={() => handleSearch('')}>
                                <Svg width={16} height={16} viewBox="0 0 24 24" fill="none">
                                    <Path d="M18 6L6 18M6 6l12 12" stroke="#8B8D97" strokeWidth={2} strokeLinecap="round" />
                                </Svg>
                            </TouchableOpacity>
                        )}
                    </View>
                </View>

                {allTransactions && (
                    <>
                        <TransactionGroupSection
                            group={allTransactions.groups.all}
                            defaultExpanded={false}
                        />
                        <TransactionGroupSection
                            group={allTransactions.groups.flexible}
                        />
                        <TransactionGroupSection
                            group={allTransactions.groups.fixed}
                            isLast={true}
                        />
                    </>
                )}
            </View>

            {/* Section 3: Top Merchants */}
            <Text style={styles.sectionHeader}>TOP MERCHANTS</Text>

            <View style={styles.card}>
                <View style={styles.merchantList}>
                    {(topMerchants?.merchants ?? []).map((merchant, i) => (
                        <View key={`${merchant.merchant_name}-${i}`}>
                            <MerchantRow merchant={merchant} />
                            {i < (topMerchants?.merchants.length ?? 0) - 1 && (
                                <View style={styles.dividerThin} />
                            )}
                        </View>
                    ))}
                    {(topMerchants?.merchants ?? []).length === 0 && (
                        <Text style={styles.emptyText}>No merchant data</Text>
                    )}
                </View>
            </View>

            {/* Section 4: Largest Purchases */}
            <Text style={styles.sectionHeader}>LARGEST PURCHASES</Text>

            <View style={styles.card}>
                <View style={styles.merchantList}>
                    {(largestPurchases?.purchases ?? []).map((purchase, i) => (
                        <View key={purchase.transaction_id}>
                            <PurchaseRow purchase={purchase} />
                            {i < (largestPurchases?.purchases.length ?? 0) - 1 && (
                                <View style={styles.dividerThin} />
                            )}
                        </View>
                    ))}
                    {(largestPurchases?.purchases ?? []).length === 0 && (
                        <Text style={styles.emptyText}>No purchases in this period</Text>
                    )}
                </View>
            </View>

            <View style={{ height: 24 }} />

            {/* Date Range Picker Modal */}
            <DateRangePicker
                visible={pickerVisible}
                onClose={() => setPickerVisible(false)}
                onApply={handleDateRangeApply}
                initialRange={dateRange}
            />
        </ScrollView>
    );
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                    */
/* ------------------------------------------------------------------ */

const UpcomingRow: React.FC<{ payment: UpcomingPayment }> = ({ payment }) => {
    let dueText = '';
    if (payment.days_until_due === 0) dueText = 'Due today';
    else if (payment.days_until_due === 1) dueText = 'Due tomorrow';
    else if (payment.days_until_due !== null && payment.days_until_due <= 7)
        dueText = `Due in ${payment.days_until_due} days`;
    else if (payment.next_expected_date)
        dueText = `Due ${payment.next_expected_date}`;
    else dueText = 'Upcoming';

    return (
        <View style={styles.upcomingRow}>
            <CatIcon leanCategory={payment.lean_category} size={32} />
            <View style={styles.txInfo}>
                <Text style={styles.upcomingName}>{payment.merchant_name}</Text>
                <Text style={styles.upcomingSub}>{dueText}</Text>
            </View>
            <Text style={styles.upcomingAmount}>
                AED {Math.round(payment.amount).toLocaleString()}
            </Text>
        </View>
    );
};

const MerchantRow: React.FC<{ merchant: TopMerchant }> = ({ merchant }) => (
    <View style={styles.merchantRow}>
        <CatIcon leanCategory={merchant.lean_category} size={36} />
        <View style={styles.txInfo}>
            <Text style={styles.merchantName}>{merchant.merchant_name}</Text>
            <Text style={styles.merchantSub}>
                {merchant.payments} payment{merchant.payments !== 1 ? 's' : ''}
            </Text>
        </View>
        <Text style={styles.merchantAmount}>
            AED {Math.round(merchant.total_spent).toLocaleString()}
        </Text>
    </View>
);

const PurchaseRow: React.FC<{ purchase: LargestPurchase }> = ({ purchase }) => (
    <View style={styles.merchantRow}>
        <CatIcon leanCategory={purchase.lean_category} size={36} />
        <View style={styles.txInfo}>
            <Text style={styles.merchantName}>{purchase.merchant_name}</Text>
            <Text style={styles.merchantSub}>{purchase.date}</Text>
        </View>
        <Text style={styles.merchantAmount}>
            AED {Math.round(purchase.amount).toLocaleString()}
        </Text>
    </View>
);

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
    emptyText: {
        fontFamily: 'Inter',
        fontSize: 13,
        color: '#8B8D97',
        textAlign: 'center',
        paddingVertical: 20,
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
    sectionHeaderRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginTop: 24,
        marginBottom: 14,
        paddingHorizontal: 2,
    },
    sectionHeader2: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
        letterSpacing: 0.8,
    },
    dateRangeLabel: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '500',
        color: '#8B8D97',
        marginTop: 4,
    },
    filterBtn: {
        width: 36,
        height: 36,
        borderRadius: 10,
        backgroundColor: '#F3F4F6',
        justifyContent: 'center',
        alignItems: 'center',
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

    calendarInner: {
        padding: 20,
    },

    upcomingToggle: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderTopWidth: 1,
        borderTopColor: '#F0F1F3',
    },
    upcomingToggleText: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        color: '#8B8D97',
    },

    upcomingList: {
        paddingHorizontal: 16,
        paddingBottom: 12,
    },
    upcomingRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
    },
    upcomingName: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        color: '#1A1D2E',
    },
    upcomingSub: {
        fontFamily: 'Inter',
        fontSize: 10,
        fontWeight: '500',
        color: '#8B8D97',
        marginTop: 2,
    },
    upcomingAmount: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
        marginLeft: 12,
    },

    searchContainer: {
        paddingHorizontal: 20,
        paddingTop: 20,
        paddingBottom: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#F0F1F3',
    },
    searchBar: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#F7F8FA',
        borderWidth: 1,
        borderColor: '#F0F1F3',
        borderRadius: 8,
        height: 40,
        paddingHorizontal: 12,
    },
    searchInput: {
        flex: 1,
        fontFamily: 'Inter',
        fontSize: 13,
        color: '#1A1D2E',
        padding: 0,
    },

    groupHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 16,
    },
    groupHeaderBorder: {
        borderBottomWidth: 1,
        borderBottomColor: '#F0F1F3',
    },
    groupLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    groupLabel: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
    },
    groupCount: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '500',
        color: '#8B8D97',
    },
    groupRight: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    groupTotal: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
    },

    txRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 14,
    },
    txRowBorder: {
        borderBottomWidth: 1,
        borderBottomColor: '#F0F1F3',
    },
    txInfo: {
        flex: 1,
        marginLeft: 12,
    },
    txName: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '500',
        color: '#1A1D2E',
        marginBottom: 2,
    },
    txSub: {
        fontFamily: 'Inter',
        fontSize: 12,
        color: '#8B8D97',
    },
    txAmount: {
        fontFamily: 'Inter',
        fontSize: 15,
        fontWeight: '600',
        color: '#1A1D2E',
        marginLeft: 12,
    },

    merchantList: {
        paddingHorizontal: 16,
        paddingVertical: 12,
    },
    merchantRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
    },
    merchantName: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        color: '#1A1D2E',
    },
    merchantSub: {
        fontFamily: 'Inter',
        fontSize: 10,
        fontWeight: '500',
        color: '#8B8D97',
        marginTop: 2,
    },
    merchantAmount: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '600',
        color: '#1A1D2E',
        marginLeft: 12,
    },

    dividerThin: {
        height: 1,
        backgroundColor: '#F0F1F3',
    },
});
