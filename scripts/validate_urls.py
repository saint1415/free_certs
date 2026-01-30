#!/usr/bin/env python3
"""
Validate all certification URLs and generate a report.
Checks HTTP status codes and identifies broken links.
"""

import csv
import json
import asyncio
import aiohttp
import ssl
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Configuration
TIMEOUT = 30
MAX_CONCURRENT = 20
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

async def check_url(session: aiohttp.ClientSession, url: str, cert_name: str) -> Dict:
    """Check if a URL is accessible."""
    result = {
        'url': url,
        'name': cert_name,
        'status': None,
        'valid': False,
        'error': None,
        'checked_at': datetime.utcnow().isoformat() + 'Z'
    }

    try:
        async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
            result['status'] = response.status
            result['valid'] = 200 <= response.status < 400
            if not result['valid']:
                # Try GET as fallback (some servers don't support HEAD)
                async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as get_response:
                    result['status'] = get_response.status
                    result['valid'] = 200 <= get_response.status < 400
    except asyncio.TimeoutError:
        result['error'] = 'Timeout'
    except aiohttp.ClientConnectorError as e:
        result['error'] = f'Connection error: {str(e)[:100]}'
    except aiohttp.ClientError as e:
        result['error'] = f'Client error: {str(e)[:100]}'
    except Exception as e:
        result['error'] = f'Unknown error: {str(e)[:100]}'

    return result

async def validate_all(certifications: List[Dict]) -> List[Dict]:
    """Validate all certification URLs concurrently."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=MAX_CONCURRENT)
    headers = {'User-Agent': USER_AGENT}

    results = []
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def bounded_check(cert):
            async with semaphore:
                return await check_url(session, cert['url'], cert['name'])

        tasks = [bounded_check(cert) for cert in certifications if cert.get('url')]
        results = await asyncio.gather(*tasks)

    return results

def generate_report(results: List[Dict], output_dir: Path) -> Dict:
    """Generate validation report."""
    valid_count = sum(1 for r in results if r['valid'])
    invalid_count = len(results) - valid_count

    report = {
        'summary': {
            'total_checked': len(results),
            'valid': valid_count,
            'invalid': invalid_count,
            'valid_percentage': round(valid_count / len(results) * 100, 2) if results else 0,
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        },
        'invalid_urls': [r for r in results if not r['valid']],
        'all_results': results
    }

    # Write full report
    report_file = output_dir / 'validation_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Write markdown summary for GitHub
    md_file = output_dir / 'VALIDATION_STATUS.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# URL Validation Report\n\n")
        f.write(f"**Generated:** {report['summary']['generated_at']}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total URLs | {report['summary']['total_checked']} |\n")
        f.write(f"| Valid | {report['summary']['valid']} |\n")
        f.write(f"| Invalid | {report['summary']['invalid']} |\n")
        f.write(f"| Success Rate | {report['summary']['valid_percentage']}% |\n\n")

        if report['invalid_urls']:
            f.write(f"## Invalid URLs ({len(report['invalid_urls'])})\n\n")
            f.write(f"| Certification | Status | Error |\n")
            f.write(f"|---------------|--------|-------|\n")
            for item in report['invalid_urls'][:50]:  # Limit to 50 for readability
                status = item.get('status') or 'N/A'
                error = item.get('error') or 'HTTP Error'
                name = item['name'][:50] + '...' if len(item['name']) > 50 else item['name']
                f.write(f"| {name} | {status} | {error[:30]} |\n")

            if len(report['invalid_urls']) > 50:
                f.write(f"\n*... and {len(report['invalid_urls']) - 50} more*\n")

    return report

def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)

    # Load certifications from JSON or CSV
    json_file = data_dir / 'certifications.json'
    csv_file = project_root / 'free_certifications.csv'

    certifications = []

    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            certifications = data.get('certifications', [])
    elif csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                certifications.append({
                    'name': row.get('Certification_Name', ''),
                    'url': row.get('URL', '')
                })

    if not certifications:
        print("No certifications found to validate")
        sys.exit(1)

    print(f"Validating {len(certifications)} URLs...")

    # Run validation
    results = asyncio.run(validate_all(certifications))

    # Generate report
    report = generate_report(results, data_dir)

    print(f"\nValidation Complete!")
    print(f"Valid: {report['summary']['valid']}/{report['summary']['total_checked']} ({report['summary']['valid_percentage']}%)")
    print(f"Invalid: {report['summary']['invalid']}")

    # Exit with error if too many invalid URLs (for CI)
    if report['summary']['valid_percentage'] < 80:
        print("\nWarning: More than 20% of URLs are invalid!")
        sys.exit(1)

if __name__ == '__main__':
    main()
