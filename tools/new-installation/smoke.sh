#!/usr/bin/env bash
set -euo pipefail
: "${API_URL:?Set API_URL to the public HTTPS API origin}"
: "${FRONTEND_URL:?Set FRONTEND_URL to the public HTTPS site origin}"
for path in /health /ready /services/; do
  curl --fail --silent --show-error --max-time 8 "${API_URL%/}${path}" --output /dev/null
done
curl --fail --silent --show-error --max-time 8 "${FRONTEND_URL%/}/pages/index.html" \
  | grep -q 'id="services-list"'
printf '%s\n' 'PASS: health, readiness, public service catalog and home page responded successfully.'
