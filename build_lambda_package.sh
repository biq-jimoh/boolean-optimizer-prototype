#!/bin/bash

echo "Building Lambda package with Docker for Linux compatibility..."

# Clean up old packages
rm -rf lambda-package lambda-deployment.zip

# Use Docker to build in Lambda-like environment
docker run --rm \
  -v "$PWD":/var/task \
  -w /var/task \
  public.ecr.aws/lambda/python:3.11 \
  /bin/sh -c "
    echo 'Installing dependencies for Linux...'
    pip install -r requirements-lambda.txt -t lambda-package/ --upgrade
    echo 'Copying application files...'
    cp *.py lambda-package/
    cp -r prompts lambda-package/
    cd lambda-package
    echo 'Cleaning up package...'
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete 2>/dev/null || true
    find . -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true
    rm -f test_*.py 2>/dev/null || true
    echo 'Creating zip file...'
    zip -r ../lambda-deployment.zip . -q
  "

echo "Package built successfully!"
ls -lh lambda-deployment.zip
