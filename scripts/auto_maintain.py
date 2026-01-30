#!/usr/bin/env python3
"""
Fully automated certification maintenance system.
- Discovers new free certifications from multiple sources
- Validates all URLs
- Automatically adds new valid certs
- Automatically removes invalid certs
- Runs without human intervention
"""

import asyncio
import aiohttp
import csv
import json
import re
import ssl
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urlparse, urljoin, quote_plus
from bs4 import BeautifulSoup

# Configuration
MAX_CONCURRENT = 15
TIMEOUT = 20
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Known free certification sources to scrape
CERTIFICATION_SOURCES = [
    # Cloud Providers
    {
        'name': 'Google Cloud Skills Boost',
        'url': 'https://www.cloudskillsboost.google/catalog?format[]=courses&free=true',
        'category': 'Cloud Computing',
        'provider': 'Google Cloud',
        'selectors': {'links': 'a[href*="/course_templates/"]', 'title': 'h3, .title'}
    },
    {
        'name': 'AWS Skill Builder Free',
        'url': 'https://explore.skillbuilder.aws/learn/catalog?ctldoc-catalog-0=se-%22Free%22',
        'category': 'Cloud Computing',
        'provider': 'Amazon Web Services',
        'selectors': {'links': 'a[href*="/learn/course/"]'}
    },
    {
        'name': 'Microsoft Learn',
        'url': 'https://learn.microsoft.com/en-us/credentials/browse/?credential_types=certification',
        'category': 'Cloud Computing',
        'provider': 'Microsoft',
        'selectors': {'links': 'a[href*="/credentials/certifications/"]'}
    },
    {
        'name': 'IBM Skills',
        'url': 'https://www.ibm.com/training/badges',
        'category': 'Cloud Computing',
        'provider': 'IBM',
        'selectors': {'links': 'a[href*="credly.com"], a[href*="youracclaim.com"]'}
    },
    {
        'name': 'Oracle University Free',
        'url': 'https://education.oracle.com/learning-explorer',
        'category': 'Cloud Computing',
        'provider': 'Oracle',
        'selectors': {'links': 'a[href*="oracle.com"]'}
    },
    # Learning Platforms
    {
        'name': 'Coursera Free Certificates',
        'url': 'https://www.coursera.org/courses?query=free%20certificate&productTypeDescription=Free%20Courses',
        'category': 'Programming & Development',
        'provider': 'Coursera',
        'selectors': {'links': 'a[href*="/learn/"]'}
    },
    {
        'name': 'edX Free Courses',
        'url': 'https://www.edx.org/search?tab=course&price=Free',
        'category': 'Programming & Development',
        'provider': 'edX',
        'selectors': {'links': 'a[href*="/course/"], a[href*="/learn/"]'}
    },
    {
        'name': 'FreeCodeCamp',
        'url': 'https://www.freecodecamp.org/learn',
        'category': 'Programming & Development',
        'provider': 'freeCodeCamp',
        'selectors': {'links': 'a[href*="/learn/"]'}
    },
    {
        'name': 'Cognitive Class',
        'url': 'https://cognitiveclass.ai/courses',
        'category': 'AI & Machine Learning Engineering',
        'provider': 'IBM',
        'selectors': {'links': 'a[href*="/courses/"]'}
    },
    {
        'name': 'Great Learning Free Courses',
        'url': 'https://www.mygreatlearning.com/academy/courses',
        'category': 'Programming & Development',
        'provider': 'Great Learning',
        'selectors': {'links': 'a[href*="/academy/"]'}
    },
    # Security
    {
        'name': 'Cisco Networking Academy',
        'url': 'https://www.netacad.com/courses/all-courses',
        'category': 'Cybersecurity & Information Security',
        'provider': 'Cisco',
        'selectors': {'links': 'a[href*="/courses/"]'}
    },
    {
        'name': 'Fortinet Training',
        'url': 'https://training.fortinet.com/local/psc/',
        'category': 'Cybersecurity & Information Security',
        'provider': 'Fortinet',
        'selectors': {'links': 'a[href*="training.fortinet.com"]'}
    },
    # Others
    {
        'name': 'HubSpot Academy',
        'url': 'https://academy.hubspot.com/courses',
        'category': 'Digital Marketing & Social Media',
        'provider': 'HubSpot',
        'selectors': {'links': 'a[href*="/courses/"]'}
    },
    {
        'name': 'Google Digital Garage',
        'url': 'https://learndigital.withgoogle.com/digitalgarage/courses',
        'category': 'Digital Marketing & Social Media',
        'provider': 'Google',
        'selectors': {'links': 'a[href*="/course/"]'}
    },
    {
        'name': 'Salesforce Trailhead',
        'url': 'https://trailhead.salesforce.com/credentials/certifications',
        'category': 'Cloud Computing',
        'provider': 'Salesforce',
        'selectors': {'links': 'a[href*="trailhead.salesforce.com"]'}
    },
]

