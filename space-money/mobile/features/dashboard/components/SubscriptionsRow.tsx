/**
 * SubscriptionsRow — Horizontal scrollable recurring-charge cards.
 * Design tokens extracted from Figma node 98-34 (dev mode).
 *
 * Card anatomy (top to bottom):
 *  ┌─────────────────────┐
 *  │  colored banner      │ ~100px, pastel bg, top-rounded
 *  │                     │
 *  │    ┌──────────┐     │
 *  │    │  avatar   │     │ 64px circle, 4px white ring, overlaps banner/body
 *  │    └──────────┘     │
 *  │  Merchant Name      │ 14px regular, centered
 *  │  AED 29             │ 18px bold, centered
 *  │  ┌─ IN 3 DAYS ─┐   │ pill badge, centered
 *  └─────────────────────┘
 */

import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { Subscription } from '../types';

interface SubscriptionsRowProps {
    subscriptions: Subscription[];
    totalMonthlyCost: number;
}

function formatAmount(val: number): string {
    return Math.round(val).toLocaleString('en-US');
}

/** Title-case conversion: "SPOTIFY PREMIUM" → "Spotify Premium" */
function toTitleCase(name: string): string {
    return name
        .toLowerCase()
        .split(/[\s_-]+/)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

// ── Color palettes ──────────────────────────────────────────────────
// Strong saturated colors for the avatar circle:
const AVATAR_COLORS: Record<string, string> = {
    A: '#6366F1', B: '#8B5CF6', C: '#EC4899', D: '#EF4444',
    E: '#F97316', F: '#F59E0B', G: '#10B981', H: '#14B8A6',
    I: '#06B6D4', J: '#3B82F6', K: '#0EA5E9', L: '#A855F7',
    M: '#6366F1', N: '#8B5CF6', O: '#EC4899', P: '#EF4444',
    Q: '#F97316', R: '#F59E0B', S: '#10B981', T: '#14B8A6',
    U: '#06B6D4', V: '#3B82F6', W: '#0EA5E9', X: '#A855F7',
    Y: '#6366F1', Z: '#8B5CF6',
};

// Soft pastel tints used for the card's top banner:
const BANNER_COLORS: Record<string, string> = {
    A: '#E0E7FF', B: '#EDE9FE', C: '#FCE7F3', D: '#FEE2E2',
    E: '#FFEDD5', F: '#FEF3C7', G: '#D1FAE5', H: '#CCFBF1',
    I: '#CFFAFE', J: '#DBEAFE', K: '#E0F2FE', L: '#F3E8FF',
    M: '#E0E7FF', N: '#EDE9FE', O: '#FCE7F3', P: '#FEE2E2',
    Q: '#FFEDD5', R: '#FEF3C7', S: '#D1FAE5', T: '#CCFBF1',
    U: '#CFFAFE', V: '#DBEAFE', W: '#E0F2FE', X: '#F3E8FF',
    Y: '#E0E7FF', Z: '#EDE9FE',
};

function getAvatarColor(name: string): string {
    const letter = name.trim().charAt(0).toUpperCase();
    return AVATAR_COLORS[letter] || '#6366F1';
}

function getBannerColor(name: string): string {
    const letter = name.trim().charAt(0).toUpperCase();
    return BANNER_COLORS[letter] || '#E0E7FF';
}

/**
 * Compute the badge text from days_until_next:
 *  null/undefined → '' (no badge)
 *  <0            → 'OVERDUE'
 *  0             → 'TODAY'
 *  1             → 'TOMORROW'
 *  2+            → 'IN X DAYS'
 */
function daysLabel(days: number | null | undefined): string {
    if (days === null || days === undefined) return '';
    if (days < 0) return 'OVERDUE';
    if (days === 0) return 'TODAY';
    if (days === 1) return 'TOMORROW';
    return `IN ${days} DAYS`;
}

// ─────────────────────────────────────────────────────────────────────
//  Section component
// ─────────────────────────────────────────────────────────────────────

export const SubscriptionsRow: React.FC<SubscriptionsRowProps> = ({
    subscriptions,
    totalMonthlyCost,
}) => {
    if (subscriptions.length === 0) return null;

    return (
        <View style={styles.container}>
            {/* Section header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>SUBSCRIPTIONS</Text>
                <Text style={styles.headerTotal}>AED {formatAmount(totalMonthlyCost)}/mo</Text>
            </View>

            {/* Horizontal scroll */}
            <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.scrollContent}
            >
                {subscriptions.map((sub) => (
                    <SubscriptionCard key={sub.id} sub={sub} />
                ))}
            </ScrollView>
        </View>
    );
};

