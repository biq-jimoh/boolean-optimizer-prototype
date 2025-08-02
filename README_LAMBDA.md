# Bankruptcy Query Optimizer - AWS Lambda API

This directory contains the AWS Lambda deployment configuration for the Bankruptcy Query Optimizer API.

## 🚀 Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- Docker installed
- Node.js and npm installed
- AWS CLI configured
- OpenAI API key

### Deploy in 3 Steps

1. **Set your API keys:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export BRAVE_SEARCH_API_KEY="your-brave-api-key"  # Optional
   ```

2. **Run the deployment script:**
   ```bash
   ./deploy.sh --stage prod --region us-east-1
   ```

3. **Test the API:**
   ```bash
   # Get your API key from the AWS Console, then:
   curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/optimize \
     -H "X-Api-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"query": "preference action trustee"}'
   ```

## 📁 Project Structure

```
.
├── lambda_handler.py           # Main Lambda function handler
├── requirements-lambda.txt     # Lambda-optimized dependencies
├── Dockerfile                  # Container image for Lambda
├── serverless.yml             # Serverless Framework configuration
├── deploy.sh                  # Deployment automation script
├── test_lambda_local.py       # Local testing script
├── schemas/                   # API request validation schemas
│   ├── optimize-request.json
│   └── batch-request.json
└── docs/
    ├── AWS_LAMBDA_API_PLAN.md    # Architecture and planning
    ├── API_DOCUMENTATION.md       # API reference
    └── DEPLOYMENT_GUIDE.md        # Detailed deployment guide
```

## 🧪 Local Testing

Test the Lambda function locally before deployment:

```bash
# Test all endpoints
python test_lambda_local.py

# Test specific endpoint
python test_lambda_local.py optimize_simple
```

## 🔑 API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/optimize` | POST | Optimize a single query | Yes |
| `/optimize/batch` | POST | Optimize multiple queries | Yes |
| `/health` | GET | Health check | No |
| `/consultants` | GET | List consultant agents | Yes |

## ⚙️ Configuration

### Environment Variables
- `OPENAI_API_KEY` - Required for GPT-4.1 access
- `BRAVE_SEARCH_API_KEY` - Optional, enables web search for citations
- `MODEL` - OpenAI model to use (default: gpt-4.1)
- `TEMPERATURE` - Model temperature (default: 0.0)

### Lambda Settings
- **Timeout**: 5 minutes
- **Memory**: 3008 MB (3 GB)
- **Runtime**: Python 3.11 (container image)

## 🏗️ Architecture

The API is built using:
- **AWS Lambda** for serverless compute
- **API Gateway** for HTTP endpoints and authentication
- **Docker** for consistent deployment package
- **CloudWatch** for logging and monitoring

## 📊 Monitoring

View Lambda logs:
```bash
serverless logs -f optimize --stage prod --tail
```

Key metrics to monitor:
- Invocation count
- Error rate
- Duration (avg/p99)
- Cold start frequency

## 💰 Cost Estimation

Based on typical usage:
- **Lambda**: ~$0.02-0.05 per optimization
- **API Gateway**: $3.50 per million requests
- **Total**: ~$20-50/month for moderate usage (1000 requests/day)

## 🚨 Troubleshooting

### Common Issues

1. **Timeout errors**: Increase Lambda timeout or optimize consultant execution
2. **Cold starts**: Enable provisioned concurrency for consistent performance
3. **API key issues**: Check API Gateway configuration and key association
4. **Memory errors**: Increase Lambda memory allocation

### Debug Commands

```bash
# View recent logs
serverless logs -f optimize --stage prod

# Get function info
serverless info --stage prod --verbose

# Update function code
serverless deploy function -f optimize --stage prod
```

## 🔄 Updates and Rollbacks

Update the deployment:
```bash
./deploy.sh --stage prod
```

Rollback to previous version:
```bash
serverless rollback --stage prod
```

## 📝 License

This Lambda deployment configuration follows the same license as the main project.

## 🤝 Support

For issues or questions:
1. Check the [API Documentation](API_DOCUMENTATION.md)
2. Review the [Deployment Guide](DEPLOYMENT_GUIDE.md)
3. Check CloudWatch logs for errors