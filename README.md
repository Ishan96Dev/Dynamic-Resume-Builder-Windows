# Dynamic Resume Builder (Windows)

A Windows desktop app (Flask + pywebview, packaged with PyInstaller) that turns a form (with optional photo) into a styled, downloadable `.docx` resume. It can prefill the form from LinkedIn.

## Project Structure

```
Dynamic-Resume-Builder-Windows/
├── main.py                 # Desktop launcher (entry point)
├── app.py                  # Flask backend
├── build.ps1               # PyInstaller build script
├── .github/workflows/      # CI: build EXE
├── resume_builder/
│   ├── builder.py          # DOCX generation logic
│   └── linkedin.py         # LinkedIn OAuth + PDF/data-export import
├── templates/index.html    # Form UI
├── requirements.txt
├── requirements-build.txt
├── LICENSE
└── README.md
```

## Getting Started (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py        # run the desktop app from source
.\build.ps1           # build dist\DynamicResumeBuilder.exe
```

Requires Windows 10/11 with the WebView2 runtime (preinstalled on modern Windows).

## LinkedIn Import

LinkedIn has no open API for reading a full profile from its URL, and scraping violates its Terms of Service, so the app uses supported routes:

1. **Profile PDF (quickest, no setup).** On your LinkedIn profile click *More → Save to PDF*, then upload the `.pdf` in the form. Review the pattern-matched fields before generating.
2. **Data export (most complete).** *Settings → Data privacy → Get a copy of your data*, then upload the emailed `.zip` (no need to unzip).
3. **Connect with LinkedIn (optional, official OAuth).** Fills name, email and photo. Create an app at <https://www.linkedin.com/developers/apps>, add *Sign In with LinkedIn using OpenID Connect*, and add `http://127.0.0.1:5000/auth/linkedin/callback` as a redirect URL. The desktop app uses port 5000 when free; otherwise it picks another port and sets the redirect URL to match (set `LINKEDIN_REDIRECT_URI` to override). Then set these once and restart the app:

```powershell
setx LINKEDIN_CLIENT_ID "your-id"
setx LINKEDIN_CLIENT_SECRET "your-secret"
```

The *Connect* button only appears when both variables are set. The profile URL field is simply added to your resume.

## CI/CD

`.github/workflows/build-exe.yml` builds the EXE on every push and PR and uploads it as an artifact. Pushing a tag like `v1.0.0` also attaches it to a GitHub Release.

## Author

**Ishan Chakraborty**

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
