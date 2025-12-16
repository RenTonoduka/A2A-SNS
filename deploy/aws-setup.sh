#!/bin/bash
# =============================================================================
# A2A SNS System - AWS Infrastructure Setup (Zero to EC2)
# =============================================================================
# Creates: VPC, Subnet, IGW, Route Table, Security Group, Key Pair, EC2
# Usage: bash aws-setup.sh
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PROJECT_NAME="a2a-sns"
REGION="ap-northeast-1"  # Tokyo
INSTANCE_TYPE="t3.medium"
AMI_ID="ami-0d52744d6551d851e"  # Amazon Linux 2023 (Tokyo)

# Network settings
VPC_CIDR="10.0.0.0/16"
SUBNET_CIDR="10.0.1.0/24"
AZ="${REGION}a"

echo "=========================================="
echo "A2A SNS - AWS Infrastructure Setup"
echo "=========================================="
echo "Region: $REGION"
echo "Instance: $INSTANCE_TYPE"
echo ""

# -----------------------------------------------------------------------------
# 1. Create VPC
# -----------------------------------------------------------------------------
echo "[1/8] Creating VPC..."
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block $VPC_CIDR \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=${PROJECT_NAME}-vpc}]" \
  --region $REGION \
  --query 'Vpc.VpcId' \
  --output text)

echo "  VPC ID: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames \
  --region $REGION

# -----------------------------------------------------------------------------
# 2. Create Internet Gateway
# -----------------------------------------------------------------------------
echo "[2/8] Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=${PROJECT_NAME}-igw}]" \
  --region $REGION \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)

echo "  IGW ID: $IGW_ID"

# Attach to VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID \
  --region $REGION

# -----------------------------------------------------------------------------
# 3. Create Subnet
# -----------------------------------------------------------------------------
echo "[3/8] Creating Subnet..."
SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block $SUBNET_CIDR \
  --availability-zone $AZ \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-subnet}]" \
  --region $REGION \
  --query 'Subnet.SubnetId' \
  --output text)

echo "  Subnet ID: $SUBNET_ID"

# Enable auto-assign public IP
aws ec2 modify-subnet-attribute \
  --subnet-id $SUBNET_ID \
  --map-public-ip-on-launch \
  --region $REGION

# -----------------------------------------------------------------------------
# 4. Create Route Table
# -----------------------------------------------------------------------------
echo "[4/8] Creating Route Table..."
RTB_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT_NAME}-rtb}]" \
  --region $REGION \
  --query 'RouteTable.RouteTableId' \
  --output text)

echo "  Route Table ID: $RTB_ID"

# Add route to IGW
aws ec2 create-route \
  --route-table-id $RTB_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID \
  --region $REGION > /dev/null

# Associate with subnet
aws ec2 associate-route-table \
  --route-table-id $RTB_ID \
  --subnet-id $SUBNET_ID \
  --region $REGION > /dev/null

# -----------------------------------------------------------------------------
# 5. Create Security Group
# -----------------------------------------------------------------------------
echo "[5/8] Creating Security Group..."
SG_ID=$(aws ec2 create-security-group \
  --group-name "${PROJECT_NAME}-sg" \
  --description "A2A SNS Security Group" \
  --vpc-id $VPC_ID \
  --region $REGION \
  --query 'GroupId' \
  --output text)

echo "  Security Group ID: $SG_ID"

# Get current IP
MY_IP=$(curl -s ifconfig.me)
echo "  Your IP: $MY_IP"

# Allow SSH from your IP only
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr "${MY_IP}/32" \
  --region $REGION > /dev/null

# Allow HTTP (8080-8084) from your IP only
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8080-8084 \
  --cidr "${MY_IP}/32" \
  --region $REGION > /dev/null

# Outbound rules - restricted to necessary services only
echo "  Setting up restricted outbound rules..."

# Remove default allow-all egress rule
DEFAULT_EGRESS=$(aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --region $REGION \
  --query 'SecurityGroups[0].IpPermissionsEgress[?IpProtocol==`-1`].IpRanges[0].CidrIp' \
  --output text 2>/dev/null)

if [ "$DEFAULT_EGRESS" = "0.0.0.0/0" ]; then
  aws ec2 revoke-security-group-egress \
    --group-id $SG_ID \
    --protocol -1 \
    --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true
