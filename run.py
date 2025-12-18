#!/usr/bin/env python3
"""MedLearn AI - Cloud Startup Script"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 MedLearn AI starting on port {port}")
    uvicorn.run("start:app", host="0.0.0.0", port=port, log_level="info")
