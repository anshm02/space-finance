/**
 * TopBar component — "Dashboard" title + notification bell with red dot.
 * Matches Figma design tokens exactly.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import Svg, { Path, Circle as SvgCircle } from 'react-native-svg';

interface TopBarProps {
    title?: string;
}

export const TopBar: React.FC<TopBarProps> = ({ title = 'Dashboard' }) => {
    return (
        <View style={styles.container}>
            <Text style={styles.title}>{title}</Text>
            <TouchableOpacity style={styles.bellContainer}>
                <Svg width={24} height={24} viewBox="0 0 24 24" fill="none">
                    <Path
                        d="M18 8A6 6 0 1 0 6 8c0 7-3 9-3 9h18s-3-2-3-9Z"
                        stroke="#1A1D2E"
                        strokeWidth={1.5}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                    <Path
                        d="M13.73 21a2 2 0 0 1-3.46 0"
                        stroke="#1A1D2E"
                        strokeWidth={1.5}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                </Svg>
                <View style={styles.redDot} />
            </TouchableOpacity>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingTop: 12,
        paddingBottom: 8,
        backgroundColor: '#F5F5F7',
    },
    title: {
        fontFamily: 'Inter',
        fontSize: 28,
        fontWeight: '700',
        color: '#1A1D2E',
        letterSpacing: -0.5,
    },
    bellContainer: {
        position: 'relative',
        width: 32,
        height: 32,
        justifyContent: 'center',
        alignItems: 'center',
    },
    redDot: {
        position: 'absolute',
        top: 4,
        right: 4,
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#EF4444',
    },
});
