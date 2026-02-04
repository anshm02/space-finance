#!/bin/bash

# Quick Backend Health Check Script

echo "=================================="
echo "Lean Integration Backend Test"
echo "=================================="
echo ""

# Check if backend is running
echo "1. Checking backend health..."
HEALTH=$(curl -s http://localhost:8000/health 2>&1)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "   ✓ Backend is running"
else
    echo "   ✗ Backend is not responding"
    echo "   Please start backend: cd backend && python main.py"
    exit 1
fi

# Check database connection
echo ""
echo "2. Testing database connection..."
curl -s http://localhost:8000/api/v1/lean/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Database connection OK"
else
    echo "   ✗ Database connection failed"
    echo "   Check PostgreSQL is running"
fi

# Test token validity
echo ""
echo "3. Testing Lean API token..."
TEST_USER="test_$(date +%s)"
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/lean/customers \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$TEST_USER\"}" 2>&1)

if echo "$RESULT" | grep -q "customer_id"; then
    echo "   ✓ Lean API token is valid"
    CUSTOMER_ID=$(echo "$RESULT" | grep -o '"customer_id":"[^"]*"' | cut -d'"' -f4)
    echo "   Customer created: $CUSTOMER_ID"
elif echo "$RESULT" | grep -q "401"; then
    echo "   ✗ OAuth token expired"
    echo "   Run: cd backend && python refresh_token.py"
    echo "   Then update LEAN_APP_TOKEN in backend/.env"
    exit 1
elif echo "$RESULT" | grep -q "CUSTOMER_ALREADY_EXISTS"; then
    echo "   ✓ Lean API is working (customer exists)"
else
    echo "   ✗ Unexpected error: $RESULT"
    exit 1
fi

echo ""
echo "=================================="
echo "✓ All backend checks passed!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Update mobile/.env with your IP address:"
echo "   EXPO_PUBLIC_API_URL=http://YOUR_IP:8000"
echo ""
echo "2. Start mobile app:"
echo "   cd mobile && npx expo start"
echo ""
echo "3. Scan QR code with Expo Go on your phone"
echo ""
