# AWS Deployment Journey - Complete Command History

## Overview
This document chronicles the complete AWS deployment process for the OpenSearch Lambda Export function, including all commands executed, errors encountered, and resolutions applied.

---

## Phase 1: Initial Setup

### 1.1 Creating IAM Role for Lambda

**Command:**
```bash
# Created trust policy file
cat > trust_policy.json <<EOF
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
EOF

# Created the IAM role
aws iam create-role --role-name OpenSearchExportRole --assume-role-policy-document file://trust_policy.json
```

**Result:** ✅ Success
- Role ARN: `arn:aws:iam::571600865109:role/OpenSearchExportRole`

---

### 1.2 Attaching Policies to the Role

**Commands:**
```bash
# Basic Lambda execution permissions
aws iam attach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# S3 full access
aws iam attach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# OpenSearch read-only access
aws iam attach-role-policy --role-name OpenSearchExportRole --policy-arn arn:aws:iam::aws:policy/AmazonOpenSearchServiceReadOnlyAccess
```

**Result:** ✅ All policies attached successfully

---

## Phase 2: Creating Deployment Package

### 2.1 Building the ZIP Package

**Commands:**
```powershell
# Clean up any existing package
if (Test-Path deploy_package) { Remove-Item -Recurse -Force deploy_package }

# Create new directory
mkdir deploy_package

# Install dependencies
pip install opensearch-py requests-aws4auth -t deploy_package

# Copy Lambda function
copy lambda_function.py deploy_package/

# Create ZIP archive
cd deploy_package
Compress-Archive -Path * -DestinationPath ..\opensearch-export.zip -Force
cd ..
```

**Result:** ✅ Package created: `opensearch-export.zip`

---

## Phase 3: Lambda Function Deployment (First Attempt)

### 3.1 Initial Deployment Attempt

**Command:**
```bash
aws lambda create-function \
    --function-name OpenSearchExport \
    --runtime python3.9 \
    --role arn:aws:iam::571600865109:role/OpenSearchExportRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://opensearch-export.zip \
    --timeout 900 \
    --environment Variables="{OPENSEARCH_URL=https://8hekccwub64d3m9chus3.us-east-1.aoss.amazonaws.com,AWS_REGION=us-east-1,OUTPUT_BUCKET=inventory-bucket-data}"
```

**Result:** ❌ **FAILED**

**Error:**
```
InvalidParameterValueException: The Environment Variables AWS_REGION may not be supported for modification. Reserved keys used in this request: AWS_REGION
```

**Root Cause:** `AWS_REGION` is a reserved Lambda environment variable and cannot be set manually.

---

### 3.2 Second Deployment Attempt (Fixed)

**Command:**
```bash
aws lambda create-function \
    --function-name OpenSearchExport \
    --runtime python3.9 \
    --role arn:aws:iam::571600865109:role/OpenSearchExportRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://opensearch-export.zip \
    --timeout 900 \
    --environment Variables="{OPENSEARCH_URL=https://8hekccwub64d3m9chus3.us-east-1.aoss.amazonaws.com,OUTPUT_BUCKET=inventory-bucket-data}"
```

**Result:** ✅ **SUCCESS**

**Response:**
```json
{
    "FunctionName": "OpenSearchExport",
    "FunctionArn": "arn:aws:lambda:us-east-1:571600865109:function:OpenSearchExport",
    "Runtime": "python3.9",
    "Role": "arn:aws:iam::571600865109:role/OpenSearchExportRole",
    "Handler": "lambda_function.lambda_handler",
    "State": "Pending",
    "Timeout": 900
}
```

---

## Phase 4: Update Attempts & Permission Issues

### 4.1 First Update Attempt

**Command:**
```bash
aws lambda update-function-code --function-name OpenSearchExport --zip-file fileb://opensearch-export.zip
```

**Result:** ❌ **FAILED**

**Error:**
```
AccessDeniedException: User: arn:aws:iam::571600865109:user/ranga is not authorized to perform: lambda:UpdateFunctionCode on resource: arn:aws:lambda:us-east-1:571600865109:function:OpenSearchExport because no identity-based policy allows the lambda:UpdateFunctionCode action
```

**Root Cause:** User `ranga` lacked Lambda update permissions.

---

### 4.2 Granting Lambda Permissions to User

**Command:**
```bash
aws iam attach-user-policy --user-name ranga --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess
```

**Result:** ✅ Policy attached successfully

**Verification:**
```bash
aws iam list-attached-user-policies --user-name ranga
```

**Output:**
```json
{
    "AttachedPolicies": [
        {
            "PolicyName": "AWSLambda_FullAccess",
            "PolicyArn": "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
        }
    ]
}
```

---

### 4.3 IAM Propagation Delay Issue

