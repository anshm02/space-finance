declare module 'lean-react-native' {
  import { Component } from 'react';

  interface LeanConnectOptions {
    customer_id: string;
    permissions: string[];
    access_token: string;
  }

  interface LeanCallbackResponse {
    status: 'SUCCESS' | 'ERROR' | 'CANCELLED';
    message?: string;
    entity_id?: string;
    bank_identifier?: string;
    exit_point?: string;
    last_api_response?: string;
    secondary_status?: string;
  }

  interface LinkSDKProps {
    appToken: string;
    country: string;
    sandbox?: boolean;
    callback?: (response: LeanCallbackResponse) => void;
  }

  export default class LinkSDK extends Component<LinkSDKProps> {
    connect(options: LeanConnectOptions): void;
  }
}
