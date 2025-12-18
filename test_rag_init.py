#!/usr/bin/env python3
"""
Test RAG Service Initialization
This simulates what happens in the cloud environment
"""
import os
import sys

# Simulate Render environment variables
os.environ["WEAVIATE_URL"] = "https://f7mb9hfbsf24gzezrpqtqa.c0.us-west3.gcp.weaviate.cloud"
os.environ["WEAVIATE_API_KEY"] = "b2tBeTJKVE5wMStXeERWRV9WQzZ5VytldmQzM2ZGUTdUTmVjRy93Rk9ldEkrV2JDL1ptZFFaUU1iOFowPV92MjAw"

print("=" * 60)
print("Testing RAG Service Initialization")
print("=" * 60)

try:
    from rag_service import RAGService
    
    print("\nInitializing RAG service...")
    rag = RAGService()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"Client connected: {rag.client is not None}")
    print(f"Is cloud mode: {rag.is_cloud}")
    print(f"Embedding model loaded: {rag.embedding_model is not None}")
    
    if rag.client:
        print("\n✅ SUCCESS - RAG service initialized successfully")
        print("   Documents can be uploaded and searched")
        
        # Test collection exists
        try:
            if rag.client.collections.exists("HospitalDocument"):
                print("   ✅ HospitalDocument collection ready")
        except Exception as e:
            print(f"   ⚠️  Collection check failed: {e}")
    else:
        print("\n❌ FAILED - RAG service not connected")
        print("   Check logs above for connection errors")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
