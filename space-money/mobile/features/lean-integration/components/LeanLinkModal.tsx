/**
 * Lean Link SDK Modal using official lean-react-native package
 */

import React, { useRef, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import LinkSDK from 'lean-react-native';

interface LeanLinkModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: (entityId: string) => void;
  onError: (error: string) => void;
  appToken: string;
  customerId: string;
  customerAccessToken: string;
}

export const LeanLinkModal: React.FC<LeanLinkModalProps> = ({
  visible,
  onClose,
  onSuccess,
  onError,
  appToken,
  customerId,
  customerAccessToken,
}) => {
  const leanRef = useRef<any>(null);

  const handleCallback = (response: any) => {
    Alert.alert('DEBUG 3', 'Callback was called!');
    console.log('[Lean SDK] Callback response:', JSON.stringify(response, null, 2));
    Alert.alert('Lean SDK Callback', `Status: ${response.status}\nFull response: ${JSON.stringify(response, null, 2)}`);
    
    if (response.status === 'SUCCESS') {
      console.log('[Lean SDK] SUCCESS - entity_id:', response.entity_id);
      Alert.alert('SUCCESS', `Entity ID: ${response.entity_id}`);
      onSuccess(response.entity_id);
      onClose();
    } else if (response.status === 'ERROR') {
      console.log('[Lean SDK] ERROR:', response.message);
      Alert.alert('ERROR', `Message: ${response.message || 'Unknown error'}`);
      onError(response.message || 'Unknown error');
      onClose();
    } else if (response.status === 'CANCELLED') {
      console.log('[Lean SDK] CANCELLED');
      Alert.alert('CANCELLED', 'User cancelled the operation');
      onClose();
    }
  };

  useEffect(() => {
    Alert.alert('DEBUG 1', `useEffect triggered\nvisible: ${visible}\nleanRef.current exists: ${!!leanRef.current}`);
    
    if (visible && leanRef.current) {
      Alert.alert('DEBUG 2', `About to call .connect()\ncustomerId: ${customerId}\nappToken: ${appToken.substring(0, 20)}...`);
      
      try {
        leanRef.current.connect({
          customer_id: customerId,
          permissions: ['identity', 'accounts', 'balance', 'transactions'],
          access_token: customerAccessToken,
        });
        
        Alert.alert('DEBUG 4', '.connect() called successfully');
      } catch (error: any) {
        Alert.alert('ERROR in useEffect', `Failed to call connect: ${error.message}`);
      }
    } else {
      if (!visible) {
        Alert.alert('DEBUG', 'Modal not visible');
      }
      if (!leanRef.current) {
        Alert.alert('DEBUG', 'leanRef.current is null - SDK not initialized yet');
      }
    }
  }, [visible, customerId, customerAccessToken]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Connect Your Bank</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        <LinkSDK
          ref={leanRef}
          appToken={appToken}
          country="ae"
          sandbox={true}
          callback={handleCallback}
        />
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E7',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 24,
    color: '#666',
  },
});
