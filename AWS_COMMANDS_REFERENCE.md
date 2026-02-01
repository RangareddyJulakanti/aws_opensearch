# AWS OpenSearch Lambda Deployment - Command Reference Guide

**For Production/Organizational Use**

## Overview
This guide provides tested AWS CLI commands for deploying a Lambda function that exports OpenSearch data to S3. All commands are production-ready and safe for organizational environments.

---

## Prerequisites Checklist

Before running any commands, ensure:

- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Active AWS account with appropriate permissions
- [ ] Python 3.8+ installed locally
- [ ] OpenSearch Serverless collection already created
- [ ] S3 bucket for exports already created
- [ ] Deployment package (`opensearch-export.zip`) prepared

---

## Section 1: IAM Role Setup

### 1.1 Create Lambda Trust Policy

**Purpose:** Define which AWS services can assume this role

**File: `trust_policy.json`**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Command:**
```bash
aws iam create-role \
    --role-name OpenSearchExportRole \
    --assume-role-policy-document file://trust_policy.json
```

**Expected Output:** Role ARN (save this for later)
```
arn:aws:iam::{ACCOUNT_ID}:role/OpenSearchExportRole
```

---

### 1.2 Attach Required Policies

**Purpose:** Grant the role necessary permissions

**Command 1: Basic Lambda Logging**
```bash
aws iam attach-role-policy \
    --role-name OpenSearchExportRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**Command 2: S3 Write Access**
```bash
aws iam attach-role-policy \
    --role-name OpenSearchExportRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**Command 3: OpenSearch Read Access**
```bash
aws iam attach-role-policy \
    --role-name OpenSearchExportRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonOpenSearchServiceReadOnlyAccess
```

**Notes:**
- For production, consider creating custom policies with least privilege
- `AmazonS3FullAccess` can be scoped to specific buckets only

---

## Section 2: Deployment Package Creation

### 2.1 Install Dependencies (Windows PowerShell)

```powershell
# Create clean directory
if (Test-Path deploy_package) { Remove-Item -Recurse -Force deploy_package }
mkdir deploy_package

# Install Python dependencies
pip install opensearch-py requests-aws4auth -t deploy_package

# Copy Lambda function
copy lambda_function.py deploy_package/

# Create ZIP archive
cd deploy_package
Compress-Archive -Path * -DestinationPath ..\opensearch-export.zip -Force
cd ..
```

### 2.2 Install Dependencies (Linux/Mac)

```bash
# Create clean directory
rm -rf deploy_package
mkdir deploy_package

# Install Python dependencies
pip install opensearch-py requests-aws4auth -t deploy_package/

# Copy Lambda function
cp lambda_function.py deploy_package/

# Create ZIP archive
cd deploy_package
zip -r ../opensearch-export.zip .
cd ..
```

**Verification:**
```bash
# Check the ZIP file was created
ls -lh opensearch-export.zip
```

---

## Section 3: Lambda Function Deployment

### 3.1 Deploy Lambda Function

**Command:**
```bash
aws lambda create-function \
    --function-name OpenSearchExport \
    --runtime python3.9 \
    --role arn:aws:iam::{ACCOUNT_ID}:role/OpenSearchExportRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://opensearch-export.zip \
    --timeout 900 \
    --memory-size 512 \
    --environment Variables="{OPENSEARCH_URL=https://YOUR_COLLECTION_ID.REGION.aoss.amazonaws.com,OUTPUT_BUCKET=your-bucket-name}"
```

**Important Variables to Replace:**
- `{ACCOUNT_ID}` - Your AWS account ID
- `YOUR_COLLECTION_ID` - Your OpenSearch collection ID
- `REGION` - Your AWS region (e.g., us-east-1)
- `your-bucket-name` - Your S3 bucket name

**Expected Output:**
```json
{
    "FunctionName": "OpenSearchExport",
    "FunctionArn": "arn:aws:lambda:REGION:ACCOUNT_ID:function:OpenSearchExport",
    "State": "Pending"
}
```

**Common Issues:**
- ❌ **Error:** "Reserved environment variable AWS_REGION"
  - **Fix:** Do NOT include `AWS_REGION` in environment variables (Lambda sets it automatically)

---

### 3.2 Verify Deployment

**Command:**
```bash
aws lambda get-function \
    --function-name OpenSearchExport \
    --query "Configuration.{Name:FunctionName,State:State,Runtime:Runtime}" \
    --output table
```

**Expected State:** `Active`

---

## Section 4: Update Lambda Code (Future Updates)

### 4.1 Update Function Code

**When to use:** After making changes to `lambda_function.py`

**Command:**
```bash
# Rebuild the ZIP first (see Section 2)
# Then update:
aws lambda update-function-code \
    --function-name OpenSearchExport \
    --zip-file fileb://opensearch-export.zip
```

---

### 4.2 Update Environment Variables

