#!/bin/bash
# Convert Markdown Presentation to PowerPoint
# Requires: pandoc (install via: brew install pandoc)

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "❌ Pandoc is not installed"
    echo "Install with: brew install pandoc"
    exit 1
fi

echo "🎯 Converting PRESENTATION.md to PowerPoint..."

# Convert markdown to PowerPoint
pandoc PRESENTATION.md \
    -o EM_Payment_Risk_Detection_POC.pptx \
    -t pptx \
    --slide-level=1

if [ $? -eq 0 ]; then
    echo "✅ PowerPoint created: EM_Payment_Risk_Detection_POC.pptx"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Open the generated .pptx file"
    echo "   2. Apply your company's PowerPoint template"
    echo "   3. Insert diagrams from ARCHITECTURE_DIAGRAMS.md"
    echo "      (Export diagrams at https://mermaid.live)"
    echo "   4. Adjust fonts, colors, and spacing as needed"
    echo "   5. Add your company logo to each slide"
    echo ""
    echo "💡 Tips:"
    echo "   - Diagrams 1, 2, 3, 6, 10 are most important"
    echo "   - Use Diagrams 4, 7 for technical appendix"
    echo "   - Diagram 9 (comparison) is great for executive summary"
else
    echo "❌ Conversion failed"
    exit 1
fi