fi

# Allow HTTPS (443) outbound - for API calls (YouTube, Anthropic, etc.)
aws ec2 authorize-security-group-egress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0 \
  --region $REGION 2>/dev/null || true

# Allow HTTP (80) outbound - for package updates
aws ec2 authorize-security-group-egress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region $REGION 2>/dev/null || true

# Allow DNS (53) outbound
aws ec2 authorize-security-group-egress \
  --group-id $SG_ID \
  --protocol udp \
  --port 53 \
  --cidr 0.0.0.0/0 \
  --region $REGION 2>/dev/null || true

aws ec2 authorize-security-group-egress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 53 \
  --cidr 0.0.0.0/0 \
  --region $REGION 2>/dev/null || true

echo "  ✅ Outbound restricted to HTTPS/HTTP/DNS only"

# -----------------------------------------------------------------------------
# 6. Create Key Pair
# -----------------------------------------------------------------------------
echo "[6/8] Creating Key Pair..."
KEY_NAME="${PROJECT_NAME}-key"
KEY_FILE="$HOME/.ssh/${KEY_NAME}.pem"

if [ -f "$KEY_FILE" ]; then
  echo "  Key file already exists: $KEY_FILE"
  echo "  Skipping key creation..."
else
  aws ec2 create-key-pair \
    --key-name $KEY_NAME \
    --query 'KeyMaterial' \
    --output text \
    --region $REGION > $KEY_FILE

  chmod 400 $KEY_FILE
  echo "  Key saved: $KEY_FILE"
fi

# -----------------------------------------------------------------------------
# 7. Launch EC2 Instance
# -----------------------------------------------------------------------------
echo "[7/8] Launching EC2 Instance..."

# User data script (runs on first boot)
USER_DATA=$(cat <<'USERDATA'
#!/bin/bash
# Install basics
dnf update -y
dnf install -y git curl wget htop tmux jq

# Install Docker
dnf install -y docker
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Install Python
dnf install -y python3.11 python3.11-pip

# Create app directory
mkdir -p /opt/a2a-sns
chown ec2-user:ec2-user /opt/a2a-sns

echo "Setup complete!" > /home/ec2-user/setup-done.txt
USERDATA
)

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --subnet-id $SUBNET_ID \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --user-data "$USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT_NAME}-server}]" \
  --region $REGION \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "  Instance ID: $INSTANCE_ID"

# -----------------------------------------------------------------------------
# 8. Wait for Instance
# -----------------------------------------------------------------------------
echo "[8/8] Waiting for instance to be running..."
aws ec2 wait instance-running \
  --instance-ids $INSTANCE_ID \
  --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --region $REGION)

echo "  Public IP: $PUBLIC_IP"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Resources created:"
echo "  VPC:            $VPC_ID"
echo "  Subnet:         $SUBNET_ID"
echo "  Internet GW:    $IGW_ID"
echo "  Route Table:    $RTB_ID"
echo "  Security Group: $SG_ID"
echo "  Key Pair:       $KEY_NAME"
echo "  Instance:       $INSTANCE_ID"
echo "  Public IP:      $PUBLIC_IP"
echo ""
echo "SSH Key: $KEY_FILE"
echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Wait 2-3 minutes for user-data to complete"
echo ""
echo "2. SSH into the instance:"
echo "   ssh -i $KEY_FILE ec2-user@$PUBLIC_IP"
echo ""
echo "3. Login to Claude Code:"
echo "   claude login"
echo ""
echo "4. Clone and start:"
echo "   cd /opt/a2a-sns"
echo "   git clone https://github.com/RenTonoduka/A2A-SNS.git ."
echo "   bash deploy/quick-start.sh"
echo ""
echo "=========================================="

# Save config for cleanup
cat > /tmp/a2a-sns-aws-config.txt <<EOF
VPC_ID=$VPC_ID
SUBNET_ID=$SUBNET_ID
IGW_ID=$IGW_ID
RTB_ID=$RTB_ID
SG_ID=$SG_ID
KEY_NAME=$KEY_NAME
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$PUBLIC_IP
REGION=$REGION
EOF

echo "Config saved to /tmp/a2a-sns-aws-config.txt"
