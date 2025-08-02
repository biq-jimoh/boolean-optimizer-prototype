# AWS Lambda Deployment Guide

This guide walks through deploying the Bankruptcy Query Optimizer as a serverless API on AWS Lambda.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Docker** installed (for building container image)
4. **Node.js** and npm (for Serverless Framework)
5. **API Keys**:
   - OpenAI API key (required)
   - Brave Search API key (optional)

## Deployment Options

### Option 1: Using Serverless Framework (Recommended)

#### 1. Install Serverless Framework

```bash
npm install -g serverless
npm install -g serverless-python-requirements
npm install -g serverless-api-gateway-throttling
```

#### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"
export BRAVE_SEARCH_API_KEY="your-brave-api-key"  # Optional
```

#### 3. Deploy to AWS

```bash
# Deploy to development
serverless deploy --stage dev

# Deploy to production
serverless deploy --stage prod

# Deploy with custom settings
serverless deploy --stage prod \
  --param="PROVISIONED_CONCURRENCY=2" \
  --param="RESERVED_CONCURRENCY=50"
```

#### 4. Get API Information

```bash
# Get deployment info
serverless info --stage prod

# Get API key
serverless info --stage prod --verbose | grep "api keys" -A 5
```

### Option 2: Using AWS SAM

#### 1. Create SAM Template

Create `template.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Parameters:
  OpenAIApiKey:
    Type: String
    NoEcho: true
  BraveApiKey:
    Type: String
    Default: ''
    NoEcho: true

Globals:
  Function:
    Timeout: 300
    MemorySize: 3008
    Runtime: python3.11

Resources:
  OptimizeFunction:
    Type: AWS::Serverless::Function
    Properties:
      PackageType: Image
      ImageConfig:
        Command: ["lambda_handler.lambda_handler"]
      Environment:
        Variables:
          OPENAI_API_KEY: !Ref OpenAIApiKey
          BRAVE_SEARCH_API_KEY: !Ref BraveApiKey
      Events:
        OptimizeApi:
          Type: Api
          Properties:
            Path: /optimize
            Method: post
            Auth:
              ApiKeyRequired: true
        BatchApi:
          Type: Api
          Properties:
            Path: /optimize/batch
            Method: post
            Auth:
              ApiKeyRequired: true
        HealthApi:
          Type: Api
          Properties:
            Path: /health
            Method: get
        ConsultantsApi:
          Type: Api
          Properties:
            Path: /consultants
            Method: get
            Auth:
              ApiKeyRequired: true
    Metadata:
      DockerTag: latest
      DockerContext: ./
      Dockerfile: Dockerfile
```

#### 2. Build and Deploy

```bash
# Build the application
sam build

# Deploy (guided for first time)
sam deploy --guided

# Subsequent deployments
sam deploy
```

### Option 3: Manual Deployment with Docker

#### 1. Build Docker Image

```bash
# Build the image
docker build -t bankruptcy-optimizer .

# Test locally
docker run -p 9000:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  bankruptcy-optimizer
```

#### 2. Push to ECR

```bash
# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name bankruptcy-optimizer

# Tag image
docker tag bankruptcy-optimizer:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/bankruptcy-optimizer:latest

# Push image
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/bankruptcy-optimizer:latest
```

#### 3. Create Lambda Function

```bash
# Create Lambda function
aws lambda create-function \
  --function-name bankruptcy-optimizer \
  --package-type Image \
  --code ImageUri=123456789.dkr.ecr.us-east-1.amazonaws.com/bankruptcy-optimizer:latest \
  --role arn:aws:iam::123456789:role/lambda-execution-role \
  --timeout 300 \
  --memory-size 3008 \
  --environment Variables="{OPENAI_API_KEY=$OPENAI_API_KEY}"
```

## Post-Deployment Configuration

### 1. Configure API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name bankruptcy-optimizer \
  --endpoint-configuration types=REGIONAL

# Create usage plan
aws apigateway create-usage-plan \
  --name basic-plan \
  --throttle burstLimit=20,rateLimit=10 \
  --quota limit=10000,period=MONTH
```

### 2. Create API Key

```bash
# Create API key
aws apigateway create-api-key \
  --name client-key \
  --enabled

# Associate with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id <usage-plan-id> \
  --key-id <api-key-id> \
  --key-type API_KEY
```

### 3. Set Up CloudWatch Alarms

```bash
# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name bankruptcy-optimizer-errors \
  --alarm-description "High error rate" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1

# Throttling alarm
aws cloudwatch put-metric-alarm \
  --alarm-name bankruptcy-optimizer-throttles \
  --alarm-description "Function throttling" \
  --metric-name Throttles \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

## Testing the Deployment

### 1. Health Check

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/health
```

### 2. Test Query Optimization

```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/optimize \
  -H "X-Api-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "preference action trustee",
    "options": {
      "version": 3
    }
  }'
```

## Monitoring and Maintenance

### CloudWatch Logs

View logs:
```bash
aws logs tail /aws/lambda/bankruptcy-optimizer --follow
```

### Metrics to Monitor

1. **Invocation count**: Track usage patterns
2. **Error rate**: Should be < 1%
3. **Duration**: Average < 5 seconds
4. **Throttles**: Should be 0
5. **Concurrent executions**: Monitor against limits

### Cost Optimization

1. **Right-size memory**: Start with 3GB, adjust based on metrics
2. **Use provisioned concurrency** only for consistent traffic
3. **Implement caching** to reduce OpenAI API calls
4. **Monitor cold starts**: Consider SnapStart if needed

## Troubleshooting

### Common Issues

1. **Timeout errors**:
   - Increase Lambda timeout (max 15 minutes)
   - Optimize consultant execution
   - Consider Step Functions for longer workflows

2. **Memory errors**:
   - Increase Lambda memory
   - Optimize consultant prompts
   - Reduce parallel execution

3. **Cold start latency**:
   - Use provisioned concurrency
   - Optimize container image size
   - Implement warm-up pings

4. **API Gateway errors**:
   - Check API key configuration
   - Verify CORS settings
   - Review request/response mappings

## Security Best Practices

1. **Secrets Management**:
   ```bash
   # Store API keys in Secrets Manager
   aws secretsmanager create-secret \
     --name bankruptcy-optimizer/openai-key \
     --secret-string $OPENAI_API_KEY
   ```

2. **IAM Permissions**:
   - Use least privilege principle
   - Separate roles for dev/prod
   - Enable CloudTrail logging

3. **API Security**:
   - Rotate API keys regularly
   - Implement IP whitelisting if needed
   - Use AWS WAF for additional protection

## Rollback Procedure

If issues arise:

```bash
# Using Serverless Framework
serverless rollback --stage prod

# Using SAM
sam deploy --stack-name bankruptcy-optimizer \
  --parameter-overrides Version=previous

# Manual rollback
aws lambda update-function-code \
  --function-name bankruptcy-optimizer \
  --image-uri <previous-image-uri>
```