// ─────────────────────────────────────────────────────────────────────
//  Individual card
// ─────────────────────────────────────────────────────────────────────

const CARD_WIDTH = 160;
const BANNER_HEIGHT = 68;
const AVATAR_SIZE = 64;
const AVATAR_BORDER = 4;
const AVATAR_OUTER = AVATAR_SIZE + AVATAR_BORDER * 2; // 72
// Avatar centered on the banner bottom edge:
const AVATAR_TOP = BANNER_HEIGHT - AVATAR_OUTER / 2;    // 32px from card top

const SubscriptionCard: React.FC<{ sub: Subscription }> = ({ sub }) => {
    const displayName = toTitleCase(sub.merchant_name);
    const initial = displayName.charAt(0).toUpperCase();
    const avatarBg = getAvatarColor(sub.merchant_name);
    const bannerBg = getBannerColor(sub.merchant_name);
    const badge = daysLabel(sub.days_until_next);

    return (
        <View style={styles.card}>
            {/* ── Colored banner (top half) ── */}
            <View style={[styles.banner, { backgroundColor: bannerBg }]} />

            {/* ── Avatar with white ring — positioned absolute, overlaps banner & body ── */}
            <View style={styles.avatarWrapper}>
                <View style={styles.avatarRing}>
                    <View style={[styles.avatarCircle, { backgroundColor: avatarBg }]}>
                        <Text style={styles.avatarLetter}>{initial}</Text>
                    </View>
                </View>
            </View>

            {/* ── Bottom content area ── */}
            <View style={styles.bodyContent}>
                <Text style={styles.merchantName} numberOfLines={1}>
                    {displayName}
                </Text>

                <Text style={styles.amount}>
                    AED {formatAmount(sub.amount)}
                </Text>

                {badge !== '' && (
                    <View style={styles.badge}>
                        <Text style={styles.badgeText}>{badge}</Text>
                    </View>
                )}
            </View>
        </View>
    );
};

// ─────────────────────────────────────────────────────────────────────
//  Styles — all tokens from Figma node 98-34
// ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    // ── Section ────────────────────────────────────────
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
    headerTotal: {
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: '500',
        lineHeight: 19.5,
        color: '#8B8D97',
    },
    scrollContent: {
        paddingLeft: 0,
        paddingRight: 20,
        gap: 16,
    },

    // ── Card outer shell ───────────────────────────────
    card: {
        width: CARD_WIDTH,
        borderRadius: 24,
        backgroundColor: '#FFFFFF',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.05,
        shadowRadius: 12,
        elevation: 3,
        overflow: 'hidden', // clips the banner's flat bottom to card radius
    },

    // ── Colored banner (top portion) ───────────────────
    banner: {
        height: BANNER_HEIGHT,
        width: '100%',
    },

    // ── Avatar — absolute-positioned to straddle banner / body ──
    avatarWrapper: {
        position: 'absolute',
        top: AVATAR_TOP,
        left: 0,
        right: 0,
        alignItems: 'center',
        zIndex: 1,
    },
    avatarRing: {
        width: AVATAR_OUTER,
        height: AVATAR_OUTER,
        borderRadius: AVATAR_OUTER / 2,
        backgroundColor: '#FFFFFF',
        justifyContent: 'center',
        alignItems: 'center',
    },
    avatarCircle: {
        width: AVATAR_SIZE,
        height: AVATAR_SIZE,
        borderRadius: AVATAR_SIZE / 2,
        justifyContent: 'center',
        alignItems: 'center',
    },
    avatarLetter: {
        fontFamily: 'Inter',
        fontSize: 24,
        fontWeight: '700',
        color: '#FFFFFF',
    },

    // ── Body content below banner ──────────────────────
    bodyContent: {
        alignItems: 'center',
        paddingTop: AVATAR_OUTER / 2 + 8,  // space below overlapping avatar
        paddingBottom: 20,
        paddingHorizontal: 12,
        gap: 6,
    },
    merchantName: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '400',
        lineHeight: 21,
        color: '#333333',
        textAlign: 'center',
        maxWidth: CARD_WIDTH - 24,
    },
    amount: {
        fontFamily: 'Inter',
        fontSize: 18,
        fontWeight: '700',
        lineHeight: 24,
        color: '#000000',
        textAlign: 'center',
    },
    badge: {
        marginTop: 4,
        backgroundColor: '#F5F5F5',
        borderRadius: 50,
        paddingHorizontal: 12,
        paddingVertical: 6,
    },
    badgeText: {
        fontFamily: 'Inter',
        fontSize: 11,
        fontWeight: '600',
        lineHeight: 13.75,
        color: '#888888',
        letterSpacing: 0.275,
        textTransform: 'uppercase',
    },
});
