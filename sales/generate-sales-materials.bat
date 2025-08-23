@echo off
REM CapSight Sales Materials Generator (Windows)
REM Automated PDF generation and packaging

echo 🚀 CapSight Sales Materials Generator
echo =====================================

REM Check if we're in the sales directory
if not exist "sales-deck.md" (
    echo ❌ Error: Run this script from the /sales directory
    echo Usage: cd sales ^& generate-sales-materials.bat
    exit /b 1
)

REM Install dependencies if needed
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    npm install
)

REM Generate PDF materials
echo.
echo 📄 Generating sales materials PDF...
npm run generate-simple

if %errorlevel% neq 0 (
    echo ❌ PDF generation failed
    exit /b 1
)

echo ✅ PDF generated successfully: sales-deck.pdf

REM Validate required files exist
echo.
echo 🔍 Validating sales materials...

set "all_files_exist=true"

for %%f in (sales-deck.pdf demo-script.md email-templates.md faq.md README.md quick-reference.md) do (
    if exist "%%f" (
        echo ✅ %%f
    ) else (
        echo ❌ Missing: %%f
        set "all_files_exist=false"
    )
)

if "%all_files_exist%"=="true" (
    echo.
    echo 🎉 All sales materials ready!
    echo.
    echo 📋 Next Steps:
    echo 1. Review generated sales-deck.pdf
    echo 2. Customize email templates for your prospects
    echo 3. Practice demo script with live platform
    echo 4. Use FAQ document for objection handling
    echo.
    echo 📞 Contact: sales@capsight.com
    echo 📅 Schedule demo: calendly.com/capsight-demo
) else (
    echo.
    echo ❌ Some sales materials are missing. Please check the setup.
    exit /b 1
)

pause
