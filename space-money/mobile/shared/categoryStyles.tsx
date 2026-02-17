/**
 * Shared category icon styles and component used across Dashboard,
 * Budget, and Transactions pages.
 *
 * Single source of truth for:
 * - Category → color mapping
 * - Category → SVG path mapping
 * - CatIcon component (filled SVG icons)
 */

import React from 'react';
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

export interface CategoryStyle {
    bg: string;
    icon: string;
    path: string;
}

export const CATEGORY_STYLES: Record<string, CategoryStyle> = {
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
    RENT: {
        bg: '#E6EBF5', icon: '#1E40AF',
        path: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
    },
};

export const DEFAULT_CATEGORY_STYLE: CategoryStyle = {
    bg: '#F3F4F6', icon: '#6B7280',
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
};

export function getCategoryStyle(leanCategory: string): CategoryStyle {
    return CATEGORY_STYLES[leanCategory] || DEFAULT_CATEGORY_STYLE;
}

/**
 * Shared filled-SVG category icon component.
 * Renders the same icon across Dashboard, Budget, and Transactions.
 */
export const CatIcon: React.FC<{
    leanCategory: string;
    size?: number;
    bgOverride?: string;
    iconOverride?: string;
}> = ({ leanCategory, size = 36, bgOverride, iconOverride }) => {
    const style = getCategoryStyle(leanCategory);
    const iconSize = size * 0.5;
    return (
        <View
            style={{
                width: size,
                height: size,
                borderRadius: size * 0.28,
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
