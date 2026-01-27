#!/bin/bash
# Quick script to send password reset email
# Usage: ./send_reset_now.sh user@example.com

cd "$(dirname "$0")/.."
python3 scripts/send_manual_password_reset.py "$@"
