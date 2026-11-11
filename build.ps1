$ErrorActionPreference = "Stop"
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE) { exit $LASTEXITCODE }
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name DynamicResumeBuilder `
    --add-data "templates;templates" `
    main.py
if ($LASTEXITCODE) { exit $LASTEXITCODE }
Write-Host "Built: dist\DynamicResumeBuilder.exe"
