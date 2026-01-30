#!/usr/bin/env python3
"""
Clean and normalize the free certifications CSV data.
- Removes duplicate columns
- Normalizes category names
- Validates URLs
- Generates JSON output
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime

def clean_category(category: str) -> str:
    """Normalize category names."""
    category = category.strip()
    # Remove sub-categories in parentheses for main category grouping
    main_category = re.sub(r'\s*\([^)]+\)', '', category).strip()
    return category

def clean_url(url: str) -> str:
    """Clean and validate URL format."""
    url = url.strip()
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def normalize_level(level: str) -> str:
    """Normalize certification level."""
    level = level.strip().lower()
    level_mapping = {
        'beginner': 'Beginner',
        'beginner-intermediate': 'Beginner-Intermediate',
        'intermediate': 'Intermediate',
        'intermediate-advanced': 'Intermediate-Advanced',
        'advanced': 'Advanced',
        'associate': 'Associate',
        'professional': 'Professional',
        'expert': 'Expert',
        '': 'Not Specified'
    }
    return level_mapping.get(level, level.title())

def main():
    project_root = Path(__file__).parent.parent
    input_file = project_root / 'free_certifications.csv'
    output_csv = project_root / 'free_certifications.csv'
    output_json = project_root / 'data' / 'certifications.json'

    # Ensure data directory exists
    output_json.parent.mkdir(exist_ok=True)

    certifications = []
    seen_urls = set()
    duplicates = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip if URL is duplicate
            url = clean_url(row.get('URL', ''))
            if url in seen_urls:
                duplicates += 1
                continue
            seen_urls.add(url)

            cert = {
                'id': len(certifications) + 1,
                'category': clean_category(row.get('Category', '')),
                'name': row.get('Certification_Name', '').strip(),
                'provider': row.get('Provider', '').strip(),
                'url': url,
                'description': row.get('Description', '').strip(),
                'duration': row.get('Duration', '').strip(),
                'level': normalize_level(row.get('Level', '')),
                'prerequisites': row.get('Prerequisites', '').strip(),
                'expiration': row.get('Expiration', '').strip(),
                'validated': None,
                'last_checked': None
            }

            # Skip entries without essential data
            if not cert['name'] or not cert['url']:
                continue

            certifications.append(cert)

    # Sort by category, then name
    certifications.sort(key=lambda x: (x['category'], x['name']))

    # Re-assign IDs after sorting
    for i, cert in enumerate(certifications):
        cert['id'] = i + 1

    # Write cleaned CSV (without the duplicate column)
    fieldnames = ['Category', 'Certification_Name', 'Provider', 'URL', 'Description',
                  'Duration', 'Level', 'Prerequisites', 'Expiration']

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cert in certifications:
            writer.writerow({
                'Category': cert['category'],
                'Certification_Name': cert['name'],
                'Provider': cert['provider'],
                'URL': cert['url'],
                'Description': cert['description'],
                'Duration': cert['duration'],
                'Level': cert['level'],
                'Prerequisites': cert['prerequisites'],
                'Expiration': cert['expiration']
            })

    # Generate JSON with metadata
    output_data = {
        'metadata': {
            'total_certifications': len(certifications),
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'categories': sorted(list(set(c['category'] for c in certifications))),
            'providers': sorted(list(set(c['provider'] for c in certifications))),
            'levels': sorted(list(set(c['level'] for c in certifications)))
        },
        'certifications': certifications
    }

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(certifications)} certifications")
    print(f"Removed {duplicates} duplicates")
    print(f"Categories: {len(output_data['metadata']['categories'])}")
    print(f"Providers: {len(output_data['metadata']['providers'])}")
    print(f"Output: {output_csv}, {output_json}")

if __name__ == '__main__':
    main()
