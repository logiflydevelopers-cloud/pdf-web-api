#!/usr/bin/env bash
set -e

apt-get update
apt-get install -y \
  tesseract-ocr \
  poppler-utils

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*
