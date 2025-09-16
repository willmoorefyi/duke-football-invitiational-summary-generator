#!/bin/bash
#
# Deploy DynamoDB infrastructure for Fantasy Football League
#
# Usage:
#   ./infrastructure/deploy.sh [environment] [table-name]
#
# Examples:
#   ./infrastructure/deploy.sh prod
#   ./infrastructure/deploy.sh dev fantasy-league-data-test

set -e

# Default values
ENVIRONMENT=${1:-prod}
TABLE_NAME=${2:-fantasy-league-data}
STACK_NAME="fantasy-league-dynamodb-${ENVIRONMENT}"
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "🚀 Deploying Fantasy Football DynamoDB Infrastructure"
echo "   Environment: ${ENVIRONMENT}"
echo "   Table Name: ${TABLE_NAME}-${ENVIRONMENT}"
echo "   Stack Name: ${STACK_NAME}"
echo "   Region: ${REGION}"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Deploy CloudFormation stack
echo "📋 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file infrastructure/fantasy-league-dynamodb.yaml \
    --stack-name "${STACK_NAME}" \
    --parameter-overrides \
        TableName="${TABLE_NAME}" \
        Environment="${ENVIRONMENT}" \
    --region "${REGION}" \
    --no-fail-on-empty-changeset

# Get stack outputs
echo ""
echo "📊 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "✅ DynamoDB table deployed successfully!"
echo ""
echo "🔧 Next steps:"
echo "   1. Update your pipeline configuration to use table: ${TABLE_NAME}-${ENVIRONMENT}"
echo "   2. Test the upload pipeline stage"
echo "   3. Implement the aggregate pipeline stage"