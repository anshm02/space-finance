/**
 * Screen component for connecting bank accounts via Lean
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
  ScrollView,
} from 'react-native';
import { useLeanIntegration } from '../hooks/useLeanIntegration';
import { LeanEntity } from '../types';
import { LeanLinkModal } from './LeanLinkModal';

const LEAN_APP_TOKEN = '33429486-4597-4dbf-b122-2ac4920d8f1d';

interface LeanConnectionScreenProps {
  userId: string;
}

export const LeanConnectionScreen: React.FC<LeanConnectionScreenProps> = ({
  userId,
}) => {
  const {
    customer,
    entities,
    accounts,
    isLoading,
    error,
    createCustomer,
    getCustomer,
    getEntities,
    syncData,
    getAccounts,
    getCustomerAccessToken,
    saveEntity,
    clearError,
  } = useLeanIntegration();

  const [syncingEntityId, setSyncingEntityId] = useState<string | null>(null);
  const [showLeanLink, setShowLeanLink] = useState(false);
  const [customerToken, setCustomerToken] = useState<string | null>(null);

  useEffect(() => {
    // Try to get existing customer or create new one
    getCustomer(userId).catch(() => {
      createCustomer(userId).catch((err) => {
        Alert.alert('Error', 'Failed to initialize Lean customer');
      });
    });
  }, [userId]);

  useEffect(() => {
    // Load entities when customer is available
    if (customer) {
      getEntities(customer.id).catch(() => {
        // Ignore error, user may not have entities yet
      });
    }
  }, [customer]);

  const handleLinkBank = async () => {
    Alert.alert('DEBUG', 'handleLinkBank called');
    
    if (!customer) {
      Alert.alert('Error', 'Customer not initialized');
      return;
    }
    
    Alert.alert('DEBUG', `Customer exists: ${customer.customer_id}`);

    try {
      // Get customer access token
      Alert.alert('DEBUG', 'Getting customer access token...');
      const token = await getCustomerAccessToken(customer.customer_id);
      
      Alert.alert('DEBUG', `Token received: ${token ? 'YES' : 'NO'}`);
      
      if (!token) {
        Alert.alert('Error', 'Failed to get customer access token');
        return;
      }
      
      setCustomerToken(token);
      Alert.alert('DEBUG', 'About to open Lean Link modal');
      setShowLeanLink(true);
    } catch (err: any) {
      Alert.alert('Error', `Failed to initialize bank linking: ${err.message}`);
    }
  };

  const handleLeanLinkSuccess = async (entityId: string) => {
    Alert.alert('DEBUG', `handleLeanLinkSuccess called - SDK didn't return entity_id, fetching from Lean...`);
    console.log('[LeanConnection] handleLeanLinkSuccess called - fetching entities from Lean');
    
    if (!customer) {
      Alert.alert('DEBUG', 'No customer found, returning');
      console.log('[LeanConnection] No customer found, returning');
      return;
    }
    
    try {
      Alert.alert('DEBUG', `Fetching entities from Lean for customer: ${customer.customer_id}`);
      console.log('[LeanConnection] Fetching entities from Lean API for customer:', customer.customer_id);
      
      // Fetch entities from Lean API
      const { fetchEntitiesFromLean } = await import('../api/leanApi');
      const leanEntities = await fetchEntitiesFromLean(customer.customer_id);
      
      Alert.alert('DEBUG', `Fetched ${leanEntities.entities?.length || 0} entities from Lean`);
      console.log('[LeanConnection] Fetched entities from Lean:', leanEntities);
      
      if (!leanEntities.entities || leanEntities.entities.length === 0) {
        Alert.alert('Error', 'No entities found. The bank connection may not have completed.');
        return;
      }
      
      // Get the most recent entity
      const latestEntity = leanEntities.entities[leanEntities.entities.length - 1];
      Alert.alert('DEBUG', `Using entity: ${latestEntity.id}`);
      console.log('[LeanConnection] Using latest entity:', latestEntity);
      
      // Save the entity to our database
      Alert.alert('DEBUG', 'Saving entity to database...');
      await saveEntity(customer.id, latestEntity.id, latestEntity.bank_identifier);
      
      Alert.alert('DEBUG', 'Entity saved successfully');
      console.log('[LeanConnection] Entity saved, fetching entities from our DB');
      
      await getEntities(customer.id);
      
      Alert.alert('DEBUG', 'Entities fetched from our DB');
      console.log('[LeanConnection] Success - entities fetched');
      
      Alert.alert('Success', 'Bank account linked successfully!');
    } catch (err: any) {
      Alert.alert('Error', `Failed to save bank connection: ${err.message}`);
      console.log('[LeanConnection] Error saving entity:', err);
    }
  };

  const handleLeanLinkError = (error: string) => {
    Alert.alert('DEBUG', `handleLeanLinkError called: ${error}`);
    console.log('[LeanConnection] handleLeanLinkError called:', error);
    Alert.alert('Error', `Bank linking failed: ${error}`);
  };

  const handleSyncData = async (entity: LeanEntity) => {
    setSyncingEntityId(entity.entity_id);
    try {
      const result = await syncData({
        entity_id: entity.entity_id,
        sync_types: ['identity', 'accounts', 'balance', 'transactions'],
      });

      if (result) {
        Alert.alert(
          'Success',
          `Synced data! Created ${result.files_created.length} files.`
        );
        
        // Load accounts for this entity
        await getAccounts(entity.entity_id);
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to sync data');
    } finally {
      setSyncingEntityId(null);
    }
  };

  if (error) {
    return (
      <View style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Error: {error}</Text>
          <TouchableOpacity
            style={styles.button}
            onPress={clearError}
          >
            <Text style={styles.buttonText}>Dismiss</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  if (isLoading && !customer) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Initializing...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Bank Connections</Text>
        
        {customer && (
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>Customer ID:</Text>
            <Text style={styles.infoValue}>{customer.customer_id}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.button, styles.primaryButton]}
          onPress={handleLinkBank}
          disabled={isLoading || !customer}
        >
          <Text style={styles.buttonText}>
            {isLoading ? 'Loading...' : '+ Link Bank Account'}
          </Text>
        </TouchableOpacity>

        {showLeanLink && customer && customerToken && (
          <LeanLinkModal
            visible={showLeanLink}
            onClose={() => setShowLeanLink(false)}
            onSuccess={handleLeanLinkSuccess}
            onError={handleLeanLinkError}
            appToken={LEAN_APP_TOKEN}
            customerId={customer.customer_id}
            customerAccessToken={customerToken}
          />
        )}

        <Text style={styles.sectionTitle}>Connected Accounts</Text>

        {entities.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateText}>
              No bank accounts connected yet
            </Text>
            <Text style={styles.emptyStateSubtext}>
              Tap "Link Bank Account" to get started
            </Text>
          </View>
        ) : (
          entities.map((entity) => (
            <View key={entity.id} style={styles.entityCard}>
              <View style={styles.entityHeader}>
                <Text style={styles.entityBank}>
                  {entity.bank_identifier || 'Bank Account'}
                </Text>
                <View
                  style={[
                    styles.statusBadge,
                    entity.status === 'ACTIVE'
                      ? styles.statusActive
                      : styles.statusPending,
                  ]}
                >
                  <Text style={styles.statusText}>{entity.status}</Text>
                </View>
              </View>
              
              <Text style={styles.entityId}>
                Entity ID: {entity.entity_id}
              </Text>
              
              {entity.last_synced_at && (
                <Text style={styles.syncTime}>
                  Last synced: {new Date(entity.last_synced_at).toLocaleString()}
                </Text>
              )}

              <TouchableOpacity
                style={[styles.button, styles.secondaryButton]}
                onPress={() => handleSyncData(entity)}
                disabled={syncingEntityId === entity.entity_id}
              >
                {syncingEntityId === entity.entity_id ? (
                  <ActivityIndicator size="small" color="#007AFF" />
                ) : (
                  <Text style={styles.secondaryButtonText}>Sync Data</Text>
                )}
              </TouchableOpacity>
            </View>
          ))
        )}

        {accounts.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Bank Accounts</Text>
            {accounts.map((account) => (
              <View key={account.id} style={styles.accountCard}>
                <Text style={styles.accountType}>
                  {account.account_type || 'Account'}
                </Text>
                <Text style={styles.accountNumber}>
                  {account.account_number || account.account_id}
                </Text>
                {account.balance && (
                  <Text style={styles.accountBalance}>
                    Balance: {account.currency} {account.balance}
                  </Text>
                )}
              </View>
            ))}
          </>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F7',
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 20,
    color: '#000',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 24,
    marginBottom: 12,
    color: '#000',
  },
  infoCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  infoLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#000',
  },
  button: {
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 8,
  },
  primaryButton: {
    backgroundColor: '#007AFF',
  },
  secondaryButton: {
    backgroundColor: '#FFF',
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  buttonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButtonText: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
  },
  emptyStateText: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#999',
  },
  entityCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  entityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  entityBank: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusActive: {
    backgroundColor: '#34C759',
  },
  statusPending: {
    backgroundColor: '#FF9500',
  },
  statusText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600',
  },
  entityId: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  syncTime: {
    fontSize: 12,
    color: '#999',
    marginBottom: 12,
  },
  accountCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  accountType: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    marginBottom: 4,
  },
  accountNumber: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  accountBalance: {
    fontSize: 16,
    fontWeight: '500',
    color: '#34C759',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#FF3B30',
    textAlign: 'center',
    marginBottom: 20,
  },
});
