#!/bin/bash
# Build the extension and create a ZIP for sideloading
set -e

cd "$(dirname "$0")"

echo "Building extension..."
npx webpack --mode production

echo "Fixing dist structure..."
cd dist

# Move sidepanel HTML to correct location
if [ -f src/sidepanel/index.html ]; then
  cp src/sidepanel/index.html sidepanel/index.html
  rm -rf src/
fi

# Remove python script from icons
rm -f icons/generate_icons.py

# Fix manifest paths (remove src/ prefix if present)
sed -i '' 's|src/background/service-worker.js|background/service-worker.js|g' manifest.json
sed -i '' 's|src/content/content-script.js|content/content-script.js|g' manifest.json
sed -i '' 's|src/sidepanel/index.html|sidepanel/index.html|g' manifest.json

echo "Creating ZIP..."
cd ..
rm -f cold-begging-extension.zip
cd dist
zip -r ../cold-begging-extension.zip . -x "*.DS_Store"
cd ..

echo "Done! Extension ready at: extension/dist/"
echo "ZIP: extension/cold-begging-extension.zip ($(du -h cold-begging-extension.zip | cut -f1))"

# Verify structure
echo ""
echo "Dist structure:"
find dist -type f | sort
