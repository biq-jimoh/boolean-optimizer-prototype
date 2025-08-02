# Multi-stage build for AWS Lambda container image
# This creates a lightweight container optimized for Lambda

# Build stage
FROM public.ecr.aws/lambda/python:3.11 as builder

# Install build dependencies
RUN yum install -y gcc python3-devel

# Copy requirements
COPY requirements-lambda.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-lambda.txt -t /opt/python

# Runtime stage
FROM public.ecr.aws/lambda/python:3.11

# Copy installed packages from builder
COPY --from=builder /opt/python ${LAMBDA_RUNTIME_DIR}

# Copy application code
COPY bankruptcy_query_optimizer.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY citation_detector.py ${LAMBDA_TASK_ROOT}/
COPY brave_search_service.py ${LAMBDA_TASK_ROOT}/
COPY content_validator.py ${LAMBDA_TASK_ROOT}/
COPY content_extractor.py ${LAMBDA_TASK_ROOT}/
COPY url_cleaner.py ${LAMBDA_TASK_ROOT}/
COPY token_budget.py ${LAMBDA_TASK_ROOT}/

# Copy prompts directory
COPY prompts/ ${LAMBDA_TASK_ROOT}/prompts/

# Set the handler
CMD ["lambda_handler.lambda_handler"]