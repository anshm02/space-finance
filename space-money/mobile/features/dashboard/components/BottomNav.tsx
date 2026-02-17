/**
 * BottomNav — Tab bar with 5 icons.
 * Accepts activeTab and onTabPress props for navigation.
 * Matches Figma design tokens.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import Svg, { Path, Rect, Circle as SvgCircle } from 'react-native-svg';

export type TabName = 'Dashboard' | 'Budget' | 'Transactions' | 'Health' | 'Settings';

interface BottomNavProps {
    activeTab?: TabName;
    onTabPress?: (tab: TabName) => void;
}

interface TabItem {
    label: TabName;
    icon: (active: boolean) => React.ReactNode;
}

const DashboardIcon = ({ active }: { active: boolean }) => (
    <Svg width={24} height={24} viewBox="0 0 24 24" fill="none">
        <Rect x={3} y={3} width={7} height={7} rx={1.5} stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
        <Rect x={14} y={3} width={7} height={7} rx={1.5} stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
        <Rect x={3} y={14} width={7} height={7} rx={1.5} stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
        <Rect x={14} y={14} width={7} height={7} rx={1.5} stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
    </Svg>
);

const BudgetIcon = ({ active }: { active: boolean }) => (
    <Svg width={24} height={24} viewBox="0 0 24 24" fill="none">
        <SvgCircle cx={12} cy={12} r={9} stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
        <Path d="M12 8v8M9 11h6" stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} strokeLinecap="round" />
    </Svg>
);

const TransactionsIcon = ({ active }: { active: boolean }) => (
    <Svg width={24} height={24} viewBox="0 0 24 24" fill="none">
        <Path d="M4 6h16M4 12h16M4 18h10" stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} strokeLinecap="round" />
    </Svg>
);

const HealthIcon = ({ active }: { active: boolean }) => (
    <Svg width={24} height={24} viewBox="0 0 24 24" fill="none">
        <Path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
);

const SettingsIcon = ({ active }: { active: boolean }) => (
    <Svg width={24} height={24} viewBox="0 0 24 24" fill="none">
        <Path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
        <SvgCircle cx={12} cy={12} r={3} stroke={active ? '#1A1D2E' : '#9CA3AF'} strokeWidth={1.5} />
    </Svg>
);

const tabs: TabItem[] = [
    { label: 'Dashboard', icon: (a) => <DashboardIcon active={a} /> },
    { label: 'Budget', icon: (a) => <BudgetIcon active={a} /> },
    { label: 'Transactions', icon: (a) => <TransactionsIcon active={a} /> },
    { label: 'Health', icon: (a) => <HealthIcon active={a} /> },
    { label: 'Settings', icon: (a) => <SettingsIcon active={a} /> },
];

export const BottomNav: React.FC<BottomNavProps> = ({
    activeTab = 'Dashboard',
    onTabPress,
}) => {
    return (
        <View style={styles.container}>
            {tabs.map((tab) => {
                const isActive = tab.label === activeTab;
                return (
                    <TouchableOpacity
                        key={tab.label}
                        style={styles.tab}
                        onPress={() => onTabPress?.(tab.label)}
                        activeOpacity={0.7}
                    >
                        {tab.icon(isActive)}
                        <Text style={[styles.label, isActive && styles.activeLabel]}>
                            {tab.label}
                        </Text>
                        {isActive && <View style={styles.activeDot} />}
                    </TouchableOpacity>
                );
            })}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
        paddingVertical: 8,
        paddingBottom: 24,
        backgroundColor: '#FFFFFF',
        borderTopWidth: 1,
        borderTopColor: '#F3F4F6',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -1 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 4,
    },
    tab: {
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: 6,
        minWidth: 60,
    },
    label: {
        fontFamily: 'Inter',
        fontSize: 10,
        fontWeight: '500',
        color: '#9CA3AF',
        marginTop: 4,
    },
    activeLabel: {
        color: '#1A1D2E',
        fontWeight: '600',
    },
    activeDot: {
        width: 4,
        height: 4,
        borderRadius: 2,
        backgroundColor: '#1A1D2E',
        marginTop: 3,
    },
});
