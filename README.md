# Dynamic Resume Builder

A Windows desktop app (Flask + pywebview, packaged with PyInstaller) that turns a form (with optional photo) into a styled, downloadable `.docx` resume.

## Project Structure

```
Dynamic-Resume-Builder/
├── app.py                  # Flask entry point
├── resume_builder/         # Resume generation package
│   ├── __init__.py
│   └── builder.py          # DOCX generation logic
├── templates/
│   └── index.html          # Web form UI
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

## Getting Started (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py        # run the desktop app from source
.\build.ps1            # build dist\DynamicResumeBuilder.exe
```

Requires Windows 10/11 with the WebView2 runtime (preinstalled on modern Windows).

## CI/CD

.github/workflows/build-exe.yml builds the EXE on every push and PR and uploads it as an artifact. Pushing a tag like `v1.0.0` also attaches it to a GitHub Release.

## Author

**Ishan Chakraborty**

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

