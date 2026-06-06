#!/bin/bash
# airunner-generate-cert: Generate a self-signed SSL certificate for local HTTPS
set -e
CERT_FILE="cert.pem"
KEY_FILE="key.pem"

# Try mkcert first for a trusted local CA, fall back to OpenSSL if not available
if command -v mkcert >/dev/null 2>&1; then
  echo "Using mkcert to generate a trusted certificate for localhost..."
  mkcert -install
  mkcert -cert-file cert.pem -key-file key.pem localhost 127.0.0.1 ::1
  echo "Trusted certificate generated with mkcert: cert.pem, key.pem"
else
  echo "mkcert not found, falling back to OpenSSL self-signed certificate."
  openssl req -x509 -newkey rsa:4096 -keyout "key.pem" -out "cert.pem" -days 365 -nodes -subj "/CN=localhost"
  echo "Self-signed certificate generated: cert.pem, key.pem"
  echo "For a trusted certificate (no browser warnings), install mkcert: https://github.com/FiloSottile/mkcert"
fi

echo "You can now use these files with the local HTTP server (see README for details)."
