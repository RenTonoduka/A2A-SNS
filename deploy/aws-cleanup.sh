#!/bin/bash
# =============================================================================
# A2A SNS System - AWS Infrastructure Cleanup
# =============================================================================
# Deletes all resources created by aws-setup.sh
# Usage: bash aws-cleanup.sh
# =============================================================================

set -e

# Load config
CONFIG_FILE="/tmp/a2a-sns-aws-config.txt"
if [ -f "$CONFIG_FILE" ]; then
  source $CONFIG_FILE
else
  echo "Config file not found: $CONFIG_FILE"
  echo "Please set variables manually or run aws-setup.sh first"
  exit 1
fi

echo "=========================================="
echo "A2A SNS - AWS Infrastructure Cleanup"
echo "=========================================="
echo ""
echo "This will DELETE:"
echo "  - EC2 Instance: $INSTANCE_ID"
echo "  - Security Group: $SG_ID"
echo "  - Subnet: $SUBNET_ID"
echo "  - Route Table: $RTB_ID"
echo "  - Internet Gateway: $IGW_ID"
echo "  - VPC: $VPC_ID"
echo "  - Key Pair: $KEY_NAME"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Cancelled."
  exit 0
fi

echo ""

# -----------------------------------------------------------------------------
# 1. Terminate EC2 Instance
# -----------------------------------------------------------------------------
echo "[1/7] Terminating EC2 Instance..."
aws ec2 terminate-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION > /dev/null 2>&1 || true

echo "  Waiting for instance to terminate..."
aws ec2 wait instance-terminated \
  --instance-ids $INSTANCE_ID \
  --region $REGION 2>/dev/null || true

echo "  Done"

# -----------------------------------------------------------------------------
# 2. Delete Key Pair
# -----------------------------------------------------------------------------
echo "[2/7] Deleting Key Pair..."
aws ec2 delete-key-pair \
  --key-name $KEY_NAME \
  --region $REGION 2>/dev/null || true

rm -f "$HOME/.ssh/${KEY_NAME}.pem"
echo "  Done"

# -----------------------------------------------------------------------------
# 3. Delete Security Group
# -----------------------------------------------------------------------------
echo "[3/7] Deleting Security Group..."
sleep 5  # Wait for ENI detachment
aws ec2 delete-security-group \
  --group-id $SG_ID \
  --region $REGION 2>/dev/null || true
echo "  Done"

# -----------------------------------------------------------------------------
# 4. Delete Subnet
# -----------------------------------------------------------------------------
echo "[4/7] Deleting Subnet..."
aws ec2 delete-subnet \
  --subnet-id $SUBNET_ID \
  --region $REGION 2>/dev/null || true
echo "  Done"

# -----------------------------------------------------------------------------
# 5. Delete Route Table
# -----------------------------------------------------------------------------
echo "[5/7] Deleting Route Table..."
# First disassociate
ASSOC_ID=$(aws ec2 describe-route-tables \
  --route-table-ids $RTB_ID \
  --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' \
  --output text \
  --region $REGION 2>/dev/null || echo "")

if [ -n "$ASSOC_ID" ] && [ "$ASSOC_ID" != "None" ]; then
  aws ec2 disassociate-route-table \
    --association-id $ASSOC_ID \
    --region $REGION 2>/dev/null || true
fi

aws ec2 delete-route-table \
  --route-table-id $RTB_ID \
  --region $REGION 2>/dev/null || true
echo "  Done"

# -----------------------------------------------------------------------------
# 6. Detach and Delete Internet Gateway
# -----------------------------------------------------------------------------
echo "[6/7] Deleting Internet Gateway..."
aws ec2 detach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID \
  --region $REGION 2>/dev/null || true

aws ec2 delete-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --region $REGION 2>/dev/null || true
echo "  Done"

# -----------------------------------------------------------------------------
# 7. Delete VPC
# -----------------------------------------------------------------------------
echo "[7/7] Deleting VPC..."
aws ec2 delete-vpc \
  --vpc-id $VPC_ID \
  --region $REGION 2>/dev/null || true
echo "  Done"

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
rm -f $CONFIG_FILE

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "All resources have been deleted."
