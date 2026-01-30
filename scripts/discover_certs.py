#!/usr/bin/env python3
"""
Discover new free certifications from known sources.
Searches various certification providers and aggregates results.
"""

import json
import asyncio
import aiohttp
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
from bs4 import BeautifulSoup
import hashlib

# Known certification sources to scrape
SOURCES = [
    {
        'name': 'Google Cloud Skills Boost',
        'url': 'https://www.cloudskillsboost.google/catalog?keywords=&locale=&format%5B%5D=courses&format%5B%5D=quests&free=true',
        'category': 'Cloud Computing',
        'provider': 'Google Cloud'
    },
    {
        'name': 'Microsoft Learn Certifications',
        'url': 'https://learn.microsoft.com/en-us/certifications/',
        'category': 'Cloud Computing',
        'provider': 'Microsoft'
    },
    {
        'name': 'AWS Training',
        'url': 'https://aws.amazon.com/training/digital/',
        'category': 'Cloud Computing',
        'provider': 'Amazon Web Services'
    },
    {
        'name': 'IBM Skills',
        'url': 'https://skills.yourlearning.ibm.com/',
        'category': 'Cloud Computing',
        'provider': 'IBM'
    },
    {
        'name': 'Oracle University',
        'url': 'https://education.oracle.com/learning-explorer',
        'category': 'Cloud Computing',
        'provider': 'Oracle'
    },
    {
        'name': 'Cisco Networking Academy',
        'url': 'https://www.netacad.com/courses/all-courses',
        'category': 'Cybersecurity & Information Security',
        'provider': 'Cisco'
    },
    {
        'name': 'Coursera Free Courses',
        'url': 'https://www.coursera.org/courses?query=free%20certificate',
        'category': 'Programming & Development',
        'provider': 'Coursera'
    },
    {
        'name': 'edX Free Courses',
        'url': 'https://www.edx.org/search?tab=course',
        'category': 'Programming & Development',
        'provider': 'edX'
    },
    {
        'name': 'LinkedIn Learning',
        'url': 'https://www.linkedin.com/learning/',
        'category': 'Programming & Development',
        'provider': 'LinkedIn Learning'
    },
    {
        'name': 'Cognitive Class',
        'url': 'https://cognitiveclass.ai/courses',
        'category': 'AI & Machine Learning Engineering',
        'provider': 'IBM'
    },
    {
        'name': 'Great Learning Academy',
        'url': 'https://www.mygreatlearning.com/academy',
        'category': 'Programming & Development',
        'provider': 'Great Learning'
    },
    {
        'name': 'Alison',
        'url': 'https://alison.com/courses',
        'category': 'Programming & Development',
        'provider': 'Alison'
    }
]

# Keywords to search for new certifications
SEARCH_KEYWORDS = [
    'free certification 2024',
    'free IT certification',
    'free cloud certification',
    'free cybersecurity certification',
    'free programming certificate',
    'free data science certification',
    'free AI certification',
    'free professional certificate'
]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def generate_cert_id(name: str, url: str) -> str:
    """Generate unique ID for a certification."""
    return hashlib.md5(f"{name}:{url}".encode()).hexdigest()[:12]

async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch a webpage and return its content."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return ""

async def search_duckduckgo(session: aiohttp.ClientSession, query: str) -> List[Dict]:
    """Search DuckDuckGo for certification-related content."""
    results = []
    # Note: This is a simplified search - in production, use an API
    search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"

    try:
        html = await fetch_page(session, search_url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            for result in soup.select('.result'):
                title_elem = result.select_one('.result__a')
                snippet_elem = result.select_one('.result__snippet')
                if title_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''
                    })
    except Exception as e:
        print(f"Search error: {e}")

    return results[:10]  # Limit results

def is_certification_url(url: str, title: str) -> bool:
    """Check if URL likely points to a certification."""
    cert_keywords = ['certif', 'course', 'training', 'learn', 'skill', 'badge', 'credential']
    title_lower = title.lower()
    url_lower = url.lower()

    return any(kw in title_lower or kw in url_lower for kw in cert_keywords)