# Search queries for discovering new certifications
SEARCH_QUERIES = [
    'free IT certification 2024 2025',
    'free cloud certification AWS Azure GCP',
    'free cybersecurity certification',
    'free programming certificate online',
    'free data science certification',
    'free AI machine learning certificate',
    'free professional certification no cost',
    'free certification with badge credential',
    'vendor free certification program',
    'free tech certification exam',
]

# Keywords that indicate a certification is free
FREE_INDICATORS = [
    'free', 'no cost', 'complimentary', '$0', 'at no charge',
    'free certification', 'free course', 'free training',
    'free badge', 'free credential', 'free exam'
]

# Keywords that indicate NOT free
PAID_INDICATORS = [
    'paid', 'purchase', 'buy now', 'enroll for $', 'pricing',
    'subscription required', 'premium', 'pro plan'
]


class CertificationDiscovery:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.existing_urls: Set[str] = set()
        self.existing_names: Set[str] = set()
        self.discovered: List[Dict] = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def setup(self):
        """Initialize session and load existing data."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=MAX_CONCURRENT)
        headers = {'User-Agent': USER_AGENT}
        self.session = aiohttp.ClientSession(connector=connector, headers=headers)

        # Load existing certifications
        json_file = self.project_root / 'data' / 'certifications.json'
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
                for cert in data.get('certifications', []):
                    self.existing_urls.add(cert['url'].lower().rstrip('/'))
                    self.existing_names.add(cert['name'].lower())

    async def cleanup(self):
        """Close session."""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> str:
        """Fetch a webpage."""
        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                allow_redirects=True
            ) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
        return ""

    async def check_url_valid(self, url: str) -> bool:
        """Check if URL is accessible."""
        try:
            async with self.session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                allow_redirects=True
            ) as response:
                if response.status < 400:
                    return True
            # Fallback to GET
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                allow_redirects=True
            ) as response:
                return response.status < 400
        except:
            return False

    def is_duplicate(self, url: str, name: str) -> bool:
        """Check if certification already exists."""
        url_normalized = url.lower().rstrip('/')
        name_normalized = name.lower()

        if url_normalized in self.existing_urls:
            return True
        if name_normalized in self.existing_names:
            return True
        return False

    def extract_cert_info(self, url: str, title: str, source: Dict) -> Optional[Dict]:
        """Extract certification info from discovered link."""
        if not url or not title:
            return None

        # Clean title
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) < 5 or len(title) > 200:
            return None

        # Skip if duplicate
        if self.is_duplicate(url, title):
            return None

        # Determine category from source or content
        category = source.get('category', 'Programming & Development')
        provider = source.get('provider', self.extract_provider(url))

        return {
            'category': category,
            'name': title,
            'provider': provider,
            'url': url,
            'description': f'Free certification from {provider}',
            'duration': 'Self-paced',
            'level': 'Beginner',
            'prerequisites': '',
            'expiration': '',
            'discovered_at': datetime.now(timezone.utc).isoformat()
        }

    def extract_provider(self, url: str) -> str:
        """Extract provider name from URL."""
        domain = urlparse(url).netloc.lower()

        providers = {
            'coursera.org': 'Coursera',
            'edx.org': 'edX',
            'udemy.com': 'Udemy',
            'linkedin.com': 'LinkedIn Learning',
            'microsoft.com': 'Microsoft',
            'google.com': 'Google',
            'aws.amazon.com': 'Amazon Web Services',
            'cloud.google.com': 'Google Cloud',
            'ibm.com': 'IBM',
            'oracle.com': 'Oracle',
            'cisco.com': 'Cisco',
            'salesforce.com': 'Salesforce',
            'hubspot.com': 'HubSpot',
            'freecodecamp.org': 'freeCodeCamp',
            'codecademy.com': 'Codecademy',
            'futurelearn.com': 'FutureLearn',
        }

        for key, value in providers.items():
            if key in domain:
                return value

        # Extract from domain
        parts = domain.replace('www.', '').split('.')
        if parts:
            return parts[0].title()
        return 'Unknown'

    async def scrape_source(self, source: Dict) -> List[Dict]:
        """Scrape a certification source."""
        print(f"  Scraping: {source['name']}")
        discovered = []

        html = await self.fetch_page(source['url'])
        if not html:
            return discovered

        soup = BeautifulSoup(html, 'html.parser')
        selectors = source.get('selectors', {})

        # Find certification links
        links = []
        if 'links' in selectors:
            links = soup.select(selectors['links'])
        else:
            # Default: find all links
            links = soup.find_all('a', href=True)

        for link in links[:50]:  # Limit per source
            href = link.get('href', '')
            if not href:
                continue

            # Make absolute URL
            if href.startswith('/'):
                base = f"{urlparse(source['url']).scheme}://{urlparse(source['url']).netloc}"
                href = urljoin(base, href)
            elif not href.startswith('http'):
                continue

            # Get title
            title = link.get_text(strip=True)
            if not title:
                title = link.get('title', '') or link.get('aria-label', '')

            cert = self.extract_cert_info(href, title, source)
            if cert:
                discovered.append(cert)

        return discovered

    async def search_web(self, query: str) -> List[Dict]:
        """Search web for certifications."""
        discovered = []

        # Use DuckDuckGo HTML search
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        try:
            html = await self.fetch_page(search_url)
            if not html:
                return discovered

            soup = BeautifulSoup(html, 'html.parser')

            for result in soup.select('.result')[:10]:
                title_elem = result.select_one('.result__a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')

                # Extract actual URL from DuckDuckGo redirect
                if 'uddg=' in href:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    href = parsed.get('uddg', [''])[0]

                if not href or not href.startswith('http'):
                    continue

                # Check if it looks like a certification
                cert_keywords = ['certif', 'course', 'training', 'learn', 'badge', 'credential']
                if not any(kw in title.lower() or kw in href.lower() for kw in cert_keywords):
                    continue

                source = {'category': 'Programming & Development', 'provider': ''}
                cert = self.extract_cert_info(href, title, source)
                if cert:
                    discovered.append(cert)

        except Exception as e:
            print(f"  Search error for '{query}': {e}")

        return discovered

    async def discover_all(self) -> List[Dict]:
        """Run full discovery process."""
        print("Starting certification discovery...")
        all_discovered = []

        # Scrape known sources
        print("\n[1/3] Scraping certification sources...")
        for source in CERTIFICATION_SOURCES:
            try:
                certs = await self.scrape_source(source)
                all_discovered.extend(certs)
                await asyncio.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"  Error with {source['name']}: {e}")

        # Web search
        print(f"\n[2/3] Searching web for new certifications...")
        for query in SEARCH_QUERIES:
            print(f"  Searching: {query[:40]}...")
            try:
                certs = await self.search_web(query)
                all_discovered.extend(certs)
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"  Search error: {e}")

        # Validate discovered certs
        print(f"\n[3/3] Validating {len(all_discovered)} discovered certifications...")
        valid_certs = []

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def validate_cert(cert):
            async with semaphore:
                is_valid = await self.check_url_valid(cert['url'])
                return cert if is_valid else None

        tasks = [validate_cert(cert) for cert in all_discovered]
        results = await asyncio.gather(*tasks)
        valid_certs = [c for c in results if c]

        # Deduplicate by URL
        seen = set()
        unique_certs = []
        for cert in valid_certs:
            url_key = cert['url'].lower().rstrip('/')
            if url_key not in seen and url_key not in self.existing_urls:
                seen.add(url_key)
                unique_certs.append(cert)

        print(f"\nDiscovered {len(unique_certs)} new valid certifications")
        return unique_certs


class CertificationValidator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.session: Optional[aiohttp.ClientSession] = None

    async def setup(self):
        """Initialize session."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=MAX_CONCURRENT)
        headers = {'User-Agent': USER_AGENT}
        self.session = aiohttp.ClientSession(connector=connector, headers=headers)

    async def cleanup(self):
        if self.session:
            await self.session.close()

    async def check_url(self, url: str) -> Tuple[str, bool]:
        """Check if URL is valid."""
        try:
            async with self.session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                allow_redirects=True
            ) as response:
                if response.status < 400:
                    return url, True
            # Fallback to GET
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                allow_redirects=True
            ) as response:
                return url, response.status < 400
        except:
            return url, False

    async def validate_all(self, certifications: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Validate all certifications, return (valid, invalid) lists."""
        print(f"Validating {len(certifications)} URLs...")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def bounded_check(cert):
            async with semaphore:
                url, is_valid = await self.check_url(cert['url'])
                return cert, is_valid

        tasks = [bounded_check(cert) for cert in certifications]
        results = await asyncio.gather(*tasks)

        valid = [cert for cert, is_valid in results if is_valid]
        invalid = [cert for cert, is_valid in results if not is_valid]

        return valid, invalid


async def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    # Load current certifications
    json_file = data_dir / 'certifications.json'
    csv_file = project_root / 'free_certifications.csv'

    current_certs = []
    if json_file.exists():
        with open(json_file) as f:
            data = json.load(f)
            current_certs = data.get('certifications', [])

    print(f"Current certifications: {len(current_certs)}")

    # Step 1: Validate existing certifications
    print("\n" + "="*50)
    print("PHASE 1: Validating existing certifications")
    print("="*50)

    validator = CertificationValidator(project_root)
    await validator.setup()

    valid_certs, invalid_certs = await validator.validate_all(current_certs)

    print(f"\nValid: {len(valid_certs)}")
    print(f"Invalid (will be removed): {len(invalid_certs)}")

    if invalid_certs:
        print("\nRemoving invalid certifications:")
        for cert in invalid_certs[:10]:
            print(f"  - {cert['name'][:50]}")
        if len(invalid_certs) > 10:
            print(f"  ... and {len(invalid_certs) - 10} more")

    await validator.cleanup()

    # Step 2: Discover new certifications
    print("\n" + "="*50)
    print("PHASE 2: Discovering new certifications")
    print("="*50)

    discovery = CertificationDiscovery(project_root)
    await discovery.setup()
    discovery.existing_urls = {c['url'].lower().rstrip('/') for c in valid_certs}
    discovery.existing_names = {c['name'].lower() for c in valid_certs}

    new_certs = await discovery.discover_all()
    await discovery.cleanup()

    # Step 3: Merge and save
    print("\n" + "="*50)
    print("PHASE 3: Updating database")
    print("="*50)

    # Combine valid existing + new discoveries
    all_certs = valid_certs + new_certs

    # Sort by category and name
    all_certs.sort(key=lambda x: (x.get('category', ''), x.get('name', '')))

    # Reassign IDs
    for i, cert in enumerate(all_certs):
        cert['id'] = i + 1

    # Get unique categories, providers, levels
    categories = sorted(set(c.get('category', '') for c in all_certs if c.get('category')))
    providers = sorted(set(c.get('provider', '') for c in all_certs if c.get('provider')))
    levels = sorted(set(c.get('level', '') for c in all_certs if c.get('level')))

    # Save JSON
    output_data = {
        'metadata': {
            'total_certifications': len(all_certs),
            'last_updated': timestamp,
            'categories': categories,
            'providers': providers,
            'levels': levels,
            'validation_run': timestamp
        },
        'certifications': all_certs
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Save CSV
    fieldnames = ['Category', 'Certification_Name', 'Provider', 'URL', 'Description',
                  'Duration', 'Level', 'Prerequisites', 'Expiration']

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cert in all_certs:
            writer.writerow({
                'Category': cert.get('category', ''),
                'Certification_Name': cert.get('name', ''),
                'Provider': cert.get('provider', ''),
                'URL': cert.get('url', ''),
                'Description': cert.get('description', ''),
                'Duration': cert.get('duration', ''),
                'Level': cert.get('level', ''),
                'Prerequisites': cert.get('prerequisites', ''),
                'Expiration': cert.get('expiration', '')
            })

    # Save run report
    report = {
        'timestamp': timestamp,
        'previous_count': len(current_certs),
        'removed_invalid': len(invalid_certs),
        'discovered_new': len(new_certs),
        'final_count': len(all_certs),
        'invalid_removed': [{'name': c['name'], 'url': c['url']} for c in invalid_certs],
        'new_added': [{'name': c['name'], 'url': c['url']} for c in new_certs]
    }

    with open(data_dir / 'maintenance_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    # Summary
    print(f"\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Previous count:    {len(current_certs)}")
    print(f"Removed (invalid): {len(invalid_certs)}")
    print(f"Added (new):       {len(new_certs)}")
    print(f"Final count:       {len(all_certs)}")
    print(f"\nData saved to:")
    print(f"  - {json_file}")
    print(f"  - {csv_file}")
    print(f"  - {data_dir / 'maintenance_report.json'}")

    # Return codes for CI
    if len(invalid_certs) > 0 or len(new_certs) > 0:
        print("\n[CHANGES DETECTED] - Will commit updates")
        return 0
    else:
        print("\n[NO CHANGES] - Database is up to date")
        return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
