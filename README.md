# Multi-Project Lines of Code Analysis Tool

A comprehensive tool for analyzing lines of code and tracking changes across multiple projects within configurable time periods.

## Features

- **Project Discovery**: Automatically discovers projects by scanning for markers (.git, package.json, pom.xml, etc.)
- **LOC Analysis**: Counts total, source, comment, and blank lines using `cloc`
- **Change Tracking**: Analyzes git history for additions, deletions, and modifications
- **Language Detection**: Identifies programming languages and calculates distribution
- **Multiple Output Formats**: JSON, CSV, and HTML reports
- **Interactive Visualizations**: Charts and dashboards for data exploration
- **Configurable Filtering**: Exclude directories and files based on patterns
- **Parallel Processing**: Efficient analysis of large codebases

## Requirements

### System Dependencies
- Python 3.7+
- `cloc` (Count Lines of Code tool)
- Git (for change analysis)

### Python Dependencies
```bash
pip3 install -r scripts/requirements.txt
```

### Install cloc
```bash
# Ubuntu/Debian
sudo apt-get install cloc

# macOS
brew install cloc

# Other systems: https://github.com/AlDanial/cloc
```

## Quick Start

1. **Install Dependencies**
   ```bash
   # Install Python dependencies
   pip3 install -r scripts/requirements.txt

   # Install cloc
   brew install cloc  # macOS
   # or apt-get install cloc  # Ubuntu/Debian
   ```

2. **Configure Analysis**
   Edit `config/analysis.yaml` to specify:
   - Root directories to scan
   - Time period for change analysis
   - File/directory exclusion patterns

3. **Run Analysis**
   ```bash
   ./scripts/run_analysis.sh
   ```

4. **View Results**
   - JSON: `output/analysis_results.json`
   - CSV: `output/project_summary.csv`
   - HTML Report: `output/analysis_report.html`

## Configuration

### Basic Configuration (config/analysis.yaml)

```yaml
projects:
  root_directories:
    - "/path/to/your/projects"
    - "."  # Current directory

time_analysis:
  start_date: "2024-01-01"
  end_date: "2024-09-18"

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
```

## Usage Examples

### Basic Analysis
```bash
# Use default configuration
./scripts/run_analysis.sh

# Specify custom config and output directory
./scripts/run_analysis.sh -c custom_config.yaml -o results/
```

### Direct Python Usage
```bash
# Run analyzer directly
python3 scripts/multi_project_analyzer.py --config config/analysis.yaml --output output/

# Create visualizations
python3 scripts/visualizer.py --results output/analysis_results.json
```

### Programmatic Usage
```python
import sys
sys.path.append('scripts')
from multi_project_analyzer import MultiProjectAnalyzer

analyzer = MultiProjectAnalyzer('config/analysis.yaml')
results = analyzer.run_analysis()
analyzer.save_results('output/')
```

## Output Structure

### JSON Results
```json
{
  "analysis_timestamp": "2024-09-18T10:30:00Z",
  "time_period": {
    "start": "2024-01-01",
    "end": "2024-09-18"
  },
  "totals": {
    "projects_analyzed": 25,
    "total_loc": 2847291,
    "source_loc": 2103847,
    "comment_loc": 485923,
    "blank_loc": 257521
  },
  "changes": {
    "lines_added": 485923,
    "lines_removed": 267834,
    "net_change": 218089,
    "total_commits": 1247,
    "all_contributors": ["dev1", "dev2", "..."]
  },
  "language_percentages": {
    "JavaScript": 35.2,
    "Python": 28.7,
    "Java": 18.3
  },
  "projects": [...]
}
```

### Project Details
Each project includes:
- Basic info (name, path, type, size)
- LOC statistics by language
- Git change statistics
- Contributor information

## Visualizations

The tool generates several types of visualizations:

1. **Language Distribution**: Pie charts showing code distribution by programming language
2. **Project Comparison**: Bar charts comparing LOC across projects
3. **Change Analysis**: Visualizations of code additions, deletions, and modifications
4. **Interactive Dashboard**: Plotly-based interactive charts

## Advanced Configuration

### Performance Settings
```yaml
performance:
  parallel_analysis: true
  max_workers: 4
  timeout_seconds: 300
  cache_results: true
```

### Language Filtering
```yaml
languages:
  include:
    - "Python"
    - "JavaScript"
    - "TypeScript"
    - "Java"
```

### Git Author Exclusion
Exclude commits from automated systems and bots:
```yaml
git:
  exclude_authors:
    - "Jenkins"
    - "jenkins"
    - "GitHub Actions"
    - "github-actions[bot]"
    - "dependabot[bot]"
    - "renovate[bot]"
    - "bot"
    - "automation"
    - "CI/CD"
    - "deploy"
```

This feature helps filter out non-human commits from:
- CI/CD systems (Jenkins, GitHub Actions, etc.)
- Dependency update bots (Dependabot, Renovate)
- Automated deployment systems
- Any other automated commit authors

The filtering is case-insensitive and uses substring matching.

### Threshold Alerts
```yaml
thresholds:
  large_change_lines: 10000
  high_activity_commits: 100
  significant_growth_percent: 50
```

## Project Detection

The tool automatically detects projects based on these markers:

| Marker | Project Type |
|--------|-------------|
| `.git` | Git repository |
| `package.json` | Node.js |
| `pom.xml` | Java Maven |
| `build.gradle` | Java Gradle |
| `Cargo.toml` | Rust |
| `setup.py` | Python setuptools |
| `pyproject.toml` | Python modern |
| `go.mod` | Go |
| `composer.json` | PHP |
| `Gemfile` | Ruby |
| `CMakeLists.txt` | C++ CMake |

## Troubleshooting

### Common Issues

1. **Python dependencies missing**
   ```bash
   # Install required packages
   pip3 install -r scripts/requirements.txt

   # If pip3 is not available
   sudo apt-get install python3-pip  # Ubuntu/Debian
   python3 -m ensurepip --upgrade    # macOS
   ```

2. **cloc not found**
   ```bash
   # Install cloc first
   sudo apt-get install cloc  # Ubuntu/Debian
   brew install cloc          # macOS
   ```

3. **Permission denied on git repositories**
   - Ensure you have read access to all git repositories
   - Check SSH keys for remote repositories

4. **Large repository timeouts**
   - Increase timeout in configuration
   - Use filtering to exclude large directories

5. **Memory issues with large codebases**
   - Enable parallel processing
   - Use incremental analysis mode
   - Apply aggressive filtering

### Performance Optimization

For large codebases (>10M LOC):
- Enable parallel processing
- Use file filtering extensively
- Consider incremental analysis
- Increase timeout values

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review configuration examples
- Create an issue with detailed error information