def extract_certification_info(title: str, url: str, snippet: str) -> Dict:
    """Extract certification information from search result."""
    # Determine category based on keywords
    categories = {
        'cloud': 'Cloud Computing',
        'aws': 'Cloud Computing',
        'azure': 'Cloud Computing',
        'gcp': 'Cloud Computing',
        'google cloud': 'Cloud Computing',
        'security': 'Cybersecurity & Information Security',
        'cyber': 'Cybersecurity & Information Security',
        'data': 'Data Science & Analytics',
        'machine learning': 'AI & Machine Learning Engineering',
        'ai': 'AI & Machine Learning Engineering',
        'python': 'Programming & Development',
        'java': 'Programming & Development',
        'javascript': 'Programming & Development',
        'web': 'Programming & Development',
    }

    category = 'Programming & Development'  # Default
    for keyword, cat in categories.items():
        if keyword in title.lower() or keyword in snippet.lower():
            category = cat
            break

    # Determine provider from URL
    providers = {
        'coursera': 'Coursera',
        'edx': 'edX',
        'udemy': 'Udemy',
        'linkedin': 'LinkedIn Learning',
        'microsoft': 'Microsoft',
        'google': 'Google',
        'aws.amazon': 'Amazon Web Services',
        'ibm': 'IBM',
        'oracle': 'Oracle',
        'cisco': 'Cisco',
        'alison': 'Alison',
    }

    provider = 'Unknown'
    for domain, prov in providers.items():
        if domain in url.lower():
            provider = prov
            break

    return {
        'id': generate_cert_id(title, url),
        'name': title,
        'url': url,
        'description': snippet,
        'category': category,
        'provider': provider,
        'level': 'Not Specified',
        'duration': 'Self-paced',
        'prerequisites': '',
        'expiration': '',
        'discovered_at': datetime.utcnow().isoformat() + 'Z',
        'source': 'web_search'
    }

async def discover_new_certifications(existing_urls: Set[str]) -> List[Dict]:
    """Discover new certifications not in existing list."""
    discovered = []
    seen_urls = set()

    headers = {'User-Agent': USER_AGENT}

    async with aiohttp.ClientSession(headers=headers) as session:
        # Search for new certifications
        for keyword in SEARCH_KEYWORDS:
            print(f"Searching: {keyword}")
            results = await search_duckduckgo(session, keyword)

            for result in results:
                url = result['url']
                title = result['title']

                # Skip if already exists or already seen
                if url in existing_urls or url in seen_urls:
                    continue

                # Skip if doesn't look like a certification
                if not is_certification_url(url, title):
                    continue

                seen_urls.add(url)
                cert_info = extract_certification_info(title, url, result['snippet'])
                discovered.append(cert_info)

            # Rate limiting
            await asyncio.sleep(2)

    return discovered

def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)

    # Load existing certifications
    json_file = data_dir / 'certifications.json'
    existing_urls = set()

    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_urls = {cert['url'] for cert in data.get('certifications', [])}

    print(f"Existing certifications: {len(existing_urls)}")
    print("Searching for new certifications...")

    # Discover new certifications
    new_certs = asyncio.run(discover_new_certifications(existing_urls))

    print(f"\nDiscovered {len(new_certs)} potential new certifications")

    # Save discoveries
    discoveries_file = data_dir / 'discoveries.json'
    with open(discoveries_file, 'w', encoding='utf-8') as f:
        json.dump({
            'discovered_at': datetime.utcnow().isoformat() + 'Z',
            'count': len(new_certs),
            'certifications': new_certs
        }, f, indent=2)

    # Generate PR-ready markdown
    if new_certs:
        md_file = data_dir / 'NEW_DISCOVERIES.md'
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# New Certification Discoveries\n\n")
            f.write(f"**Discovered:** {datetime.utcnow().isoformat()}Z\n\n")
            f.write(f"Found **{len(new_certs)}** potential new certifications:\n\n")

            for cert in new_certs:
                f.write(f"### {cert['name']}\n")
                f.write(f"- **Provider:** {cert['provider']}\n")
                f.write(f"- **Category:** {cert['category']}\n")
                f.write(f"- **URL:** {cert['url']}\n")
                f.write(f"- **Description:** {cert['description'][:200]}...\n\n")

        print(f"Discoveries saved to {discoveries_file}")
        print(f"Markdown report saved to {md_file}")

if __name__ == '__main__':
    main()
