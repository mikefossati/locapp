#!/bin/bash

# Multi-Project LOC Analysis Runner
# Usage: ./run_analysis.sh [config_file] [output_directory]

set -e

# Default values
CONFIG_FILE="config/analysis.yaml"
OUTPUT_DIR="output"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --config FILE    Configuration file (default: config/analysis.yaml)"
            echo "  -o, --output DIR     Output directory (default: output)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Prerequisites:"
            echo "  • Install Python dependencies: pip3 install -r scripts/requirements.txt"
            echo "  • Install cloc: brew install cloc (macOS) or apt-get install cloc (Ubuntu)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found"
    echo "Please create a configuration file or specify a different path with -c"
    exit 1
fi

# Check if cloc is installed
if ! command -v cloc &> /dev/null; then
    echo "Error: 'cloc' is not installed"
    echo "Please install cloc:"
    echo "  Ubuntu/Debian: sudo apt-get install cloc"
    echo "  macOS: brew install cloc"
    echo "  Other: Visit https://github.com/AlDanial/cloc"
    exit 1
fi

# Check if Python dependencies are available
echo "Checking Python dependencies..."
if ! python3 -c "import pandas, yaml, matplotlib, seaborn, plotly" &> /dev/null; then
    echo "Error: Required Python dependencies are missing"
    echo "Please install them with: pip3 install -r scripts/requirements.txt"
    echo ""
    echo "If you don't have pip3, install it first:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-pip"
    echo "  macOS: python3 -m ensurepip --upgrade"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "Starting multi-project LOC analysis..."
echo "Configuration: $CONFIG_FILE"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Run the analysis
python3 scripts/multi_project_analyzer.py --config "$CONFIG_FILE" --output "$OUTPUT_DIR"

# Check if analysis was successful
if [[ $? -eq 0 ]]; then
    echo ""
    echo "Analysis completed successfully!"
    echo "Results available in: $OUTPUT_DIR"

    # List output files
    if [[ -d "$OUTPUT_DIR" ]]; then
        echo ""
        echo "Generated files:"
        ls -la "$OUTPUT_DIR"

        # Open HTML report if it exists and we're on macOS
        if [[ -f "$OUTPUT_DIR/analysis_report.html" ]] && [[ "$OSTYPE" == "darwin"* ]]; then
            echo ""
            read -p "Open HTML report in browser? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                open "$OUTPUT_DIR/analysis_report.html"
            fi
        fi
    fi
else
    echo "Analysis failed. Check the error messages above."
    exit 1
fi