# Copyright (c) 2026 Ishan Chakraborty
# SPDX-License-Identifier: MIT
"""LinkedIn integration using only sanctioned, open-source-friendly methods.

1. "Sign In with LinkedIn using OpenID Connect" (official OAuth 2.0) -> name, email, photo.
2. Import of the user's own LinkedIn data export (Settings > Data privacy >
   Get a copy of your data) -> headline, summary, positions, education,
   skills, certifications, projects.

LinkedIn does not offer an open API for reading full profiles, and scraping a
profile URL violates its Terms of Service, so that is intentionally not done.

Author: Ishan Chakraborty
License: MIT
"""
import csv
import io
import os
import re
import urllib.parse
import zipfile

import requests

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPE = "openid profile email"
MAX_ZIP_BYTES = 20 * 1024 * 1024


def is_configured():
    return bool(os.environ.get("LINKEDIN_CLIENT_ID") and os.environ.get("LINKEDIN_CLIENT_SECRET"))


def redirect_uri():
    return os.environ.get("LINKEDIN_REDIRECT_URI", "http://127.0.0.1:5000/auth/linkedin/callback")


def authorization_url(state):
    params = {
        "response_type": "code",
        "client_id": os.environ["LINKEDIN_CLIENT_ID"],
        "redirect_uri": redirect_uri(),
        "state": state,
        "scope": SCOPE,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def fetch_profile(code):
    """Exchange an OAuth code for the member's OpenID profile."""
    tok = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(),
            "client_id": os.environ["LINKEDIN_CLIENT_ID"],
            "client_secret": os.environ["LINKEDIN_CLIENT_SECRET"],
        },
        timeout=15,
    )
    tok.raise_for_status()
    access = tok.json()["access_token"]
    info = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access}"}, timeout=15)
    info.raise_for_status()
    d = info.json()
    return {
        "name": d.get("name") or " ".join(x for x in (d.get("given_name"), d.get("family_name")) if x),
        "email": d.get("email", ""),
        "photo_url": d.get("picture", ""),
    }


def fetch_photo(url):
    """Download a LinkedIn profile picture (host-restricted to avoid SSRF)."""
    p = urllib.parse.urlparse(url or "")
    if p.scheme != "https" or not (p.hostname or "").endswith(".licdn.com"):
        return None
    try:
        r = requests.get(url, timeout=10)
        if r.ok and len(r.content) <= 5 * 1024 * 1024:
            return r.content
    except requests.RequestException:
        pass
    return None


# ---------------------------------------------------------------- export import
def _rows(zf, filename):
    """Yield dict rows from a CSV in the export (case-insensitive name match)."""
    match = next((n for n in zf.namelist() if n.lower().split("/")[-1] == filename.lower()), None)
    if not match:
        return []
    text = zf.read(match).decode("utf-8-sig", errors="replace")
    lines = list(csv.reader(io.StringIO(text)))
    # Some exports prepend a "Notes" preamble; header = first row with 2+ cells.
    for i, row in enumerate(lines):
        if len(row) >= 2:
            header = [h.strip() for h in row]
            return [dict(zip(header, r)) for r in lines[i + 1:] if any(c.strip() for c in r)]
    # single-column file (e.g. Skills.csv)
    if lines:
        header = [h.strip() for h in lines[0]]
        return [dict(zip(header, r)) for r in lines[1:] if any(c.strip() for c in r)]
    return []


def _g(row, key):
    return (row.get(key) or "").strip()


def _dates(row):
    start, end = _g(row, "Started On"), _g(row, "Finished On")
    if not start and not end:
        return ""
    return f"{start} – {end or 'Present'}"


def parse_export(data):
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("File too large.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Please upload the .zip file downloaded from LinkedIn.")

    out = {}
    prof = next(iter(_rows(zf, "Profile.csv")), {})
    out["name"] = " ".join(x for x in (_g(prof, "First Name"), _g(prof, "Last Name")) if x)
    out["title"] = _g(prof, "Headline")
    out["summary"] = _g(prof, "Summary")
    out["location"] = _g(prof, "Geo Location")
    sites = _g(prof, "Websites")
    m = re.search(r"https?://[^\s,\]\)]+", sites)
    if m:
        out["website"] = m.group(0)

    emails = _rows(zf, "Email Addresses.csv")
    primary = next((e for e in emails if _g(e, "Primary").lower() == "yes"), emails[0] if emails else None)
    if primary:
        out["email"] = _g(primary, "Email Address")

    out["experience"] = [
        {
            "title": _g(r, "Title"),
            "company": _g(r, "Company Name"),
            "location": _g(r, "Location"),
            "dates": _dates(r),
            "duties": [l.strip(" -•\t") for l in _g(r, "Description").splitlines() if l.strip(" -•\t")],
        }
        for r in _rows(zf, "Positions.csv")
    ]
    out["education"] = [
        {
            "degree": _g(r, "Degree Name"),
            "school": _g(r, "School Name"),
            "year": " – ".join(x for x in (_g(r, "Start Date"), _g(r, "End Date")) if x),
            "details": _g(r, "Notes"),
        }
        for r in _rows(zf, "Education.csv")
    ]
    skills = [_g(r, "Name") for r in _rows(zf, "Skills.csv") if _g(r, "Name")]
    out["skills"] = [{"category": "Skills", "items": ", ".join(skills)}] if skills else []
    out["certifications"] = [
        {"name": _g(r, "Name"), "issuer": _g(r, "Authority")} for r in _rows(zf, "Certifications.csv")
    ]
    out["projects"] = [
        {"title": _g(r, "Title"), "description": _g(r, "Description"), "url": _g(r, "Url"), "live_url": ""}
        for r in _rows(zf, "Projects.csv")
    ]
    return out


