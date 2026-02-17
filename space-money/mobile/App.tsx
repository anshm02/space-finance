/**
 * Space Money — Main application entry point.
 *
 * Tab-based navigation:
 * - Dashboard (home)
 * - Budget (spending plan + breakdown)
 * - Transactions (calendar + grouped list)
 * - Health (placeholder)
 * - Settings (placeholder)
 *
 * TEMPORARY: Hardcoded to user b62164d4-1965-45bd-8975-62971f7a0654.
 */

import React, { useState } from 'react';
import { SafeAreaView, StatusBar, StyleSheet, View, Text } from 'react-native';
import { DashboardScreen } from './features/dashboard';
import { BudgetScreen } from './features/budget';
import { TransactionsScreen } from './features/transactions';
import { BottomNav, TabName } from './features/dashboard/components/BottomNav';
import { TopBar } from './features/dashboard/components/TopBar';

const HARDCODED_USER_ID = 'b62164d4-1965-45bd-8975-62971f7a0654';

/* ------------------------------------------------------------------ */
/*  Placeholder screens for Health & Settings                         */
/* ------------------------------------------------------------------ */

const PlaceholderScreen: React.FC<{ title: string }> = ({ title }) => (
    <View style={placeholderStyles.container}>
        <TopBar />
        <View style={placeholderStyles.content}>
            <Text style={placeholderStyles.emoji}>
                {title === 'Health' ? '❤️' : '⚙️'}
            </Text>
            <Text style={placeholderStyles.title}>{title}</Text>
            <Text style={placeholderStyles.subtitle}>Coming soon</Text>
        </View>
    </View>
);

const placeholderStyles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F5F7',
    },
    content: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    emoji: {
        fontSize: 48,
    },
    title: {
        fontFamily: 'Inter',
        fontSize: 22,
        fontWeight: '600',
        color: '#1A1D2E',
        marginTop: 16,
    },
    subtitle: {
        fontFamily: 'Inter',
        fontSize: 14,
        fontWeight: '400',
        color: '#8B8D97',
        marginTop: 8,
    },
});

/* ------------------------------------------------------------------ */
/*  Screen wrapper using real TopBar (matches Dashboard exactly)      */
/* ------------------------------------------------------------------ */

const ScreenWithHeader: React.FC<{
    title: string;
    children: React.ReactNode;
}> = ({ title, children }) => (
    <View style={headerStyles.container}>
        <TopBar title={title} />
        {children}
    </View>
);

const headerStyles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F5F7',
    },
});

/* ------------------------------------------------------------------ */
/*  App Root                                                          */
/* ------------------------------------------------------------------ */

export default function App() {
    const [activeTab, setActiveTab] = useState<TabName>('Dashboard');

    const renderScreen = () => {
        switch (activeTab) {
            case 'Dashboard':
                return <DashboardScreen userId={HARDCODED_USER_ID} />;
            case 'Budget':
                return (
                    <ScreenWithHeader title="Budget">
                        <BudgetScreen userId={HARDCODED_USER_ID} />
                    </ScreenWithHeader>
                );
            case 'Transactions':
                return (
                    <ScreenWithHeader title="Transactions">
                        <TransactionsScreen userId={HARDCODED_USER_ID} />
                    </ScreenWithHeader>
                );
            case 'Health':
                return <PlaceholderScreen title="Health" />;
            case 'Settings':
                return <PlaceholderScreen title="Settings" />;
            default:
                return <DashboardScreen userId={HARDCODED_USER_ID} />;
        }
    };

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="dark-content" backgroundColor="#F5F5F7" />
            {renderScreen()}
            <BottomNav activeTab={activeTab} onTabPress={setActiveTab} />
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F5F7',
    },
});
