# Quick Deployment Checklist

## Before You Deploy

- [ ] Weaviate cluster is running in Weaviate Cloud Console
- [ ] You have the cluster URL ready
- [ ] You have the API key ready

## Render Dashboard Steps

### 1. Set Environment Variables
- [ ] Go to Render Dashboard
- [ ] Click on your service "medlearn-ai"
- [ ] Click "Environment" tab
- [ ] Add WEAVIATE_URL (no quotes):
  ```
  https://f7mb9hfbsf24gzezrpqtqa.c0.us-west3.gcp.weaviate.cloud
  ```
- [ ] Add WEAVIATE_API_KEY (no quotes):
  ```
  b2tBeTJKVE5wMStXeERWRV9WQzZ5VytldmQzM2ZGUTdUTmVjRy93Rk9ldEkrV2JDL1ptZFFaUU1iOFowPV92MjAw
  ```
- [ ] Click "Save Changes"

### 2. Deploy Updated Code
- [ ] Upload all files from this package
- [ ] Click "Manual Deploy" (or wait for auto-deploy if using Git)

### 3. Watch Deployment Logs
- [ ] Look for "RAG Service Initialization" section
- [ ] Should see "✅ RAG SERVICE READY"
- [ ] Note the Mode (should be "Cloud")

### 4. Test Diagnostics
- [ ] Visit: https://medlearn-ai-1-zej7.onrender.com/diagnostics
- [ ] Check `services.rag.status` = "connected"
- [ ] Check `services.rag.is_cloud` = true

### 5. Test Document Upload
- [ ] Visit: https://medlearn-ai-1-zej7.onrender.com
- [ ] Go to "Smart Authoring" tab
- [ ] Click "Upload from Computer"
- [ ] Select a small PDF file
- [ ] Should see upload progress
- [ ] Should see success message

## If Something Goes Wrong

### Connection Failed?
1. Check Weaviate Console - is cluster running?
2. Try regenerating API key
3. Update in Render
4. Deploy again

### Environment Variables Not Working?
1. Double-check no quotes around values
2. Click "Save Changes" after editing
3. **Trigger manual deploy after saving**

### Still Not Working?
1. Share the full error from deployment logs
2. Share the output from /diagnostics endpoint
3. Verify cluster URL matches exactly

## Success Indicators

You know it's working when you see ALL of these:

✅ Deployment logs show:
```
============================================================
✅ RAG SERVICE READY
   Mode: Cloud
============================================================
```

✅ /diagnostics endpoint shows:
```json
{
  "services": {
    "rag": {
      "status": "connected",
      "is_cloud": true,
      "has_embedding_model": true
    }
  }
}
```

✅ Can upload documents in the UI

✅ No errors in browser console (F12)

## Estimated Time
- Setting environment variables: 2 minutes
- Deployment: 3-5 minutes
- Testing: 2 minutes
- **Total: ~10 minutes**

## Notes
- Weaviate sandbox clusters may auto-sleep after inactivity
- If it was sleeping, it takes ~30 seconds to wake up
- First connection after wake-up might be slow
- Subsequent uploads should be fast
