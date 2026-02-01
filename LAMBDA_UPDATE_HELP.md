# Lambda Update Workaround

## Issue
IAM policy propagation can take 5-10 minutes. Meanwhile, you can update via AWS Console.

## Quick Update via Console
1. Go to: https://console.aws.amazon.com/lambda
2. Click **OpenSearchExport** function
3. Click **Upload from** → **.zip file**
4. Choose `opensearch-export.zip` from `F:\aws_opensearch\`
5. Click **Save**

## Or Wait and Retry
After 5-10 minutes, run:
```bash
aws lambda update-function-code --function-name OpenSearchExport --zip-file fileb://opensearch-export.zip
```

## Current Status
- ✅ Lambda function deployed
- ✅ IAM policy attached  
- ⏳ Waiting for AWS propagation
