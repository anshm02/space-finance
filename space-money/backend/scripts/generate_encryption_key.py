#!/usr/bin/env python3
"""
Generate encryption key for DIFC compliance.

This script generates a Fernet (AES-256) encryption key
for field-level encryption of PII data.

Usage:
    python generate_encryption_key.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key()
    print("=" * 60)
    print("Encryption Key Generated (AES-256)")
    print("=" * 60)
    print()
    print("ENCRYPTION_KEY=" + key.decode())
    print()
    print("=" * 60)
    print("IMPORTANT:")
    print("1. Add this to your .env file")
    print("2. Keep this key secure - do NOT commit to version control")
    print("3. Store backup in secure location (AWS Secrets Manager)")
    print("4. If key is lost, encrypted data cannot be recovered")
    print("=" * 60)
