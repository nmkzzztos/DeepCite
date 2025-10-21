#!/usr/bin/env python3
"""
Script to add GitHub projects to projects.json

This script fetches project metadata from GitHub and adds it to the projects.json file
used by the DeepCite documentation site.

Usage:
    python add_project.py <github_repo_or_url> [category] [description]

Examples:
    # Interactive mode (will prompt for category and description)
    python add_project.py langchain-ai/langchain

    # Non-interactive mode with all parameters
    python add_project.py langchain-ai/langchain "AI Frameworks" "Framework for developing applications powered by language models"

    # Works with URLs too
    python add_project.py https://github.com/langchain-ai/langchain

Arguments:
    github_repo_or_url: GitHub repository in format owner/repo or full URL
    category: Optional category string (will prompt if not provided)
    description: Optional description override (will fetch from GitHub if not provided)
"""

import sys
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import httpx
from urllib.parse import urlparse
import asyncio

# Handle Unicode encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class GitHubProject:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.name = kwargs.get('name', '')
        self.full_name = kwargs.get('full_name', '')
        self.description = kwargs.get('description', '')
        self.owner = kwargs.get('owner', {})
        self.html_url = kwargs.get('html_url', '')
        self.created_at = kwargs.get('created_at', '')
        self.updated_at = kwargs.get('updated_at', '')
        self.stargazers_count = kwargs.get('stargazers_count', 0)
        self.language = kwargs.get('language', '')
        self.license = kwargs.get('license', {})
        self.homepage = kwargs.get('homepage', '')
        self.topics = kwargs.get('topics', [])
        self.contributors_url = kwargs.get('contributors_url', '')


class GitHubApiService:
    """GitHub API service for fetching repository information"""

    def __init__(self, token: Optional[str] = None):
        self.base_url = 'https://api.github.com'
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'DeepCite-Project-Adder/1.0'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

    async def get_repository(self, owner: str, repo: str) -> Optional[GitHubProject]:
        """Get repository information from GitHub API"""
        url = f"{self.base_url}/repos/{owner}/{repo}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 404:
                    print(f"Repository {owner}/{repo} not found")
                    return None
                elif response.status_code == 403:
                    print("Rate limit exceeded. Consider providing a GitHub token via GITHUB_TOKEN environment variable")
                    return None
                elif response.status_code != 200:
                    print(f"GitHub API error: {response.status_code}")
                    return None

                data = response.json()
                return GitHubProject(**data)

        except Exception as e:
            print(f"Error fetching from GitHub: {e}")
            return None

    async def get_readme_content(self, owner: str, repo: str) -> Optional[str]:
        """Get README content from repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/readme"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    return None

                data = response.json()
                if 'content' in data:
                    import base64
                    content = base64.b64decode(data['content']).decode('utf-8')
                    return content

        except Exception as e:
            print(f"Error fetching README: {e}")
            return None

    def extract_description_from_readme(self, readme_content: str) -> Optional[str]:
        """Extract project description from README content"""
        if not readme_content:
            return None

        # Try to find description in the first few lines
        lines = readme_content.split('\n')[:10]  # Check first 10 lines

        for line in lines:
            line = line.strip()
            # Skip empty lines, headers, badges
            if not line or line.startswith('#') or '[' in line or '!' in line:
                continue
            # Look for meaningful description (longer than 20 chars)
            if len(line) > 20 and not line.startswith('```'):
                return line

        return None


def extract_github_repo(input_str: str) -> Tuple[str, str]:
    """Extract owner and repo from GitHub URL or return as-is if it's already owner/repo"""
    # Handle URLs like https://github.com/owner/repo
    github_match = re.search(r'github\.com/([^/]+)/([^/]+)', input_str)
    if github_match:
        owner, repo = github_match.groups()
        # Remove .git suffix if present
        repo = repo.rstrip('.git')
        return owner, repo

    # Handle direct owner/repo input
    if '/' in input_str and len(input_str.split('/')) == 2:
        owner, repo = input_str.split('/')
        return owner, repo

    raise ValueError(f"Could not extract valid GitHub repository from: {input_str}")


def create_project_id(name: str) -> str:
    """Create URL-friendly ID from project name"""
    # Convert to lowercase, replace spaces and special chars with hyphens
    id_str = name.lower()
    id_str = re.sub(r'[^\w\s-]', '', id_str)  # Remove special characters except spaces and hyphens
    id_str = re.sub(r'[\s_-]+', '-', id_str)  # Replace spaces, underscores, multiple hyphens with single hyphen
    id_str = id_str.strip('-')  # Remove leading/trailing hyphens
    return id_str


