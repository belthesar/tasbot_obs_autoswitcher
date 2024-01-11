#!/usr/bin/env bash
set -eof pipefail
NPX=$(which npx)
# if npx is not installed, throw an error and exit
if [ -z "$NPX" ]; then
  echo "npx is not installed. Please install npx and try again."
  exit 1
fi
# if npx is installed, start the mock tracker
npx http-server 