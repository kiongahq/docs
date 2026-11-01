"""Refresh the documentation's public release snapshot without modifying Git history."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORIES = (
    'platform', 'contracts', 'sdk-python', 'agent-runtime', 'pipeline-runner',
    'serving', 'trace-proxy', 'workspace', 'deploy', 'docs', '.github',
)
ROOT = Path(__file__).resolve().parents[1]


def fetch_releases(repository):
    if repository not in REPOSITORIES:
        raise ValueError('Repository is not in the public release catalog')
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
               'User-Agent': 'kionga-docs-release-catalog'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(f'https://api.github.com/repos/kiongahq/{repository}/releases?per_page=5',
                      headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:  # nosec B310 -- fixed HTTPS API origin
                return json.load(response)
        except (HTTPError, URLError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def snapshot(fetch=fetch_releases):
    repositories = {}
    for repository in REPOSITORIES:
        releases = []
        for release in fetch(repository):
            if release.get('draft') or not release.get('published_at'):
                continue
            published = datetime.fromisoformat(release['published_at'].replace('Z', '+00:00'))
            releases.append({
                'tag': str(release['tag_name']),
                'name': str(release.get('name') or release['tag_name']),
                'published_at': published.isoformat(),
                'prerelease': bool(release.get('prerelease')),
                'body': str(release.get('body') or ''),
                'assets': [str(asset['name']) for asset in release.get('assets', [])],
            })
        repositories[repository] = sorted(releases, key=lambda r: r['published_at'], reverse=True)
    return {'schema_version': 1, 'updated_at': datetime.now(timezone.utc).isoformat(),
            'repositories': repositories}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'releases.json')
    args = parser.parse_args()
    # Fetch every repository successfully before replacing the last usable snapshot.
    data = snapshot()
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(args.output)
    print('Updated published releases for all public components.')


if __name__ == '__main__':
    main()