def format_contributors(contributors) -> str:
    """Format contributors list for JSON"""
    if isinstance(contributors, list):
        return ', '.join(contributors)
    return str(contributors)


def extract_year(date_str: str) -> int:
    """Extract year from ISO date string"""
    try:
        # Handle ISO format: 2023-12-15T10:30:00Z
        if 'T' in date_str:
            date_part = date_str.split('T')[0]
            return int(date_part.split('-')[0])
        # Handle other formats
        return int(date_str[:4])
    except (ValueError, IndexError):
        return datetime.now().year


def detect_category_from_topics(topics: list, language: str) -> str:
    """Try to detect category from repository topics and language"""
    topic_to_category = {
        'machine-learning': 'AI Frameworks',
        'artificial-intelligence': 'AI Frameworks',
        'llm': 'AI Frameworks',
        'nlp': 'NLP Libraries',
        'natural-language-processing': 'NLP Libraries',
        'computer-vision': 'Computer Vision',
        'deep-learning': 'AI Frameworks',
        'neural-network': 'AI Frameworks',
        'chatbot': 'AI Applications',
        'rag': 'RAG Frameworks',
        'retrieval-augmented-generation': 'RAG Frameworks',
        'vector-database': 'Vector Databases',
        'embedding': 'Embeddings',
        'speech-recognition': 'Speech & Audio',
        'text-to-speech': 'Speech & Audio',
        'gradio': 'UI & Interfaces',
        'streamlit': 'UI & Interfaces',
        'web-ui': 'UI & Interfaces',
        'agent': 'Agent Frameworks',
        'autonomous-agent': 'Agent Frameworks',
        'search': 'Search & Retrieval',
        'document-processing': 'Document Processing',
        'pdf': 'Document Processing'
    }

    # Check topics first
    for topic in topics:
        if topic in topic_to_category:
            return topic_to_category[topic]

    # Check language
    if language:
        lang_to_category = {
            'Python': 'AI Frameworks',
            'JavaScript': 'UI & Interfaces',
            'TypeScript': 'UI & Interfaces',
            'Go': 'Infrastructure',
            'Rust': 'Infrastructure',
            'C++': 'Infrastructure'
        }
        if language in lang_to_category:
            return lang_to_category[language]

    return ""  # Will prompt user


