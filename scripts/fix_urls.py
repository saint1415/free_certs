#!/usr/bin/env python3
"""
Fix broken certification URLs by searching for updated links.
"""

import json
import csv
import re
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urlparse, quote_plus

# URL pattern fixes for known domain changes
URL_FIXES = {
    # Coursera often changes course URLs
    'www.coursera.org': {
        'pattern': r'/learn/([^/]+)',
        'search_template': 'site:coursera.org {name}'
    },
    # edX course URL patterns
    'www.edx.org': {
        'pattern': r'/course/([^/]+)',
        'search_template': 'site:edx.org {name}'
    },
    # Microsoft Learn paths change
    'learn.microsoft.com': {
        'pattern': r'/training/([^/]+)',
        'search_template': 'site:learn.microsoft.com {name}'
    }
}

# Known URL replacements (manual fixes for common patterns)
KNOWN_REPLACEMENTS = {
    # Coursera URL structure changes
    'https://www.coursera.org/learn/project-management-basics': 'https://www.coursera.org/learn/project-management',
    'https://www.coursera.org/learn/ethics-modern-world': 'https://www.coursera.org/learn/ethics',
    # edX changes
    'https://www.edx.org/course/introduction-to-computer-science': 'https://www.edx.org/learn/computer-science',
}

async def check_url(session, url):
    """Check if a URL is valid."""
    try:
        async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return resp.status < 400
    except:
        return False

async def search_new_url(session, name, provider, old_url):
    """Try to find a new URL for a certification."""
    domain = urlparse(old_url).netloc

    # Check known replacements first
    if old_url in KNOWN_REPLACEMENTS:
        new_url = KNOWN_REPLACEMENTS[old_url]
        if await check_url(session, new_url):
            return new_url

    # Try common URL variations
    variations = []

    if 'coursera.org' in domain:
        # Try different Coursera URL patterns
        slug = name.lower().replace(' ', '-').replace(':', '').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        variations = [
            f'https://www.coursera.org/learn/{slug}',
            f'https://www.coursera.org/specializations/{slug}',
            f'https://www.coursera.org/professional-certificates/{slug}',
        ]
    elif 'edx.org' in domain:
        slug = name.lower().replace(' ', '-').replace(':', '').replace('(', '').replace(')', '')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        variations = [
            f'https://www.edx.org/learn/{slug}',
            f'https://www.edx.org/course/{slug}',
        ]
    elif 'futurelearn.com' in domain:
        slug = name.lower().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        variations = [
            f'https://www.futurelearn.com/courses/{slug}',
        ]
    elif 'learn.microsoft.com' in domain:
        slug = name.lower().replace(' ', '-')
        variations = [
            f'https://learn.microsoft.com/en-us/training/paths/{slug}',
            f'https://learn.microsoft.com/en-us/training/modules/{slug}',
        ]

    for new_url in variations:
        if await check_url(session, new_url):
            return new_url

    return None

async def fix_broken_urls():
    """Main function to fix broken URLs."""
    project_root = Path(__file__).parent.parent

    # Load validation report
    report_file = project_root / 'data' / 'validation_report.json'
    with open(report_file) as f:
        report = json.load(f)

    invalid_urls = {item['url']: item['name'] for item in report['invalid_urls']}

    # Load current CSV
    csv_file = project_root / 'free_certifications.csv'
    rows = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Checking {len(invalid_urls)} broken URLs...")

    fixes = {}
    removals = []

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    connector = aiohttp.TCPConnector(limit=10)

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        for i, row in enumerate(rows):
            url = row.get('URL', '')
            if url not in invalid_urls:
                continue

            name = row.get('Certification_Name', '')
            provider = row.get('Provider', '')

            # Try to find new URL
            new_url = await search_new_url(session, name, provider, url)

            if new_url:
                fixes[url] = new_url
                print(f"[FIXED] {name[:50]}")
                print(f"        {url[:60]} -> {new_url[:60]}")
            else:
                removals.append(url)
                print(f"[REMOVE] {name[:50]} - No replacement found")

            # Rate limiting
            if i % 10 == 0:
                await asyncio.sleep(0.5)

    print(f"\n--- Summary ---")
    print(f"Fixed: {len(fixes)}")
    print(f"To remove: {len(removals)}")

    # Apply fixes to rows
    updated_rows = []
    for row in rows:
        url = row.get('URL', '')
        if url in fixes:
            row['URL'] = fixes[url]
            updated_rows.append(row)
        elif url in removals:
            # Skip removed entries
            continue
        else:
            updated_rows.append(row)

    # Write updated CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"\nUpdated CSV: {len(updated_rows)} certifications (removed {len(rows) - len(updated_rows)})")

    # Save fix report
    fix_report = {
        'fixes': fixes,
        'removals': removals,
        'summary': {
            'fixed': len(fixes),
            'removed': len(removals),
            'remaining': len(updated_rows)
        }
    }

    with open(project_root / 'data' / 'url_fixes.json', 'w') as f:
        json.dump(fix_report, f, indent=2)

if __name__ == '__main__':
    asyncio.run(fix_broken_urls())
