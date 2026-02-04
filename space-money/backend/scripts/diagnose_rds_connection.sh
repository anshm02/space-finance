#!/bin/bash
# AWS RDS Connection Troubleshooting Script
# Run this to diagnose connection issues

echo "============================================================"
echo "AWS RDS Connection Diagnostics"
echo "============================================================"
echo ""

# Extract endpoint from .env
ENDPOINT=$(grep "DATABASE_URL" .env | sed 's/.*@\([^:]*\):.*/\1/')
echo "RDS Endpoint: $ENDPOINT"
echo ""

# Test 1: DNS Resolution
echo "1. Testing DNS resolution..."
if host "$ENDPOINT" > /dev/null 2>&1; then
    echo "   ✓ DNS resolves correctly"
    host "$ENDPOINT" | head -1
else
    echo "   ✗ DNS resolution failed"
    echo "   → Check endpoint URL is correct"
fi
echo ""

# Test 2: Network connectivity (ping)
echo "2. Testing network connectivity..."
if ping -c 3 "$ENDPOINT" > /dev/null 2>&1; then
    echo "   ✓ Host is reachable"
else
    echo "   ⚠ Host not responding to ping (may be normal for AWS)"
fi
echo ""

# Test 3: Port accessibility
echo "3. Testing PostgreSQL port (5432)..."
if command -v nc > /dev/null 2>&1; then
    if timeout 5 nc -zv "$ENDPOINT" 5432 2>&1 | grep -q "succeeded"; then
        echo "   ✓ Port 5432 is accessible"
    else
        echo "   ✗ Port 5432 is NOT accessible"
        echo "   → Security group is blocking connections"
        echo ""
        echo "   Checklist:"
        echo "   [ ] Security group allows PostgreSQL (5432) from your IP"
        echo "   [ ] RDS instance has 'Publicly accessible' = Yes"
        echo "   [ ] VPC has internet gateway attached"
        echo "   [ ] Subnet route table routes to internet gateway"
    fi
else
    echo "   ⚠ nc (netcat) not installed, skipping port test"
    echo "   Install with: brew install netcat"
fi
echo ""

# Test 4: Check if using correct database name
echo "4. Common Issues Checklist:"
echo "   [ ] Is your RDS instance 'Publicly accessible'?"
echo "       → Go to RDS > Databases > spacemoney-db-dev"
echo "       → Check 'Publicly accessible' under Connectivity"
echo ""
echo "   [ ] Does the database 'spacemoney' exist in your instance?"
echo "       → Default database is usually 'postgres'"
echo "       → Try changing DATABASE_URL to use 'postgres' database"
echo ""
echo "   [ ] Is your IP allowed in the security group?"
echo "       → Your current IP may have changed"
echo "       → Update security group with current IP"
echo ""
echo "   [ ] Are you connecting from inside AWS VPC?"
echo "       → If not in VPC, RDS must be publicly accessible"
echo ""

echo "============================================================"
echo "Suggested Next Steps:"
echo "============================================================"
echo ""
echo "1. Verify 'Publicly accessible' setting in AWS Console:"
echo "   https://console.aws.amazon.com/rds"
echo ""
echo "2. If NOT publicly accessible, you have two options:"
echo "   a) Make it publicly accessible (Modify > Connectivity)"
echo "   b) Use SSH tunnel through EC2 bastion host"
echo ""
echo "3. Try connecting to default 'postgres' database:"
echo "   Change your .env DATABASE_URL database name from"
echo "   '/spacemoney' to '/postgres'"
echo ""
echo "4. Test connection with psql client:"
echo "   psql -h $ENDPOINT -U postgres -d postgres"
echo ""
echo "============================================================"
