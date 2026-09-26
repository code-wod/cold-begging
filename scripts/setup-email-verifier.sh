#!/bin/bash
# Setup and run the email-verifier Go service
# This provides SMTP-level email verification

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMAIL_VERIFIER_DIR="$SCRIPT_DIR/../email-verifier"

echo "=== Email Verifier Service Setup ==="

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo "Error: Go is not installed."
    echo "Install from: https://go.dev/dl/"
    exit 1
fi

# Check if email-verifier is cloned
if [ ! -d "$EMAIL_VERIFIER_DIR" ]; then
    echo "Cloning email-verifier..."
    git clone https://github.com/AfterShip/email-verifier.git "$EMAIL_VERIFIER_DIR"
fi

# Build and run
cd "$EMAIL_VERIFIER_DIR"
echo "Building email-verifier API server..."
go build -o email-verifier-server ./cmd/apiserver

echo "Starting email-verifier API server on :8080..."
echo "Set EMAIL_VERIFIER_URL=http://localhost:8080 in backend/.env"
./email-verifier-server