async def update_all_stars():
    """Update star counts for all existing projects"""
    projects_file = Path(__file__).parent / "src" / "pages" / "projects.json"

    try:
        with open(projects_file, 'r', encoding='utf-8') as f:
            projects_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {projects_file} not found!")
        return
    except json.JSONDecodeError:
        print(f"Error: {projects_file} contains invalid JSON!")
        return

    if not projects_data:
        print("No projects found in projects.json")
        return

    service = GitHubApiService()
    updated_count = 0
    error_count = 0

    print(f"Updating star counts for {len(projects_data)} projects...")

    for i, project in enumerate(projects_data):
        github_url = project.get('github', '')
        if not github_url:
            print(f"⚠️  Project '{project.get('title', 'Unknown')}' has no GitHub URL, skipping")
            continue

        try:
            # Extract owner/repo from GitHub URL
            owner, repo = extract_github_repo(github_url)
            print(f"[{i+1}/{len(projects_data)}] Fetching {owner}/{repo}...")

            # Fetch current project data
            current_project = await service.get_repository(owner, repo)
            if current_project and current_project.stargazers_count != project.get('stars', 0):
                old_stars = project.get('stars', 0)
                project['stars'] = current_project.stargazers_count
                print(f"  ✅ Updated {owner}/{repo}: {old_stars} → {current_project.stargazers_count} stars")
                updated_count += 1
            elif current_project:
                print(f"  ✓ {owner}/{repo}: stars are up to date ({current_project.stargazers_count})")
            else:
                print(f"  ❌ Failed to fetch {owner}/{repo}")
                error_count += 1

        except Exception as e:
            print(f"  ❌ Error updating {github_url}: {e}")
            error_count += 1

    # Save updated data
    try:
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(projects_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully updated {updated_count} projects")
        if error_count > 0:
            print(f"⚠️  {error_count} projects had errors")
    except Exception as e:
        print(f"Error saving to projects.json: {e}")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "update_stars":
        # Update all stars
        asyncio.run(update_all_stars())
        return

    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print("Usage: python add_project.py <github_repo_or_url> [category] [description] [stars]")
        print("Examples:")
        print("  python add_project.py langchain-ai/langchain")
        print("  python add_project.py https://github.com/langchain-ai/langchain")
        print("  python add_project.py langchain-ai/langchain 'AI Frameworks' 'Framework for LLM applications'")
        sys.exit(1)

    input_str = sys.argv[1]
    category_arg = sys.argv[2] if len(sys.argv) >= 3 else None
    description_arg = sys.argv[3] if len(sys.argv) >= 4 else None
    stars_arg = sys.argv[4] if len(sys.argv) >= 5 else None
    
    try:
        owner, repo = extract_github_repo(input_str)
        print(f"Fetching project: {owner}/{repo}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Initialize the GitHubApiService
    service = GitHubApiService()

    # Fetch project data
    import asyncio

    async def fetch_project():
        project = await service.get_repository(owner, repo)
        if project:
            # Try to get better description from README
            readme_content = await service.get_readme_content(owner, repo)
            if readme_content:
                readme_description = service.extract_description_from_readme(readme_content)
                if readme_description and len(readme_description) > len(project.description or ''):
                    project.description = readme_description
        return project

    # Run the async function
    project = asyncio.run(fetch_project())

    if not project:
        print(f"Error: Could not fetch project {owner}/{repo}")
        sys.exit(1)

    # Create the project entry
    project_id = create_project_id(project.name)
    year = extract_year(project.created_at)

    # Detect or get category
    detected_category = detect_category_from_topics(project.topics, project.language)
    if category_arg:
        category = category_arg
        print(f"Category (from args): {category}")
    elif detected_category:
        category = detected_category
        print(f"Category (auto-detected): {category}")
    else:
        try:
            category = input("Category: ").strip()
            if not category:
                print("Warning: Category is empty. You can edit projects.json later to add it.")
        except EOFError:
            print("Warning: No category provided. You can edit projects.json later to add it.")
            category = ""

    # Get description
    description = description_arg or project.description or ""
    if description_arg:
        print(f"Description (from args): {description}")
    elif not description:
        try:
            description = input("Description: ").strip()
            if not description:
                print("Warning: Description is empty. You can edit projects.json later to add it.")
        except EOFError:
            print("Warning: No description provided. You can edit projects.json later to add it.")
            description = ""
            
    # Get stars
    github_stars = project.stargazers_count
    if stars_arg:
        try:
            user_stars = int(stars_arg)
            if user_stars != github_stars:
                print(f"Warning: Provided stars count ({user_stars}) differs from GitHub ({github_stars}). Using GitHub value.")
        except ValueError:
            print(f"Warning: '{stars_arg}' is not a valid number. Using GitHub stars: {github_stars}")

    stars = github_stars
    print(f"Stars: {stars}")

    # Get license
    license_name = ""
    if project.license and isinstance(project.license, dict):
        license_name = project.license.get('name', '')

    project_entry = {
        "id": project_id,
        "title": project.name,
        "authors": project.owner.get('login', 'Unknown') if project.owner else 'Unknown',
        "year": year,
        "abstract": description,
        "category": category,
        "github": project.html_url,
        "stars": stars,
        "license": license_name
    }

    # Add optional fields if available
    if project.homepage:
        project_entry["demo"] = project.homepage

    # Display the fetched information
    print("\n" + "="*80)
    print("FETCHED PROJECT INFORMATION:")
    print("="*80)
    print(f"Name: {project.name}")
    print(f"Owner: {project.owner.get('login', 'Unknown') if project.owner else 'Unknown'}")
    print(f"Year: {year}")
    print(f"Stars: {stars}")
    print(f"Language: {project.language}")
    print(f"License: {license_name}")
    print(f"Description: {description[:200]}{'...' if len(description) > 200 else ''}")
    if project.homepage:
        print(f"Homepage: {project.homepage}")
    if project.topics:
        print(f"Topics: {', '.join(project.topics[:5])}{'...' if len(project.topics) > 5 else ''}")
    print("="*80)

    # Load existing projects.json
    projects_file = Path(__file__).parent / "src" / "pages" / "projects.json"

    try:
        with open(projects_file, 'r', encoding='utf-8') as f:
            projects_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {projects_file} not found!")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {projects_file} contains invalid JSON!")
        sys.exit(1)

    # Check if project already exists
    existing_ids = [p.get('id') for p in projects_data]
    if project_id in existing_ids:
        print(f"Warning: Project with ID '{project_id}' already exists in projects.json")
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Aborted.")
            sys.exit(0)
        else:
            # Remove existing entry
            projects_data = [p for p in projects_data if p.get('id') != project_id]

    # Add new project to the beginning of the list
    projects_data.insert(0, project_entry)

    # Save back to file
    try:
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(projects_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully added project '{project.name}' to projects.json")
        print(f"   ID: {project_id}")
        print(f"   Category: {category}")
        print(f"   Stars: {project.stargazers_count}")
    except Exception as e:
        print(f"Error saving to projects.json: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()