# Disk Cleaner

A fast Python CLI tool for Windows that analyzes disk usage and helps clean up storage space.

## Overview

Disk Cleaner scans directories on your system to identify large files and folders that are consuming storage space. It helps you find potential space hogs like cache directories, package repositories, and temporary files while protecting important system folders.

This tool is particularly useful when you're running low on disk space and need to quickly identify where your storage is being used.

## Features

- Fast recursive directory scanning with minimal system impact
- Identification of the largest files and folders by size
- Detection of common space-consuming directories (node_modules, .conda, etc.)
- Smart flagging of items that are safe to delete
- Protection against accidental deletion of system-critical folders
- Human-readable file sizes (KB, MB, GB)
- Interactive deletion mode with confirmation prompts
- CSV report generation for further analysis

## Requirements

- Python 3.6 or higher
- Required packages: typer, rich

## Installation

1. Clone or download this repository to your local machine.
2. Install the required packages:

```
pip install typer rich
```

## Usage

Basic usage:

```
python disk_cleaner.py --path "C:/Users/YourName"
```

### Command Line Options

- `--path`, `-p`: Target directory to scan [default: current user home directory]
- `--only-hidden`, `-h`: Only show hidden files and folders
- `--threshold`, `-t`: Minimum size threshold to display (e.g., "100KB", "10MB", "1GB") [default: "1MB"]
- `--top`, `-n`: Show top N largest items [default: 20]
- `--delete`, `-d`: Enable interactive deletion mode
- `--report`, `-r`: Generate a CSV report (provide a filename)

### Examples

Scan your Downloads folder for files over 100MB:
```
python disk_cleaner.py --path "C:/Users/YourName/Downloads" --threshold "100MB"
```

Find the top 10 largest items:
```
python disk_cleaner.py --path "C:/Program Files" --top 10
```

Generate a report of all items over 1GB:
```
python disk_cleaner.py --path "D:/" --threshold "1GB" --report "large_files.csv"
```

Interactive deletion mode:
```
python disk_cleaner.py --path "C:/Users/YourName/AppData/Local/Temp" --delete
```

## Safety Features

Disk Cleaner includes several safety mechanisms:

- System-critical folders are marked as protected
- Clear warnings before deleting any items
- Additional confirmation for potentially risky deletions
- Auto-detection of administrator privileges where needed

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Feel free to submit pull requests or open issues to improve the functionality.