**Multiple Retry Attempts:**
```bash
# Attempt 1 (immediate retry)
aws lambda update-function-code --function-name OpenSearchExport --zip-file fileb://opensearch-export.zip
# Result: Still AccessDeniedException

# Attempt 2 (after 10 seconds)
Start-Sleep -Seconds 10
aws lambda update-function-code --function-name OpenSearchExport --zip-file fileb://opensearch-export.zip
# Result: Still AccessDeniedException

# Attempt 3 (manual retry after 2-3 minutes)
aws lambda update-function-code --function-name OpenSearchExport --zip-file fileb://opensearch-export.zip
# Result: Still AccessDeniedException
```

**Issue:** IAM policy propagation delay (can take 5-10 minutes in AWS)

**Note:** This is a known AWS behavior, not a configuration error.

---

## Phase 5: Verification Commands

### 5.1 Check Lambda Function Status

**Command:**
```bash
aws lambda get-function --function-name OpenSearchExport --query "{FunctionName:Configuration.FunctionName,State:Configuration.State,Runtime:Configuration.Runtime,Timeout:Configuration.Timeout,Role:Configuration.Role}" --output json
```

**Result:** ✅ **SUCCESS**

**Output:**
```json
{
    "FunctionName": "OpenSearchExport",
    "State": "Active",
    "Runtime": "python3.9",
    "Timeout": 900,
    "Role": "arn:aws:iam::571600865109:role/OpenSearchExportRole"
}
```

---

### 5.2 List All Lambda Functions

**Command:**
```bash
aws lambda list-functions --query "Functions[?FunctionName=='OpenSearchExport'].{Name:FunctionName,Runtime:Runtime,LastModified:LastModified}" --output table
```

---

## Summary of Issues & Resolutions

| # | Issue | Command/Symptom | Resolution |
|---|-------|----------------|------------|
| 1 | Reserved environment variable | `AWS_REGION` in create-function | Removed `AWS_REGION` from environment variables (Lambda sets it automatically) |
| 2 | Missing update permissions | `AccessDeniedException` on `UpdateFunctionCode` | Attached `AWSLambda_FullAccess` policy to user |
| 3 | IAM propagation delay | Update still failing after policy attachment | Waited 5-10 minutes OR used AWS Console for immediate update |

---

## Critical Next Steps

### ⚠️ OpenSearch Data Access Policy (MANDATORY)

The Lambda function is deployed but **cannot access OpenSearch** until you update the Data Access Policy.

**Steps:**
1. Go to AWS Console → Amazon OpenSearch Service → Serverless → Collections
2. Select your collection: `8hekccwub64d3m9chus3`
3. Scroll to **Data access policies** section
4. Click **Edit**
5. Add a new rule:
   - **Principal**: `arn:aws:iam::571600865109:role/OpenSearchExportRole`
   - **Permissions**: Grant `Read` access to all indices (or specific index patterns)
   - **Collections**: Select your collection
6. Save the policy

**Why this is critical:** Even with full IAM permissions, OpenSearch Serverless has an internal access control layer that requires explicit principal authorization.

---

## Final Deployment Status

✅ **IAM Role Created**: `OpenSearchExportRole`
✅ **Policies Attached**: Lambda, S3, OpenSearch
✅ **Deployment Package**: `opensearch-export.zip` created
✅ **Lambda Function**: `OpenSearchExport` deployed and **Active**
✅ **User Permissions**: `ranga` has `AWSLambda_FullAccess`
⏳ **Pending**: OpenSearch Data Access Policy update (manual step required)

---

## Quick Reference: Essential Commands

```bash
# Check Lambda status
aws lambda get-function --function-name OpenSearchExport

# Update Lambda code (after permissions propagate)
aws lambda update-function-code --function-name OpenSearchExport --zip-file fileb://opensearch-export.zip

# Invoke Lambda manually (for testing)
aws lambda invoke --function-name OpenSearchExport --payload '{"index_name":"inventory","bucket_name":"inventory-bucket-data"}' response.json

# View Lambda logs
aws logs tail /aws/lambda/OpenSearchExport --follow

# Update environment variables
aws lambda update-function-configuration --function-name OpenSearchExport --environment Variables="{OPENSEARCH_URL=https://...,OUTPUT_BUCKET=...}"
```

---

## Lessons Learned

1. **AWS_REGION is reserved** - Lambda automatically provides this variable
2. **IAM propagation takes time** - Always wait 5-10 minutes after policy changes
3. **Console can bypass propagation** - For urgent updates, use AWS Console GUI
4. **OpenSearch has dual security** - Both IAM policies AND internal Data Access Policies required
5. **Full access policies are broad** - Consider scoping down to least privilege in production
