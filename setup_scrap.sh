#!/bin/bash

# Exit on error
set -e

echo "📁 Creating folders..."
mkdir -p .github/workflows

echo "📝 Creating files..."

# GitHub Actions Workflow
cat > .github/workflows/scrape-bachelor-programs.yml << 'EOF'
name: Scrape Bachelor Programs

on:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2 AM UTC
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run scraper
        run: python bachelor_portal_scraper.py

      - name: Run data processor
        run: python bachelor_data_processor.py

      - name: Upload to Supabase
        run: python upload_to_supabase.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
EOF

# Python placeholders
touch bachelor_portal_scraper.py
touch bachelor_data_processor.py
touch upload_to_supabase.py

# requirements.txt
cat > requirements.txt << EOF
requests
beautifulsoup4
pandas
numpy
supabase
EOF

echo "✅ Setup complete. Files created:"
echo "  - .github/workflows/scrape-bachelor-programs.yml"
echo "  - bachelor_portal_scraper.py"
echo "  - bachelor_data_processor.py"
echo "  - upload_to_supabase.py"
echo "  - requirements.txt"