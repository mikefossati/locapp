# Multi-Project Lines of Code Analysis Tool

A simple tool for analyzing lines of code and tracking git changes across multiple projects within configurable time periods.

## Features

- **Project Discovery**: Automatically discovers projects by scanning for markers (.git, package.json, pom.xml, etc.)
- **LOC Analysis**: Counts total, source, comment, and blank lines using `cloc`
- **Historical Accuracy**: Analyzes LOC at the exact state matching your end date
- **Change Tracking**: Analyzes git history for additions, deletions, and modifications
- **Language Detection**: Identifies programming languages and calculates distribution
- **Multiple Output Formats**: JSON, CSV, and HTML reports
- **Detailed Commits Report**: Interactive HTML and CSV reports with commit-level details
- **Author Filtering**: Exclude automated commits (bots, CI/CD systems)

## Requirements

- Python 3.7+
- `cloc` (Count Lines of Code tool)
- Git (for change analysis)

### Install Dependencies

```bash
# Install Python dependencies
pip3 install -r scripts/requirements.txt

# Install cloc
brew install cloc          # macOS
sudo apt-get install cloc  # Ubuntu/Debian
```

## Quick Start

1. **Configure Analysis** - Copy `config/analysis_example.yaml` to `config/analysis.yaml` and edit:
   ```yaml
   projects:
     root_directories:
       - "/path/to/your/projects"

   time_analysis:
     start_date: "2024-01-01"
     end_date: "2025-09-18"
   ```

2. **Run Analysis**:
   ```bash
   python3 scripts/multi_project_analyzer.py --config config/analysis.yaml --output output/
   ```

3. **View Results**:
   - **Main Report**: `output/analysis_report.html`
   - **Commits Report**: `output/commits_report.html` (interactive with filtering)
   - **CSV Data**: `output/project_summary.csv` and `output/commits_details.csv`
   - **Raw JSON**: `output/analysis_results.json`

## Configuration

### Basic Settings (`config/analysis.yaml`)

```yaml
projects:
  root_directories:
    - "/path/to/your/projects"

time_analysis:
  start_date: "2024-01-01"
  end_date: "2025-09-18"

filters:
  exclude_directories:
    - "node_modules"
    - "target"
    - "build"
    - ".git"
  exclude_files:
    - "*.min.js"
    - "*.log"
    - "package-lock.json"

output:
  format: ["json", "csv", "html"]

git:
  # Historical checkout - analyzes LOC at end_date state for accuracy
  checkout_target_date: true
  preserve_working_directory: true

  # Exclude automated commits
  exclude_authors:
    - "GitHub Actions"
    - "github-actions[bot]"
    - "dependabot[bot]"
    - "Jenkins"
    - "bot"
```

## Key Features Explained

### Historical Accuracy
The tool automatically checks out each git project to the commit that matches your `end_date` before analyzing LOC. This ensures your analysis reflects the actual codebase state at that point in time, not the current HEAD.

### Commits Report
- Interactive HTML table with filtering by project, author, and message
- Shows detailed file changes per commit
- CSV export for further analysis
- Respects author exclusion rules

### Project Detection
Automatically detects projects by these markers:
- `.git` → Git repository
- `package.json` → Node.js
- `pom.xml` → Java Maven
- `build.gradle` → Java Gradle
- `pyproject.toml` → Python

## Output Structure

### Summary Metrics
- Total projects analyzed
- Lines of code breakdown (source/comments/blank)
- Git changes (additions, deletions, net change)
- Language distribution percentages

### Per-Project Details
- LOC statistics by language
- Git change statistics for time period
- Contributor information

## Troubleshooting

**Dependencies missing**:
```bash
pip3 install -r scripts/requirements.txt
```

**cloc not found**:
```bash
brew install cloc  # macOS
sudo apt-get install cloc  # Ubuntu/Debian
```

**Git permission issues**:
- Ensure read access to all repositories
- Check SSH keys for remote repositories

**Large repository timeouts**:
- Add directories to `exclude_directories` filter
- The tool has built-in 5-minute timeouts for git operations

## License

MIT License - see LICENSE file for details.