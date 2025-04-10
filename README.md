# Disk Cleaner

A fast CLI tool for analyzing disk usage on Windows. This tool scans directories to identify large files and folders, flags items that are safe to delete, and provides interactive deletion options.

## Features

- Scan directories to identify large files and folders
- Show size information in human-readable format (KB, MB, GB, etc.)
- Focus on hidden files/folders
- Set minimum size threshold for items to display
- Smart detection of common "space hog" directories
- Interactive deletion mode with confirmation prompts
- Generate CSV reports of scan results

## Installation

1. Clone this repository:
```bash
git clone https://github.com/KimutaiLawrence/diskanalyzer.git
cd diskanalyzer
```

2. Create and activate a virtual environment:
```bash
uv venv
.venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
uv pip install typer rich
```

## Usage

Basic command structure:
```bash
python disk_cleaner.py [OPTIONS]
```

### Available Options

- `--path` or `-p`: Directory to scan (default is your user directory)
- `--threshold` or `-t`: Minimum size threshold (e.g., "10MB", "1GB")
- `--top` or `-n`: Number of largest items to show
- `--only-hidden` or `-h`: Only show hidden files and folders
- `--delete` or `-d`: Enable deletion mode
- `--report` or `-r`: Generate a CSV report file

### Example Commands

```bash
# Scan Downloads folder for files larger than 10MB
python disk_cleaner.py --path "C:\Users\ADMIN\Downloads" --threshold "10MB"

# Show top 5 largest items in Documents
python disk_cleaner.py --path "C:\Users\ADMIN\Documents" --top 5

# Enable deletion mode for cleaning up Downloads
python disk_cleaner.py --path "C:\Users\ADMIN\Downloads" --delete

# Generate a report of large files
python disk_cleaner.py --path "C:\Users\ADMIN" --threshold "100MB" --report "disk_report.csv"
```

### Output Information

The tool displays:
- A table of the largest items found
- Whether each item is safe to delete
- Total space used
- Percentage of space represented by the displayed items

## Features

- **Smart Detection**: Identifies common "space hog" directories like:
  - `node_modules`
  - `.cache`
  - `.venv`
  - `temp` folders
  - And more...

- **Safety Features**:
  - Protects critical system folders
  - Provides reasons for why items are safe/unsafe to delete
  - Interactive confirmation for deletions

- **Reporting**:
  - Generate CSV reports of scan results
  - Detailed information about each item found

## Contributing

Feel free to submit issues and enhancement requests!