#!/usr/bin/env python3
"""
LinkedIn Recon — OSINT Employee & Org Intelligence via LinkedIn
Extracts employee names, titles, and tech stack signals via Google dork + public data.
Author: Omar Khalid (amooryx) | github.com/amooryx/linkedin-recon
AUTHORIZED USE ONLY — for authorized red team engagements and OSINT research.
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

# Google dorking URLs (no API key required)
GOOGLE_DORK = "https://www.google.com/search?q=site:linkedin.com+%22{company}%22+%22{title}%22&num=20"
BING_DORK   = "https://www.bing.com/search?q=site:linkedin.com/in+%22{company}%22&count=50"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

def dork_search(engine: str, company: str, title: str = "Engineer") -> list[dict]:
    if engine == "google":
        url = GOOGLE_DORK.format(
            company=urllib.parse.quote(company),
            title=urllib.parse.quote(title)
        )
    else:
        url = BING_DORK.format(company=urllib.parse.quote(company))

    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Accept-Language", "en-US,en;q=0.9")

    results = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read(65536).decode(errors="ignore")
            # Extract LinkedIn profile URLs
            profile_urls = re.findall(r"https?://(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-]+)", html)
            # Extract names from title snippets
            names = re.findall(r'<h3[^>]*>([^<]{5,80})</h3>', html)
            for slug in set(profile_urls[:20]):
                results.append({
                    "profile_url": f"https://www.linkedin.com/in/{slug}",
                    "slug": slug,
                })
            for name in names[:10]:
                name = re.sub(r"<[^>]+>", "", name).strip()
                if "linkedin" in name.lower() or len(name) < 5:
                    continue
                results.append({"name": name, "source": "google_snippet"})
    except Exception as e:
        results.append({"error": str(e)})
    return results

def guess_emails_from_names(names: list[str], domain: str) -> list[str]:
    """Generate email format guesses from a list of names."""
    emails = []
    for name in names:
        parts = name.strip().split()
        if len(parts) < 2:
            continue
        first, last = parts[0].lower(), parts[-1].lower()
        f = first[0]
        l = last[0]
        for fmt in [f"{first}.{last}", f"{f}{last}", f"{first}{l}", f"{first}_{last}"]:
            emails.append(f"{fmt}@{domain}")
    return list(set(emails))

def infer_tech_stack_signals(company: str) -> dict:
    """Look for tech job postings to infer tech stack (via Google)."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(company)}+jobs+engineer+%22AWS%20OR%20Azure%20OR%20GCP%20OR%20Kubernetes%22&num=10"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    signals = {"cloud": [], "languages": [], "frameworks": []}
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read(32768).decode(errors="ignore").lower()
            for kw in ["aws", "azure", "gcp", "kubernetes", "terraform", "ansible"]:
                if kw in html:
                    signals["cloud"].append(kw)
            for kw in ["python", "go", "java", "c#", "javascript", "typescript", "ruby", "rust"]:
                if kw in html:
                    signals["languages"].append(kw)
            for kw in ["react", "django", "spring", "rails", "laravel", "node.js", "angular"]:
                if kw in html:
                    signals["frameworks"].append(kw)
    except Exception:
        pass
    return signals

def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Recon — Employee OSINT (Authorized use only)",
    )
    parser.add_argument("company",     help="Target company name")
    parser.add_argument("--domain",    help="Email domain for format guesses (e.g., company.com)")
    parser.add_argument("--title",     default="Engineer", help="Job title to search")
    parser.add_argument("--engine",    choices=["google", "bing"], default="google")
    parser.add_argument("--tech",      action="store_true", help="Infer tech stack from job signals")
    parser.add_argument("--out",       help="Output JSON file")
    args = parser.parse_args()

    print(f"[*] LinkedIn OSINT for '{args.company}' via {args.engine}")
    results = {}

    profiles = dork_search(args.engine, args.company, args.title)
    print(f"[+] {len(profiles)} profiles/snippets found")
    for p in profiles[:10]:
        if "profile_url" in p:
            print(f"    {p['profile_url']}")
        elif "name" in p:
            print(f"    Name: {p['name']}")
    results["profiles"] = profiles

    if args.domain:
        names = [p["name"] for p in profiles if "name" in p]
        emails = guess_emails_from_names(names, args.domain)
        print(f"[+] Email format guesses: {len(emails)}")
        for e in emails[:10]:
            print(f"    {e}")
        results["email_guesses"] = emails

    if args.tech:
        print(f"[*] Inferring tech stack signals ...")
        tech = infer_tech_stack_signals(args.company)
        print(f"[+] Cloud: {tech['cloud']}  Languages: {tech['languages']}  Frameworks: {tech['frameworks']}")
        results["tech_stack_signals"] = tech

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[*] Results → {args.out}")

if __name__ == "__main__":
    main()