**Command:**
```bash
aws lambda update-function-configuration \
    --function-name OpenSearchExport \
    --environment Variables="{OPENSEARCH_URL=https://NEW_URL,OUTPUT_BUCKET=new-bucket}"
```

---

## Section 5: Testing & Monitoring

### 5.1 Manual Invocation (Test)

**Command:**
```bash
aws lambda invoke \
    --function-name OpenSearchExport \
    --payload '{"index_name":"inventory","bucket_name":"your-bucket"}' \
    response.json

# View response
cat response.json
```

---

### 5.2 View Logs

**Command:**
```bash
# Tail logs in real-time
aws logs tail /aws/lambda/OpenSearchExport --follow

# View specific time range
aws logs tail /aws/lambda/OpenSearchExport --since 1h
```

---

## Section 6: OpenSearch Data Access Policy (CRITICAL)

### ⚠️ MANDATORY STEP

Even with IAM permissions, OpenSearch Serverless requires explicit Data Access Policy configuration.

**Steps (AWS Console):**
1. Navigate to: **Amazon OpenSearch Service** → **Serverless** → **Collections**
2. Select your collection
3. Click **Data access policies**
4. Click **Edit** on your data access policy
5. Add new rule:
   ```json
   {
     "Rules": [
       {
         "ResourceType": "index",
         "Resource": ["index/*/*"],
         "Permission": ["aoss:ReadDocument", "aoss:DescribeIndex"]
       }
     ],
     "Principal": [
       "arn:aws:iam::{ACCOUNT_ID}:role/OpenSearchExportRole"
     ]
   }
   ```
6. **Save**

**Without this step, Lambda will fail with 403 Forbidden errors.**

---

## Section 7: Cleanup (When Needed)

### 7.1 Delete Lambda Function

```bash
aws lambda delete-function --function-name OpenSearchExport
```

### 7.2 Detach Policies and Delete Role

```bash
# Detach policies
aws iam detach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam detach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/AmazonOpenSearchServiceReadOnlyAccess

# Delete role
aws iam delete-role --role-name OpenSearchExportRole
```

---

## Section 8: Production Best Practices

### 8.1 Security Recommendations

✅ **Do:**
- Use least-privilege IAM policies
- Enable Lambda function versioning
- Use AWS Secrets Manager for sensitive credentials
- Enable CloudTrail for audit logging
- Use VPC endpoints for OpenSearch access
- Enable Lambda reserved concurrency limits
- Tag all resources for cost tracking

❌ **Don't:**
- Use `*FullAccess` policies in production
- Hardcode credentials in code
- Share IAM roles across environments
- Skip CloudWatch log retention policies

---

### 8.2 Cost Optimization

```bash
# Set memory to minimum required (reduces cost)
aws lambda update-function-configuration \
    --function-name OpenSearchExport \
    --memory-size 256

# Set appropriate timeout
aws lambda update-function-configuration \
    --function-name OpenSearchExport \
    --timeout 300
```

---

### 8.3 Monitoring Setup

**Create CloudWatch Alarm for Errors:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name OpenSearchExport-Errors \
    --alarm-description "Alert on Lambda errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value=OpenSearchExport \
    --evaluation-periods 1
```

---

## Section 9: Troubleshooting Guide

| Error | Cause | Solution |
|-------|-------|----------|
| `AccessDeniedException` on Lambda operations | User lacks Lambda permissions | Attach `AWSLambdaFullAccess` to user |
| `403 Forbidden` from OpenSearch | Missing Data Access Policy | Add Lambda role to OpenSearch Data Access Policy |
| `Invalid parameter: AWS_REGION` | Reserved environment variable | Remove `AWS_REGION` from environment variables |
| `ResourceNotFoundException` | Function doesn't exist | Verify function name and region |
| IAM policy changes not taking effect | Propagation delay | Wait 5-10 minutes after policy changes |

---

## Section 10: Required IAM Permissions (For Deploying User)

The user running these commands needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Quick Command Summary

```bash
# 1. Create Role
aws iam create-role --role-name OpenSearchExportRole --assume-role-policy-document file://trust_policy.json

# 2. Attach Policies
aws iam attach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# 3. Deploy Lambda
aws lambda create-function --function-name OpenSearchExport --runtime python3.9 --role arn:aws:iam::ACCOUNT:role/OpenSearchExportRole --handler lambda_function.lambda_handler --zip-file fileb://opensearch-export.zip --timeout 900 --environment Variables="{OPENSEARCH_URL=...,OUTPUT_BUCKET=...}"

# 4. Verify
aws lambda get-function --function-name OpenSearchExport

# 5. Test
aws lambda invoke --function-name OpenSearchExport --payload '{"index_name":"test"}' out.json
```

---

## Support & References

- AWS Lambda Documentation: https://docs.aws.amazon.com/lambda/
- OpenSearch Serverless: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html
- IAM Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-02  
**Status:** Production Ready
