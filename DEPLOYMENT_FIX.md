# MedLearn AI - Weaviate Cloud Deployment Fix

## Problem
Weaviate connection failing in Render deployment despite correct environment variables.

## Root Cause
The RAG service initialization was failing silently without detailed error logging, making it impossible to diagnose the connection issue.

## Solution Implemented

### 1. Enhanced RAG Service Logging (`rag_service.py`)
- Added detailed initialization logging with clear status messages
- Added full exception tracebacks for all connection attempts
- Added summary status at end (SUCCESS or FAILURE)
- Prints actual URL and API key length for verification

### 2. Added Diagnostics Endpoint (`start.py`)
New endpoint: `GET /diagnostics`

Returns:
```json
{
  "timestamp": "2024-12-18T22:45:00",
  "services": {
    "rag": {
      "status": "connected|disconnected|error",
      "is_cloud": true,
      "has_embedding_model": true,
      "weaviate_url": "https://f7mb9hfbsf...",
      "weaviate_api_key": "set|not set"
    },
    "genai": { "status": "ready" },
    "learner": { "status": "ready" }
  }
}
```

## Deployment Steps

### 1. Update Your Render Service

In Render Dashboard:
1. Go to your `medlearn-ai` service
2. **Environment Variables** - Verify these are set:
   ```
   WEAVIATE_URL=https://f7mb9hfbsf24gzezrpqtqa.c0.us-west3.gcp.weaviate.cloud
   WEAVIATE_API_KEY=b2tBeTJKVE5wMStXeERWRV9WQzZ5VytldmQzM2ZGUTdUTmVjRy93Rk9ldEkrV2JDL1ptZFFaUU1iOFowPV92MjAw
   ```

### 2. Deploy Updated Code

Option A - Manual File Upload (if using Render's manual deployment):
1. Upload all files from this package
2. Trigger manual deploy

Option B - Git Deployment (recommended):
1. Push these files to your repository
2. Render will auto-deploy

### 3. Check Deployment Logs

After deployment, look for these messages in Render logs:

**SUCCESS:**
```
============================================================
📧 RAG Service Initialization
============================================================
   WEAVIATE_URL set: True
   WEAVIATE_API_KEY set: True
   URL: https://f7mb9hfbsf24gzezrpqtqa.c0.us-west3.gcp.weaviate.cloud...
   API Key: b2tBeTJKVE5wMStXeERW...

🌐 Attempting Weaviate Cloud connection: https://...
   Method 1: connect_to_weaviate_cloud...
   ✅ Connected via connect_to_weaviate_cloud

📦 Loading embedding model...
   ✅ Embedding model loaded
   ✅ HospitalDocument collection exists

============================================================
✅ RAG SERVICE READY
   Mode: Cloud
============================================================
```

**FAILURE:**
```
❌ ALL WEAVIATE CONNECTION METHODS FAILED
   Last error: [error message here]
   URL: https://...
   API Key length: 96
```

### 4. Test the Diagnostics Endpoint

Once deployed, visit:
```
https://medlearn-ai-1-zej7.onrender.com/diagnostics
```

This will show you:
- Whether RAG service connected
- Which Weaviate instance (cloud vs local)
- Whether embedding model loaded
- Status of all services

### 5. Common Issues & Fixes

**Issue: "Method 1 failed: SSL: CERTIFICATE_VERIFY_FAILED"**
- **Cause:** Render's environment may have SSL certificate issues
- **Fix:** This is why we try 3 different connection methods
- **Expected:** Method 2 or 3 should succeed

**Issue: "Method 1-3 all failed: connection timeout"**
- **Cause:** Weaviate cluster URL is incorrect or cluster is down
- **Fix:** 
  1. Verify cluster is running in Weaviate Cloud Console
  2. Check URL is exactly: `https://f7mb9hfbsf24gzezrpqtqa.c0.us-west3.gcp.weaviate.cloud`
  3. No trailing slash
  4. Includes `https://`

**Issue: "Method 1-3 all failed: authentication failed"**
- **Cause:** API key is incorrect
- **Fix:** 
  1. Go to Weaviate Cloud Console
  2. Go to your cluster details
  3. Regenerate API key if needed
  4. Update WEAVIATE_API_KEY in Render

**Issue: Environment variables not set (shows False)**
- **Cause:** Variables not saved in Render
- **Fix:**
  1. In Render dashboard, click "Environment"
  2. Add both variables
  3. Click "Save Changes"
  4. **Important:** Trigger manual deploy after saving

### 6. Test Document Upload

Once RAG service shows as connected:

1. Visit: `https://medlearn-ai-1-zej7.onrender.com`
2. Navigate to "Smart Authoring"
3. Try uploading a PDF document
4. Should see upload progress and success message

## Files Modified

1. **rag_service.py** - Enhanced logging and error reporting
2. **start.py** - Added `/diagnostics` endpoint with RAG status
3. All other files unchanged

## Verification Checklist

- [ ] Environment variables set in Render
- [ ] New code deployed to Render
- [ ] Deployment logs show RAG SERVICE READY
- [ ] `/diagnostics` endpoint shows RAG status: "connected"
- [ ] Can upload documents through UI
- [ ] Can search uploaded documents

## Next Steps After Connection Success

Once Weaviate connects successfully:

1. Test document upload with small PDF
2. Test RAG search functionality
3. Monitor Render logs for any errors
4. Check Weaviate Cloud Console for indexed data

## Support

If still having issues after following this guide:

1. Check Render deployment logs for the exact error message
2. Visit `/diagnostics` endpoint and share the JSON output
3. Verify Weaviate sandbox cluster is active in Weaviate Cloud Console
4. Try regenerating the API key in Weaviate Console

## Environment Variable Format Reference

```bash
# Correct format (no quotes in Render UI)
WEAVIATE_URL=https://f7mb9hfbsf24gzezrpqtqa.c0.us-west3.gcp.weaviate.cloud
WEAVIATE_API_KEY=b2tBeTJKVE5wMStXeERWRV9WQzZ5VytldmQzM2ZGUTdUTmVjRy93Rk9ldEkrV2JDL1ptZFFaUU1iOFowPV92MjAw

# Wrong (don't use quotes)
WEAVIATE_URL="https://..."
```
