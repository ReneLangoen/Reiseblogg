#!/usr/bin/env bash
set -euo pipefail

# Run local preview using the development config (no baseurl)
cd "$(dirname "$0")/.."

echo "Installing gems if needed..."
bundle install

echo "Starting Jekyll (dev config) with livereload..."
bundle exec jekyll serve --config _config.yml,_config_dev.yml --livereload
