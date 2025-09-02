#!/bin/bash

# Bankruptcy Query Optimizer - AWS Lambda Deployment Script
# This script helps deploy the application to AWS Lambda using Serverless Framework

# Ensure we run from repo root
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
STAGE="dev"
REGION="us-east-1"
PROFILE="default"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage)
            STAGE="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: ./scripts/deploy.sh [options]"
            echo "Options:"
            echo "  --stage <stage>     Deployment stage (default: dev)"
            echo "  --region <region>   AWS region (default: us-east-1)"
            echo "  --profile <profile> AWS profile (default: default)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Bankruptcy Query Optimizer Lambda Deployment ===${NC}"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo "AWS Profile: $PROFILE"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install AWS CLI first.${NC}"
    exit 1
fi

# Check for Serverless Framework
if ! command -v serverless &> /dev/null; then
    echo -e "${YELLOW}Serverless Framework not found. Installing...${NC}"
    npm install -g serverless
fi

# Install Serverless plugins
echo -e "${YELLOW}Installing Serverless plugins...${NC}"
npm install --save-dev serverless-python-requirements
npm install --save-dev serverless-api-gateway-throttling

# Check for required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}OPENAI_API_KEY environment variable is not set${NC}"
    echo "Please set it with: export OPENAI_API_KEY=your-key"
    exit 1
fi

echo -e "${GREEN}Prerequisites check passed!${NC}"
echo ""

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -f infra/Dockerfile -t bankruptcy-optimizer:latest .
if [ $? -ne 0 ]; then
    echo -e "${RED}Docker build failed${NC}"
    exit 1
fi
echo -e "${GREEN}Docker image built successfully!${NC}"
echo ""

# Deploy using Serverless Framework
echo -e "${YELLOW}Deploying to AWS Lambda...${NC}"
serverless deploy \
    --config infra/serverless.yml \
    --stage $STAGE \
    --region $REGION \
    --aws-profile $PROFILE \
    --verbose

if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Deployment Successful! ===${NC}"
echo ""

# Get deployment information
echo -e "${YELLOW}Getting deployment information...${NC}"
serverless info --config infra/serverless.yml --stage $STAGE --region $REGION --aws-profile $PROFILE

# Extract API endpoint and key
API_ENDPOINT=$(serverless info --config infra/serverless.yml --stage $STAGE --region $REGION --aws-profile $PROFILE | grep "POST" | head -1 | awk '{print $3}')
echo ""
echo -e "${GREEN}API Endpoint:${NC} $API_ENDPOINT"
echo ""

# Test the deployment
echo -e "${YELLOW}Testing health endpoint...${NC}"
HEALTH_ENDPOINT="${API_ENDPOINT%/optimize}/health"
curl -s "$HEALTH_ENDPOINT" | python -m json.tool

echo ""
echo -e "${GREEN}=== Next Steps ===${NC}"
echo "1. Get your API key from AWS Console or using:"
echo "   aws apigateway get-api-keys --profile $PROFILE"
echo ""
echo "2. Test the optimization endpoint:"
echo "   curl -X POST $API_ENDPOINT \\"
echo "     -H 'X-Api-Key: your-api-key' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"preference action trustee\"}'"
echo ""
echo "3. Monitor logs:"
echo "   serverless logs -f optimize --stage $STAGE --tail"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
