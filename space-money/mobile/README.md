# Space Money Mobile - Lean Integration

React Native mobile app with Lean Technologies bank linking integration.

## Quick Start

### 1. Install Dependencies

```bash
npm install
# or
yarn install
```

### 2. Configure Environment

Create `.env` file:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000
```

For physical device testing, use your computer's IP:
```env
EXPO_PUBLIC_API_URL=http://192.168.1.XXX:8000
```

### 3. Start Development Server

```bash
# Using Expo
npx expo start

# Using React Native CLI
npx react-native start
```

## Using Lean Integration

### Import the Feature

```typescript
import {
  LeanConnectionScreen,
  useLeanIntegration,
  LeanCustomer,
  LeanEntity,
} from './features/lean-integration';
```

### Use in Your Component

```typescript
import { LeanConnectionScreen } from './features/lean-integration';

function App() {
  const userId = "user_123";
  
  return <LeanConnectionScreen userId={userId} />;
}
```

### Use the Hook Directly

```typescript
import { useLeanIntegration } from './features/lean-integration';

function MyComponent() {
  const {
    customer,
    entities,
    accounts,
    isLoading,
    error,
    createCustomer,
    linkEntity,
    syncData,
  } = useLeanIntegration();
  
  // Use the hook methods...
}
```

## Feature Structure

```
mobile/features/lean-integration/
├── types/                    # TypeScript types
│   └── index.ts
├── api/                      # API client
│   └── leanApi.ts
├── hooks/                    # React hooks
│   └── useLeanIntegration.ts
├── components/               # UI components
│   └── LeanConnectionScreen.tsx
└── index.ts                  # Feature exports
```

## API Methods

- `createCustomer(userId)` - Initialize Lean customer
- `getCustomer(userId)` - Get existing customer
- `linkEntity(request)` - Link bank account
- `getEntities(customerId)` - Get linked banks
- `syncData(request)` - Sync financial data
- `getAccounts(entityId)` - Get bank accounts

## Testing

1. Ensure backend is running at `EXPO_PUBLIC_API_URL`
2. Run the app
3. Navigate to Lean connection screen
4. Test bank linking and data sync flows

See full documentation in: `../specs/lean-tech-integration/implementation-notes.md`
