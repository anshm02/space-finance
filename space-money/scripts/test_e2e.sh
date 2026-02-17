#!/bin/bash

# Complete End-to-End Test Script
# Tests the full flow from customer creation to entity linking

echo "=========================================="
echo "Lean Integration End-to-End Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"
TEST_USER="e2e_test_$(date +%s)"

echo "Test Configuration:"
echo "  Base URL: $BASE_URL"
echo "  Test User: $TEST_USER"
echo ""

# Test 1: Health Check
echo "1. Testing backend health..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "   ${GREEN}✓${NC} Backend is healthy"
else
    echo -e "   ${RED}✗${NC} Backend health check failed"
    exit 1
fi

# Test 2: Create Customer
echo ""
echo "2. Creating Lean customer..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/lean/customers" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$TEST_USER\"}")

if echo "$CREATE_RESPONSE" | grep -q "customer_id"; then
    CUSTOMER_DB_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    CUSTOMER_ID=$(echo "$CREATE_RESPONSE" | grep -o '"customer_id":"[^"]*"' | cut -d'"' -f4)
    echo -e "   ${GREEN}✓${NC} Customer created"
    echo "   DB ID: $CUSTOMER_DB_ID"
    echo "   Lean ID: $CUSTOMER_ID"
else
    echo -e "   ${RED}✗${NC} Customer creation failed"
    echo "   Response: $CREATE_RESPONSE"
    exit 1
fi

# Test 3: Get Customer Access Token
echo ""
echo "3. Getting customer access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/lean/customer-token/$CUSTOMER_ID")

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo -e "   ${GREEN}✓${NC} Customer token obtained"
    echo "   Token: ${ACCESS_TOKEN:0:50}..."
else
    echo -e "   ${RED}✗${NC} Token generation failed"
    echo "   Response: $TOKEN_RESPONSE"
    exit 1
fi

# Test 4: Simulate Entity Link (what would come from SDK)
echo ""
echo "4. Simulating entity link from SDK..."
MOCK_ENTITY_ID="entity_test_$(date +%s)"
ENTITY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/lean/entities/link" \
    -H "Content-Type: application/json" \
    -d "{
        \"customer_id\":\"$CUSTOMER_DB_ID\",
        \"entity_id\":\"$MOCK_ENTITY_ID\",
        \"bank_identifier\":\"LEAN_MB1\",
        \"permissions\":[\"identity\",\"accounts\",\"balance\",\"transactions\"]
    }")

if echo "$ENTITY_RESPONSE" | grep -q "entity_id"; then
    ENTITY_DB_ID=$(echo "$ENTITY_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "   ${GREEN}✓${NC} Entity linked"
    echo "   DB ID: $ENTITY_DB_ID"
    echo "   Entity ID: $MOCK_ENTITY_ID"
else
    echo -e "   ${RED}✗${NC} Entity linking failed"
    echo "   Response: $ENTITY_RESPONSE"
    exit 1
fi

# Test 5: Get Entities
echo ""
echo "5. Retrieving linked entities..."
ENTITIES_RESPONSE=$(curl -s "$BASE_URL/api/v1/lean/entities/$CUSTOMER_DB_ID")

if echo "$ENTITIES_RESPONSE" | grep -q "$MOCK_ENTITY_ID"; then
    ENTITY_COUNT=$(echo "$ENTITIES_RESPONSE" | grep -o "entity_id" | wc -l | tr -d ' ')
    echo -e "   ${GREEN}✓${NC} Entities retrieved"
    echo "   Count: $ENTITY_COUNT"
else
    echo -e "   ${RED}✗${NC} Entity retrieval failed"
    echo "   Response: $ENTITIES_RESPONSE"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ All tests passed!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Backend health check"
echo "  ✓ Customer creation"
echo "  ✓ Customer token generation"
echo "  ✓ Entity linking"
echo "  ✓ Entity retrieval"
echo ""
echo "The backend is ready for mobile testing!"
echo ""
echo "Next: Start mobile app and test with real Lean Link SDK"
echo "  cd mobile && npx expo start"
echo ""
