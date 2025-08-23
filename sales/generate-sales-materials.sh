#!/bin/bash

# CapSight Sales Materials Generator
# Automated PDF generation and packaging

echo "🚀 CapSight Sales Materials Generator"
echo "====================================="

# Check if we're in the sales directory
if [[ ! -f "sales-deck.md" ]]; then
    echo "❌ Error: Run this script from the /sales directory"
    echo "Usage: cd sales && ./generate-sales-materials.sh"
    exit 1
fi

# Install dependencies if needed
if [[ ! -d "node_modules" ]]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Generate PDF materials
echo ""
echo "📄 Generating sales materials PDF..."
npm run generate-simple

if [[ $? -eq 0 ]]; then
    echo "✅ PDF generated successfully: sales-deck.pdf"
else
    echo "❌ PDF generation failed"
    exit 1
fi

# Validate required files exist
echo ""
echo "🔍 Validating sales materials..."

required_files=(
    "sales-deck.pdf"
    "demo-script.md"
    "email-templates.md"
    "faq.md"
    "README.md"
    "quick-reference.md"
)

all_files_exist=true

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ Missing: $file"
        all_files_exist=false
    fi
done

if [[ "$all_files_exist" == true ]]; then
    echo ""
    echo "🎉 All sales materials ready!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Review generated sales-deck.pdf"
    echo "2. Customize email templates for your prospects"
    echo "3. Practice demo script with live platform"
    echo "4. Use FAQ document for objection handling"
    echo ""
    echo "📞 Contact: sales@capsight.com"
    echo "📅 Schedule demo: calendly.com/capsight-demo"
else
    echo ""
    echo "❌ Some sales materials are missing. Please check the setup."
    exit 1
fi
