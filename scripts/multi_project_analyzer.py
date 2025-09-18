#!/usr/bin/env python3
"""
Multi-Project Lines of Code Analysis Tool
Analyzes LOC and tracks changes across multiple projects within a configurable time period.
"""

import os
import json
import subprocess
import sys
import argparse
from datetime import datetime
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import yaml
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProjectInfo:
    name: str
    path: str
    type: str
    size: int
    last_modified: str
    languages: Dict[str, int]
    is_git_repo: bool

@dataclass
class LOCStats:
    total_lines: int
    source_lines: int
    comment_lines: int
    blank_lines: int
    languages: Dict[str, Dict[str, int]]

@dataclass
class ChangeStats:
    lines_added: int
    lines_removed: int
    lines_modified: int
    net_change: int
    commits_count: int
    files_changed: int
    contributors: List[str]
    commits_details: List[Dict[str, Any]] = None

class MultiProjectAnalyzer:
    def __init__(self, config_path: str):
        """Initialize analyzer with configuration"""
        self.config = self._load_config(config_path)
        self.projects = []
        self.results = {}

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_path} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            sys.exit(1)

    def discover_projects(self, root_paths: List[str]) -> List[ProjectInfo]:
        """Discover all projects in the specified root directories (max depth 1)"""
        logger.info(f"Discovering projects in {len(root_paths)} root directories...")
        projects = []

        project_markers = {
            '.git': 'git',
            'package.json': 'nodejs',
            'pom.xml': 'java-maven',
            'build.gradle': 'java-gradle',
            'Cargo.toml': 'rust',
            'setup.py': 'python-setuptools',
            'pyproject.toml': 'python-modern',
            'go.mod': 'go',
            'composer.json': 'php',
            'Gemfile': 'ruby',
            'CMakeLists.txt': 'cpp-cmake',
            'Makefile': 'c-make'
        }

        for root_path in root_paths:
            if not os.path.exists(root_path):
                logger.warning(f"Root path {root_path} does not exist, skipping...")
                continue

            # Check if the root path itself is a project
            self._check_and_add_project(root_path, project_markers, projects)

            # Check direct subdirectories only (max depth 1)
            try:
                for item in os.listdir(root_path):
                    item_path = os.path.join(root_path, item)
                    if os.path.isdir(item_path) and not self._should_exclude_dir(item):
                        self._check_and_add_project(item_path, project_markers, projects)
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not access directory {root_path}: {e}")

        logger.info(f"Discovered {len(projects)} projects")
        return projects

    def _check_and_add_project(self, path: str, project_markers: Dict[str, str], projects: List[ProjectInfo]):
        """Check if a directory is a project and add it to the list"""
        try:
            files = os.listdir(path)
            dirs = [f for f in files if os.path.isdir(os.path.join(path, f))]
            files = [f for f in files if os.path.isfile(os.path.join(path, f))]

            project_type = None
            is_git_repo = '.git' in dirs

            # Detect project type
            for marker, ptype in project_markers.items():
                if marker in files or marker in dirs:
                    project_type = ptype
                    break

            if project_type:
                project_name = os.path.basename(path)
                project_info = ProjectInfo(
                    name=project_name,
                    path=path,
                    type=project_type,
                    size=self._get_directory_size(path),
                    last_modified=self._get_last_modified(path),
                    languages={},
                    is_git_repo=is_git_repo
                )
                projects.append(project_info)
                logger.info(f"Found {project_type} project: {project_name}")

        except (OSError, PermissionError) as e:
            logger.warning(f"Could not access directory {path}: {e}")

    def _should_exclude_dir(self, dirname: str) -> bool:
        """Check if directory should be excluded"""
        exclude_dirs = self.config.get('filters', {}).get('exclude_directories', [])
        return dirname in exclude_dirs

    def _should_exclude_file(self, filepath: str) -> bool:
        """Check if file should be excluded"""
        exclude_patterns = self.config.get('filters', {}).get('exclude_files', [])
        filename = os.path.basename(filepath)

        for pattern in exclude_patterns:
            if pattern.startswith('*.'):
                extension = pattern[1:]
                if filename.endswith(extension):
                    return True
            elif pattern == filename:
                return True
        return False

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for filename in filenames:
                    if not self._should_exclude_file(filename):
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, IOError):
                            continue
        except (OSError, IOError):
            pass
        return total_size

    def _get_last_modified(self, path: str) -> str:
        """Get last modification time of directory"""
        try:
            timestamp = os.path.getmtime(path)
            return datetime.fromtimestamp(timestamp).isoformat()
        except (OSError, IOError):
            return datetime.now().isoformat()

    def analyze_current_loc(self, project: ProjectInfo) -> LOCStats:
        """Analyze current lines of code using cloc"""
        logger.info(f"Analyzing LOC for project: {project.name}")

        # Build cloc command
        exclude_dirs = ','.join(self.config.get('filters', {}).get('exclude_directories', []))
        cmd = [
            'cloc', '--json', '--quiet',
            '--exclude-dir=' + exclude_dirs if exclude_dirs else '--exclude-dir=',
            project.path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"cloc failed for {project.name}: {result.stderr}")
                return self._create_empty_loc_stats()

            cloc_data = json.loads(result.stdout)
            return self._parse_cloc_output(cloc_data)

        except subprocess.TimeoutExpired:
            logger.error(f"cloc timeout for {project.name}")
            return self._create_empty_loc_stats()
        except json.JSONDecodeError:
            logger.error(f"Failed to parse cloc output for {project.name}")
            return self._create_empty_loc_stats()
        except FileNotFoundError:
            logger.error("cloc not found. Install with: apt-get install cloc or brew install cloc")
            return self._create_empty_loc_stats()

    def _create_empty_loc_stats(self) -> LOCStats:
        """Create empty LOC stats"""
        return LOCStats(
            total_lines=0,
            source_lines=0,
            comment_lines=0,
            blank_lines=0,
            languages={}
        )

    def _parse_cloc_output(self, cloc_data: Dict[str, Any]) -> LOCStats:
        """Parse cloc JSON output into LOCStats"""
        languages = {}
        total_files = 0
        total_lines = 0
        source_lines = 0
        comment_lines = 0
        blank_lines = 0

        for lang, data in cloc_data.items():
            if lang in ['header', 'SUM']:
                if lang == 'SUM':
                    total_files = data.get('nFiles', 0)
                    source_lines = data.get('code', 0)
                    comment_lines = data.get('comment', 0)
                    blank_lines = data.get('blank', 0)
                    total_lines = source_lines + comment_lines + blank_lines
                elif lang == 'header':
                    # Get totals from header if SUM is not available
                    if 'n_lines' in data:
                        total_lines = data['n_lines']
                    if 'n_files' in data:
                        total_files = data['n_files']
                continue

            # Parse individual language data
            files_count = data.get('nFiles', 0)
            code_lines = data.get('code', 0)
            comment_lines_lang = data.get('comment', 0)
            blank_lines_lang = data.get('blank', 0)
            total_lines_lang = code_lines + comment_lines_lang + blank_lines_lang

            languages[lang] = {
                'files': files_count,
                'lines': total_lines_lang,
                'code': code_lines,
                'comments': comment_lines_lang,
                'blanks': blank_lines_lang
            }

            # Aggregate totals if SUM section is not present
            if total_lines == 0:
                source_lines += code_lines
                comment_lines += comment_lines_lang
                blank_lines += blank_lines_lang
                total_files += files_count

        # Calculate total_lines if not set from header
        if total_lines == 0:
            total_lines = source_lines + comment_lines + blank_lines

        return LOCStats(
            total_lines=total_lines,
            source_lines=source_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            languages=languages
        )

    def analyze_git_changes(self, project: ProjectInfo, start_date: str, end_date: str) -> ChangeStats:
        """Analyze git changes in the specified time period"""
        if not project.is_git_repo:
            logger.info(f"Skipping git analysis for {project.name} (not a git repo)")
            return ChangeStats(0, 0, 0, 0, 0, 0, [], [])

        logger.info(f"Analyzing git changes for project: {project.name}")

        original_cwd = os.getcwd()
        try:
            os.chdir(project.path)

            # Get commit statistics
            cmd = [
                'git', 'log', '--pretty=format:%H|%ad|%an|%s',
                '--date=short', '--numstat',
                f'--since={start_date}', f'--until={end_date}'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"git log failed for {project.name}: {result.stderr}")
                return ChangeStats(0, 0, 0, 0, 0, 0, [], [])

            return self._parse_git_output(result.stdout)

        except subprocess.TimeoutExpired:
            logger.error(f"git log timeout for {project.name}")
            return ChangeStats(0, 0, 0, 0, 0, 0, [], [])
        finally:
            os.chdir(original_cwd)

    def _should_exclude_author(self, author: str) -> bool:
        """Check if commit author should be excluded"""
        exclude_authors = self.config.get('git', {}).get('exclude_authors', [])

        # Case-insensitive comparison
        author_lower = author.lower().strip()
        for exclude_author in exclude_authors:
            if exclude_author.lower().strip() in author_lower:
                return True
        return False

    def _parse_git_output(self, output: str) -> ChangeStats:
        """Parse git log output into ChangeStats"""
        lines = output.strip().split('\n')
        if not lines or lines == ['']:
            return ChangeStats(0, 0, 0, 0, 0, 0, [], [])

        commits = []
        contributors = set()
        total_added = 0
        total_removed = 0
        files_changed = set()
        excluded_commits = 0

        current_commit = None
        for line in lines:
            if '|' in line and len(line.split('|')) >= 4:
                # New commit header
                parts = line.split('|', 3)
                hash_val, date, author, message = parts

                # Check if author should be excluded
                if self._should_exclude_author(author):
                    excluded_commits += 1
                    current_commit = None  # Skip this commit
                    continue

                contributors.add(author)
                current_commit = {
                    'hash': hash_val,
                    'date': date,
                    'author': author,
                    'message': message,
                    'files': []
                }
                commits.append(current_commit)
            elif '\t' in line and current_commit:
                # File change line (only process if commit is not excluded)
                parts = line.split('\t')
                if len(parts) >= 3:
                    added_str, removed_str, filename = parts[0], parts[1], parts[2]

                    # Handle binary files (marked with -)
                    added = int(added_str) if added_str.isdigit() else 0
                    removed = int(removed_str) if removed_str.isdigit() else 0

                    total_added += added
                    total_removed += removed
                    files_changed.add(filename)

                    current_commit['files'].append({
                        'added': added,
                        'removed': removed,
                        'file': filename
                    })

        net_change = total_added - total_removed
        lines_modified = min(total_added, total_removed)  # Approximation

        if excluded_commits > 0:
            logger.info(f"Excluded {excluded_commits} automated commits from analysis")

        return ChangeStats(
            lines_added=total_added,
            lines_removed=total_removed,
            lines_modified=lines_modified,
            net_change=net_change,
            commits_count=len(commits),
            files_changed=len(files_changed),
            contributors=list(contributors),
            commits_details=commits
        )

    def _get_git_state(self, project_path: str) -> Dict[str, Any]:
        """Get current git state for backup purposes"""
        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)

            git_state = {
                'project_path': project_path,
                'original_branch': None,
                'original_commit': None,
                'is_detached': False,
                'has_stash': False,
                'working_directory_clean': True
            }

            # Get current branch or commit
            try:
                # Check if we're on a branch
                result = subprocess.run(['git', 'symbolic-ref', '--short', 'HEAD'],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    git_state['original_branch'] = result.stdout.strip()
                else:
                    # We're in detached HEAD state
                    git_state['is_detached'] = True
                    result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        git_state['original_commit'] = result.stdout.strip()
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout getting git state for {project_path}")

            # Check if working directory is clean
            try:
                result = subprocess.run(['git', 'status', '--porcelain'],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    git_state['working_directory_clean'] = False
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout checking git status for {project_path}")

            return git_state

        except Exception as e:
            logger.error(f"Error getting git state for {project_path}: {e}")
            return None
        finally:
            os.chdir(original_cwd)

    def _stash_changes(self, project_path: str) -> bool:
        """Stash uncommitted changes"""
        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)

            result = subprocess.run(['git', 'stash', 'push', '-m', 'LOC Analysis Backup'],
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                logger.info(f"Stashed uncommitted changes in {project_path}")
                return True
            else:
                logger.warning(f"Failed to stash changes in {project_path}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout stashing changes in {project_path}")
            return False
        except Exception as e:
            logger.error(f"Error stashing changes in {project_path}: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    def _restore_git_state(self, git_state: Dict[str, Any]) -> bool:
        """Restore git state to original condition"""
        if not git_state:
            return False

        project_path = git_state['project_path']
        original_cwd = os.getcwd()

        try:
            os.chdir(project_path)

            # Restore original branch or commit
            if git_state['original_branch']:
                result = subprocess.run(['git', 'checkout', git_state['original_branch']],
                                      capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    logger.error(f"Failed to restore branch {git_state['original_branch']} in {project_path}: {result.stderr}")
                    return False
            elif git_state['original_commit']:
                result = subprocess.run(['git', 'checkout', git_state['original_commit']],
                                      capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    logger.error(f"Failed to restore commit {git_state['original_commit']} in {project_path}: {result.stderr}")
                    return False

            # Restore stashed changes if any
            if git_state['has_stash']:
                result = subprocess.run(['git', 'stash', 'pop'],
                                      capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    logger.warning(f"Failed to restore stashed changes in {project_path}: {result.stderr}")

            logger.info(f"Successfully restored git state for {project_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout restoring git state for {project_path}")
            return False
        except Exception as e:
            logger.error(f"Error restoring git state for {project_path}: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    def _find_target_commit(self, project_path: str, end_date: str) -> str:
        """Find commit that matches the end date (or closest previous one)"""
        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)

            # First, try to find commit on or before the end date
            cmd = [
                'git', 'log', '--format=%H', '--until', f'{end_date} 23:59:59',
                '--max-count=1'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout.strip():
                target_commit = result.stdout.strip()
                logger.info(f"Found target commit {target_commit[:8]} for date {end_date} in {project_path}")
                return target_commit

            # If no commits before end date, use the earliest commit
            logger.warning(f"No commits found before {end_date} in {project_path}, using earliest commit")
            cmd = ['git', 'log', '--format=%H', '--reverse', '--max-count=1']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout.strip():
                earliest_commit = result.stdout.strip()
                logger.info(f"Using earliest commit {earliest_commit[:8]} in {project_path}")
                return earliest_commit

            logger.error(f"No commits found at all in {project_path}")
            return None

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout finding target commit for {project_path}")
            return None
        except Exception as e:
            logger.error(f"Error finding target commit for {project_path}: {e}")
            return None
        finally:
            os.chdir(original_cwd)

    def _checkout_target_commit(self, project_path: str, target_commit: str) -> bool:
        """Checkout the target commit"""
        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)

            result = subprocess.run(['git', 'checkout', target_commit],
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                logger.info(f"Successfully checked out {target_commit[:8]} in {project_path}")
                return True
            else:
                logger.error(f"Failed to checkout {target_commit} in {project_path}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout checking out {target_commit} in {project_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking out {target_commit} in {project_path}: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    def run_analysis(self) -> Dict[str, Any]:
        """Run complete analysis on all discovered projects"""
        logger.info("Starting multi-project analysis...")

        # Discover projects
        root_paths = self.config.get('projects', {}).get('root_directories', ['.'])
        self.projects = self.discover_projects(root_paths)

        if not self.projects:
            logger.warning("No projects found to analyze")
            return {}

        # Analyze each project
        results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'time_period': {
                'start': self.config.get('time_analysis', {}).get('start_date', ''),
                'end': self.config.get('time_analysis', {}).get('end_date', '')
            },
            'projects': [],
            'totals': {
                'projects_analyzed': len(self.projects),
                'total_loc': 0,
                'source_loc': 0,
                'comment_loc': 0,
                'blank_loc': 0
            },
            'changes': {
                'lines_added': 0,
                'lines_removed': 0,
                'lines_modified': 0,
                'net_change': 0,
                'total_commits': 0,
                'total_files_changed': 0,
                'all_contributors': set()
            },
            'languages': {},
            'commits': []
        }

        start_date = self.config.get('time_analysis', {}).get('start_date', '')
        end_date = self.config.get('time_analysis', {}).get('end_date', '')

        # Git checkout configuration
        checkout_enabled = self.config.get('git', {}).get('checkout_target_date', True)
        preserve_working_dir = self.config.get('git', {}).get('preserve_working_directory', True)

        if checkout_enabled and end_date:
            logger.info(f"Historical checkout enabled - will analyze LOC at state matching {end_date}")
        elif not end_date:
            logger.warning("No end date specified - LOC analysis will use current repository state")
        else:
            logger.info("Historical checkout disabled - LOC analysis will use current repository state")

        for project in self.projects:
            logger.info(f"Processing project: {project.name}")

            git_state = None
            checkout_performed = False

            try:
                # Handle git checkout for historical accuracy if enabled and project is git repo
                if checkout_enabled and project.is_git_repo and end_date:
                    logger.info(f"Preparing historical checkout for {project.name} to date {end_date}")

                    # Backup current git state
                    git_state = self._get_git_state(project.path)
                    if not git_state:
                        logger.warning(f"Could not get git state for {project.name}, skipping checkout")
                    else:
                        # Stash uncommitted changes if needed
                        if preserve_working_dir and not git_state['working_directory_clean']:
                            if self._stash_changes(project.path):
                                git_state['has_stash'] = True
                            else:
                                logger.warning(f"Could not stash changes for {project.name}, skipping checkout")
                                git_state = None

                        if git_state:
                            # Find and checkout target commit
                            target_commit = self._find_target_commit(project.path, end_date)
                            if target_commit:
                                if self._checkout_target_commit(project.path, target_commit):
                                    checkout_performed = True
                                    logger.info(f"Successfully checked out historical state for {project.name}")
                                else:
                                    logger.warning(f"Failed to checkout target commit for {project.name}")
                            else:
                                logger.warning(f"Could not find target commit for {project.name}")

                # Analyze current LOC (now on historical commit if checkout was performed)
                loc_stats = self.analyze_current_loc(project)

                # Analyze git changes (this always uses the time range regardless of checkout)
                change_stats = self.analyze_git_changes(project, start_date, end_date)

            finally:
                # Always restore git state if we modified it
                if git_state and checkout_performed:
                    logger.info(f"Restoring original git state for {project.name}")
                    if not self._restore_git_state(git_state):
                        logger.error(f"Failed to restore git state for {project.name} - manual intervention may be required")

            project_result = {
                'info': asdict(project),
                'loc_stats': asdict(loc_stats),
                'change_stats': asdict(change_stats)
            }
            results['projects'].append(project_result)

            # Update totals
            results['totals']['total_loc'] += loc_stats.total_lines
            results['totals']['source_loc'] += loc_stats.source_lines
            results['totals']['comment_loc'] += loc_stats.comment_lines
            results['totals']['blank_loc'] += loc_stats.blank_lines

            results['changes']['lines_added'] += change_stats.lines_added
            results['changes']['lines_removed'] += change_stats.lines_removed
            results['changes']['lines_modified'] += change_stats.lines_modified
            results['changes']['net_change'] += change_stats.net_change
            results['changes']['total_commits'] += change_stats.commits_count
            results['changes']['total_files_changed'] += change_stats.files_changed
            results['changes']['all_contributors'].update(change_stats.contributors)

            # Collect commit details
            if change_stats.commits_details:
                for commit in change_stats.commits_details:
                    commit_with_project = commit.copy()
                    commit_with_project['project'] = project.name
                    commit_with_project['project_path'] = project.path
                    results['commits'].append(commit_with_project)

            # Update language totals
            for lang, lang_stats in loc_stats.languages.items():
                if lang not in results['languages']:
                    results['languages'][lang] = 0
                results['languages'][lang] += lang_stats['lines']

        # Convert contributors set to list
        results['changes']['all_contributors'] = list(results['changes']['all_contributors'])

        # Calculate language percentages
        total_lang_lines = sum(results['languages'].values())
        if total_lang_lines > 0:
            language_percentages = {}
            for lang, lines in results['languages'].items():
                percentage = (lines / total_lang_lines) * 100
                language_percentages[lang] = round(percentage, 1)
            results['language_percentages'] = language_percentages

        self.results = results
        logger.info("Analysis completed successfully")

        # Log detailed breakdown
        logger.info("=" * 60)
        logger.info("DETAILED LINES OF CODE BREAKDOWN")
        logger.info("=" * 60)
        logger.info(f"Total Lines:    {results['totals']['total_loc']:,}")
        logger.info(f"Source Code:    {results['totals']['source_loc']:,} ({results['totals']['source_loc']/results['totals']['total_loc']*100:.1f}%)")
        logger.info(f"Comments:       {results['totals']['comment_loc']:,} ({results['totals']['comment_loc']/results['totals']['total_loc']*100:.1f}%)")
        logger.info(f"Blank Lines:    {results['totals']['blank_loc']:,} ({results['totals']['blank_loc']/results['totals']['total_loc']*100:.1f}%)")
        logger.info("=" * 60)

        return results

    def save_results(self, output_dir: str):
        """Save analysis results to various formats"""
        os.makedirs(output_dir, exist_ok=True)

        output_formats = self.config.get('output', {}).get('format', ['json'])

        # Save JSON
        if 'json' in output_formats:
            json_path = os.path.join(output_dir, 'analysis_results.json')
            with open(json_path, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"Results saved to {json_path}")

        # Save CSV summary
        if 'csv' in output_formats:
            self._save_csv_summary(output_dir)

            # Generate commits CSV report if enabled
            commits_config = self.config.get('reporting', {}).get('commits_reports', {})
            if commits_config.get('generate_csv', True):
                self._save_commits_csv(output_dir)

        # Generate HTML report
        if 'html' in output_formats:
            self._generate_html_report(output_dir)

            # Generate commits HTML report if enabled
            commits_config = self.config.get('reporting', {}).get('commits_reports', {})
            if commits_config.get('generate_html', True):
                self._generate_commits_html_report(output_dir)

    def _save_csv_summary(self, output_dir: str):
        """Save project summary as CSV"""
        csv_data = []
        for project_data in self.results['projects']:
            info = project_data['info']
            loc = project_data['loc_stats']
            changes = project_data['change_stats']

            csv_data.append({
                'Project Name': info['name'],
                'Project Type': info['type'],
                'Path': info['path'],
                'Total LOC': loc['total_lines'],
                'Source LOC': loc['source_lines'],
                'Comments LOC': loc['comment_lines'],
                'Blank LOC': loc['blank_lines'],
                'Lines Added': changes['lines_added'],
                'Lines Removed': changes['lines_removed'],
                'Net Change': changes['net_change'],
                'Commits': changes['commits_count'],
                'Contributors': len(changes['contributors']),
                'Is Git Repo': info['is_git_repo']
            })

        df = pd.DataFrame(csv_data)
        csv_path = os.path.join(output_dir, 'project_summary.csv')
        df.to_csv(csv_path, index=False)
        logger.info(f"CSV summary saved to {csv_path}")

    def _save_commits_csv(self, output_dir: str):
        """Save detailed commits data as CSV"""
        commits = self.results.get('commits', [])
        if not commits:
            logger.info("No commits data to export to CSV")
            return

        csv_data = []
        for commit in commits:
            files = commit.get('files', [])
            total_added = sum(f.get('added', 0) for f in files)
            total_removed = sum(f.get('removed', 0) for f in files)

            csv_data.append({
                'Project': commit.get('project', 'Unknown'),
                'Date': commit.get('date', 'Unknown'),
                'Hash': commit.get('hash', 'Unknown'),
                'Hash Short': commit.get('hash', 'Unknown')[:8],
                'Author': commit.get('author', 'Unknown'),
                'Message': commit.get('message', 'No message'),
                'Files Changed': len(files),
                'Lines Added': total_added,
                'Lines Removed': total_removed,
                'Net Change': total_added - total_removed,
                'Project Path': commit.get('project_path', 'Unknown')
            })

        df = pd.DataFrame(csv_data)

        # Sort by date (newest first)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values('Date', ascending=False)

        csv_path = os.path.join(output_dir, 'commits_details.csv')
        df.to_csv(csv_path, index=False)
        logger.info(f"Commits CSV saved to {csv_path}")

    def _generate_html_report(self, output_dir: str):
        """Generate HTML report"""
        html_content = self._create_html_template()
        html_path = os.path.join(output_dir, 'analysis_report.html')

        with open(html_path, 'w') as f:
            f.write(html_content)
        logger.info(f"HTML report saved to {html_path}")

    def _create_html_template(self) -> str:
        """Create HTML report template with results"""
        totals = self.results['totals']
        changes = self.results['changes']
        language_percentages = self.results.get('language_percentages', {})

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Project LOC Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .language-chart {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Multi-Project Lines of Code Analysis</h1>
    <p>Generated: {self.results['analysis_timestamp']}</p>
    <p>Analysis Period: {self.results['time_period']['start']} to {self.results['time_period']['end']}</p>

    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">
            <div class="metric-value">{totals['projects_analyzed']}</div>
            <div class="metric-label">Projects</div>
        </div>
        <div class="metric">
            <div class="metric-value">{totals['total_loc']:,}</div>
            <div class="metric-label">Total LOC</div>
        </div>
        <div class="metric">
            <div class="metric-value">{totals['source_loc']:,}</div>
            <div class="metric-label">Source Code</div>
        </div>
        <div class="metric">
            <div class="metric-value">{totals['comment_loc']:,}</div>
            <div class="metric-label">Comments</div>
        </div>
        <div class="metric">
            <div class="metric-value">{totals['blank_loc']:,}</div>
            <div class="metric-label">Blank Lines</div>
        </div>
        <div class="metric">
            <div class="metric-value">{changes['net_change']:,}</div>
            <div class="metric-label">Net Change</div>
        </div>
        <div class="metric">
            <div class="metric-value">{changes['total_commits']}</div>
            <div class="metric-label">Total Commits</div>
        </div>
    </div>

    <h2>Language Distribution</h2>
    <div class="language-chart">
        <table>
            <tr><th>Language</th><th>Percentage</th><th>Lines</th></tr>
"""

        for lang, percentage in sorted(language_percentages.items(), key=lambda x: x[1], reverse=True):
            lines = self.results['languages'].get(lang, 0)
            html += f"            <tr><td>{lang}</td><td>{percentage}%</td><td>{lines:,}</td></tr>\n"

        html += """        </table>
    </div>

    <h2>Project Details</h2>
    <table>
        <tr>
            <th>Project</th>
            <th>Type</th>
            <th>Total LOC</th>
            <th>Source</th>
            <th>Comments</th>
            <th>Blanks</th>
            <th>Changes (+/-)</th>
            <th>Commits</th>
        </tr>
"""

        for project_data in self.results['projects']:
            info = project_data['info']
            loc = project_data['loc_stats']
            changes = project_data['change_stats']

            html += f"""        <tr>
            <td>{info['name']}</td>
            <td>{info['type']}</td>
            <td>{loc['total_lines']:,}</td>
            <td>{loc['source_lines']:,}</td>
            <td>{loc['comment_lines']:,}</td>
            <td>{loc['blank_lines']:,}</td>
            <td>+{changes['lines_added']:,}/-{changes['lines_removed']:,}</td>
            <td>{changes['commits_count']}</td>
        </tr>
"""

        html += """    </table>
</body>
</html>"""

        return html

    def _generate_commits_html_report(self, output_dir: str):
        """Generate HTML report for commits details"""
        html_content = self._create_commits_html_template()
        html_path = os.path.join(output_dir, 'commits_report.html')

        with open(html_path, 'w') as f:
            f.write(html_content)
        logger.info(f"Commits HTML report saved to {html_path}")

    def _create_commits_html_template(self) -> str:
        """Create HTML template for commits report"""
        commits = self.results.get('commits', [])

        # Get configuration for commits reporting
        commits_config = self.config.get('reporting', {}).get('commits_reports', {})
        max_message_length = commits_config.get('max_commit_message_length', 100)
        max_files_display = commits_config.get('max_files_per_commit_display', 5)

        # Sort commits by date (newest first)
        commits_sorted = sorted(commits, key=lambda x: x.get('date', ''), reverse=True)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Project Commits Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .commit-hash {{ font-family: monospace; font-size: 12px; }}
        .commit-message {{ max-width: 300px; word-wrap: break-word; }}
        .project-name {{ font-weight: bold; color: #2980b9; }}
        .files-changed {{ font-size: 11px; color: #7f8c8d; }}
        .added {{ color: #27ae60; }}
        .removed {{ color: #e74c3c; }}
        .filter-section {{ margin: 20px 0; }}
        .filter-input {{ padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }}
    </style>
    <script>
        function filterTable() {{
            const projectFilter = document.getElementById('projectFilter').value.toLowerCase();
            const authorFilter = document.getElementById('authorFilter').value.toLowerCase();
            const messageFilter = document.getElementById('messageFilter').value.toLowerCase();
            const rows = document.querySelectorAll('#commitsTable tbody tr');

            rows.forEach(row => {{
                const project = row.cells[1].textContent.toLowerCase();
                const author = row.cells[3].textContent.toLowerCase();
                const message = row.cells[4].textContent.toLowerCase();

                const showRow = project.includes(projectFilter) &&
                              author.includes(authorFilter) &&
                              message.includes(messageFilter);

                row.style.display = showRow ? '' : 'none';
            }});
        }}
    </script>
</head>
<body>
    <h1>Multi-Project Commits Report</h1>
    <p>Generated: {self.results['analysis_timestamp']}</p>
    <p>Analysis Period: {self.results['time_period']['start']} to {self.results['time_period']['end']}</p>

    <div class="summary">
        <h2>Commits Summary</h2>
        <div class="metric">
            <div class="metric-value">{len(commits):,}</div>
            <div class="metric-label">Total Commits</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(set(c.get('author', 'Unknown') for c in commits))}</div>
            <div class="metric-label">Contributors</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(set(c.get('project', 'Unknown') for c in commits))}</div>
            <div class="metric-label">Projects</div>
        </div>
        <div class="metric">
            <div class="metric-value">{sum(sum(f.get('added', 0) for f in c.get('files', [])) for c in commits):,}</div>
            <div class="metric-label">Lines Added</div>
        </div>
        <div class="metric">
            <div class="metric-value">{sum(sum(f.get('removed', 0) for f in c.get('files', [])) for c in commits):,}</div>
            <div class="metric-label">Lines Removed</div>
        </div>
    </div>

    <div class="filter-section">
        <h3>Filter Commits</h3>
        <input type="text" id="projectFilter" class="filter-input" placeholder="Filter by project..." onkeyup="filterTable()">
        <input type="text" id="authorFilter" class="filter-input" placeholder="Filter by author..." onkeyup="filterTable()">
        <input type="text" id="messageFilter" class="filter-input" placeholder="Filter by commit message..." onkeyup="filterTable()">
    </div>

    <h2>Detailed Commits ({len(commits_sorted)} commits)</h2>
    <table id="commitsTable">
        <thead>
            <tr>
                <th>Date</th>
                <th>Project</th>
                <th>Hash</th>
                <th>Author</th>
                <th>Message</th>
                <th>Files Changed</th>
                <th>Changes</th>
            </tr>
        </thead>
        <tbody>"""

        for commit in commits_sorted:
            hash_short = commit.get('hash', '')[:8]
            project_name = commit.get('project', 'Unknown')
            date = commit.get('date', 'Unknown')
            author = commit.get('author', 'Unknown')
            original_message = commit.get('message', 'No message')
            message = original_message[:max_message_length] + ('...' if len(original_message) > max_message_length else '')

            files = commit.get('files', [])
            files_count = len(files)
            total_added = sum(f.get('added', 0) for f in files)
            total_removed = sum(f.get('removed', 0) for f in files)

            files_list = []
            for f in files[:max_files_display]:  # Show first N files based on config
                file_name = f.get('file', 'Unknown')
                added = f.get('added', 0)
                removed = f.get('removed', 0)
                files_list.append(f"{file_name} (+{added}/-{removed})")
            if len(files) > max_files_display:
                files_list.append(f"... and {len(files) - max_files_display} more files")

            files_text = "<br>".join(files_list)

            html += f"""
            <tr>
                <td>{date}</td>
                <td class="project-name">{project_name}</td>
                <td class="commit-hash">{hash_short}</td>
                <td>{author}</td>
                <td class="commit-message">{message}</td>
                <td class="files-changed">{files_count} files<br><small>{files_text}</small></td>
                <td><span class="added">+{total_added}</span> / <span class="removed">-{total_removed}</span></td>
            </tr>"""

        html += """
        </tbody>
    </table>
</body>
</html>"""

        return html


def main():
    parser = argparse.ArgumentParser(description='Multi-Project Lines of Code Analyzer')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--output', default='./output', help='Output directory for results')
    args = parser.parse_args()

    analyzer = MultiProjectAnalyzer(args.config)
    results = analyzer.run_analysis()

    if results:
        analyzer.save_results(args.output)
        print(f"\nAnalysis completed successfully!")
        print(f"Projects analyzed: {results['totals']['projects_analyzed']}")
        print()
        print("Lines of Code Breakdown:")
        print(f"  Total LOC:     {results['totals']['total_loc']:,}")
        print(f"  Source Code:   {results['totals']['source_loc']:,} ({results['totals']['source_loc']/results['totals']['total_loc']*100:.1f}%)")
        print(f"  Comments:      {results['totals']['comment_loc']:,} ({results['totals']['comment_loc']/results['totals']['total_loc']*100:.1f}%)")
        print(f"  Blank Lines:   {results['totals']['blank_loc']:,} ({results['totals']['blank_loc']/results['totals']['total_loc']*100:.1f}%)")
        print()
        print(f"Git Changes: {results['changes']['net_change']:,} net lines ({results['changes']['total_commits']} commits)")
        print(f"Results saved to: {args.output}")
    else:
        print("No results generated.")


if __name__ == '__main__':
    main()