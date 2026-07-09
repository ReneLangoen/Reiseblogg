#!/usr/bin/env bash
set -euo pipefail

# Build site locally using development config (no baseurl)
cd "$(dirname "$0")/.."

echo "Installing gems if needed..."
bundle install

echo "Building site to _site/ (dev config)..."
bundle exec jekyll build --config _config.yml,_config_dev.yml

echo "Built to _site/"
