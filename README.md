# Free Certifications Directory

[![Validate URLs](https://github.com/saint1415/free_certs/actions/workflows/validate-urls.yml/badge.svg)](https://github.com/saint1415/free_certs/actions/workflows/validate-urls.yml)
[![Data Quality](https://github.com/saint1415/free_certs/actions/workflows/data-quality.yml/badge.svg)](https://github.com/saint1415/free_certs/actions/workflows/data-quality.yml)
[![Discover Certs](https://github.com/saint1415/free_certs/actions/workflows/discover-certs.yml/badge.svg)](https://github.com/saint1415/free_certs/actions/workflows/discover-certs.yml)

A curated directory of **780+ free professional certifications** across Cloud Computing, Cybersecurity, Programming, AI/ML, and 40+ other categories.

## Live Demo

**[View the Interactive Directory](https://saint1415.github.io/free_certs/)**

## Features

- **780+ Free Certifications** - Verified and categorized
- **40+ Categories** - Cloud, Security, Programming, AI/ML, Engineering, and more
- **Modern UI** - Responsive design with dark mode support
- **Smart Search** - Filter by category, provider, level, or keyword
- **Automated Validation** - Weekly URL checks ensure links stay fresh
- **Auto-Discovery** - Monthly scans find new certifications
- **JSON API** - Access data programmatically at `/data/certifications.json`

## Categories

| Category | Count | Category | Count |
|----------|-------|----------|-------|
| Cloud Computing | 170+ | Cybersecurity | 20+ |
| Programming & Development | 40+ | AI & Machine Learning | 20+ |
| Data Science & Analytics | 18+ | Engineering | 100+ |
| Business & Management | 20+ | Digital Marketing | 20+ |
| And 30+ more categories... | | | |

## Quick Start

### View Online
Visit **[saint1415.github.io/free_certs](https://saint1415.github.io/free_certs/)**

### Use the API
```bash
curl https://saint1415.github.io/free_certs/data/certifications.json
```

### Clone Locally
```bash
git clone https://github.com/saint1415/free_certs.git
cd free_certs
# Open index.html in your browser
```

## Data Format

### CSV Structure
```csv
Category,Certification_Name,Provider,URL,Description,Duration,Level,Prerequisites,Expiration
```

### JSON Structure
```json
{
  "metadata": {
    "total_certifications": 781,
    "last_updated": "2024-01-01T00:00:00Z",
    "categories": ["..."],
    "providers": ["..."],
    "levels": ["Beginner", "Intermediate", "Advanced", "..."]
  },
  "certifications": [
    {
      "id": 1,
      "category": "Cloud Computing",
      "name": "AWS Cloud Practitioner",
      "provider": "Amazon Web Services",
      "url": "https://...",
      "description": "...",
      "duration": "Self-paced",
      "level": "Beginner",
      "prerequisites": "",
      "expiration": "3 years"
    }
  ]
}
```

## Automation

This repository includes GitHub Actions for automated maintenance:

### URL Validation (Weekly)
- Checks all certification URLs for broken links
- Generates validation reports
- Creates issues for dead links
- Runs every Sunday at 2:00 AM UTC

### Certificate Discovery (Monthly)
- Searches known sources for new certifications
- Auto-creates PRs with discoveries
- Runs on the 1st of each month

### Data Quality Check (On PR)
- Validates CSV format
- Detects duplicates
- Checks for missing required fields

## Contributing

We welcome contributions! Here's how you can help:

### Add a Certification
1. Fork the repository
2. Add your certification to `free_certifications.csv`
3. Ensure all required fields are filled:
   - Category
   - Certification_Name
   - Provider
   - URL (must be working)
   - Description
   - Duration
   - Level (Beginner/Intermediate/Advanced)
4. Submit a Pull Request

### Report Issues
- [Report a broken link](https://github.com/saint1415/free_certs/issues/new?labels=broken-link)
- [Suggest a new certification](https://github.com/saint1415/free_certs/issues/new?labels=new-cert)
- [Report a bug](https://github.com/saint1415/free_certs/issues/new?labels=bug)

### Guidelines
- Only add certifications that are **completely free**
- Ensure the certification provides a verifiable credential
- Include accurate duration estimates
- Properly categorize using existing categories when possible

## Local Development

### Run Data Scripts
```bash
# Install dependencies
pip install aiohttp beautifulsoup4

# Clean and generate JSON
python scripts/clean_data.py

# Validate URLs (takes a while)
python scripts/validate_urls.py

# Discover new certifications
python scripts/discover_certs.py
```

### Project Structure
```
free_certs/
├── index.html                 # Main website
├── linkedin_posts.html        # LinkedIn post generator
├── free_certifications.csv    # Source data
├── data/
│   ├── certifications.json    # Generated JSON API
│   ├── validation_report.json # URL validation results
│   └── discoveries.json       # New cert discoveries
├── scripts/
│   ├── clean_data.py          # Data cleaning & JSON generation
│   ├── validate_urls.py       # URL validation
│   └── discover_certs.py      # Certificate discovery
└── .github/workflows/
    ├── validate-urls.yml      # Weekly URL validation
    ├── discover-certs.yml     # Monthly discovery
    └── data-quality.yml       # PR quality checks
```

## License

This project is open source and available for anyone to use.

## Acknowledgments

- All certification providers for offering free learning opportunities
- Contributors who help maintain and expand this directory
- The open source community

---

**Start your learning journey today!** Browse the [directory](https://saint1415.github.io/free_certs/) and earn your first certification.