# ------------------------------------------------------------ profile PDF import
_HEADINGS = {
    "contact", "top skills", "skills", "languages", "certifications", "honors-awards",
    "publications", "patents", "summary", "experience", "education", "projects",
    "volunteer experience", "courses", "organizations", "test scores",
}
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}"
_DATE_RE = re.compile(rf"^({_MONTH})\s*[-–]\s*({_MONTH}|Present)", re.I)
_YEARS_RE = re.compile(r"\((\d{4})?\s*[-–]\s*(\d{4})?\)")


def _pdf_lines(data):
    from pypdf import PdfReader  # imported lazily so the zip import works without it

    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        raise ValueError("Could not read that PDF.")
    lines = [l.strip() for l in text.splitlines()]
    return [l for l in lines if l and not re.match(r"^Page \d+ of \d+$", l)]


def parse_profile_pdf(data):
    """Best-effort parser for LinkedIn's 'Save to PDF' profile. Users should review the result."""
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("File too large.")
    lines = _pdf_lines(data)

    sections, current, order = {"_pre": []}, "_pre", []
    for l in lines:
        if l.lower() in _HEADINGS:
            current = l.lower()
            sections.setdefault(current, [])
            order.append(current)
        else:
            sections[current].append(l)
    if not order:
        raise ValueError("This doesn't look like a LinkedIn profile PDF.")

    out = {}
    contact = " ".join(sections.get("contact", []))
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", contact)
    if m:
        out["email"] = m.group(0)
    m = re.search(r"(?:https?://)?(?:[a-z]+\.)?linkedin\.com/in/[\w%-]+", contact.replace(" ", ""))
    if m:
        out["linkedin"] = "https://" + re.sub(r"^https?://", "", m.group(0))

    # Name / headline / location are the last 3 lines before the first main-column heading.
    main_first = next((h for h in order if h in ("summary", "experience", "education")), None)
    if main_first:
        idx = order.index(main_first)
        prev = sections[order[idx - 1]] if idx > 0 else sections["_pre"]
        if len(prev) >= 3:
            out["name"], out["title"], out["location"] = prev[-3], prev[-2], prev[-1]
            if idx > 0:
                sections[order[idx - 1]] = prev[:-3]

    out["summary"] = " ".join(sections.get("summary", []))
    skills = sections.get("top skills", []) + sections.get("skills", [])
    out["skills"] = [{"category": "Skills", "items": ", ".join(skills)}] if skills else []
    out["certifications"] = [{"name": c, "issuer": ""} for c in sections.get("certifications", [])]

    # Experience: each date-range line marks a role; title is the line above, company above that.
    ex = sections.get("experience", [])
    marks = [i for i, l in enumerate(ex) if _DATE_RE.match(l)]
    exp = []
    for n, i in enumerate(marks):
        nxt = marks[n + 1] if n + 1 < len(marks) else len(ex) + 2
        body = ex[i + 1: max(i + 1, nxt - 2)]
        location = ""
        if body and len(body[0]) < 60 and not body[0].endswith("."):
            location, body = body[0], body[1:]
        dm = _DATE_RE.match(ex[i])
        exp.append({
            "title": ex[i - 1] if i >= 1 else "",
            "company": ex[i - 2] if i >= 2 else "",
            "dates": f"{dm.group(1)} – {dm.group(2)}",
            "location": location,
            "duties": body,
        })
    out["experience"] = exp

    # Education: a line containing "(YYYY - YYYY)"; the line above is the school.
    ed = sections.get("education", [])
    edu = []
    for i, l in enumerate(ed):
        ym = _YEARS_RE.search(l)
        if ym:
            degree = _YEARS_RE.sub("", l).strip(" ·,")
            edu.append({
                "degree": degree,
                "school": ed[i - 1] if i else "",
                "year": " – ".join(x for x in ym.groups() if x),
                "details": "",
            })
    out["education"] = edu
    out["projects"] = []
    return out


def parse_upload(filename, data):
    """Dispatch on file type: LinkedIn data-export .zip or profile .pdf."""
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return parse_profile_pdf(data)
    return parse_export(data)
