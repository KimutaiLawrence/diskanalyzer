#!/usr/bin/env python3
"""
Disk Cleaner - A fast CLI tool for analyzing disk usage on Windows.

This tool scans directories to identify large files and folders, flags items that
are safe to delete, and provides interactive deletion options.
"""

import os
import sys
import pathlib
import shutil
import ctypes
from typing import Dict, List, Tuple, Set, Optional, Union
from datetime import datetime
import getpass
import time

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Confirm
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text

# Initialize typer app and rich console
app = typer.Typer(help="Fast disk usage analyzer and cleanup tool for Windows")
console = Console()

# Define constants
DEFAULT_TOP_COUNT = 20
DEFAULT_PATH = f"C:/Users/{getpass.getuser()}"
DEFAULT_THRESHOLD = 1024 * 1024  # 1MB in bytes

# Known space hogs (directories that often consume significant space)
SPACE_HOGS = {
    "node_modules": "NPM packages (usually safe to delete if not actively developing)",
    ".conda": "Conda environments (safe if not needed)",
    ".venv": "Python virtual environments (safe if not needed)",
    ".cache": "Cache files (usually safe to delete)",
    ".npm": "NPM cache (safe to delete)",
    "temp": "Temporary files (safe to delete)",
    "tmp": "Temporary files (safe to delete)",
    ".git": "Git repositories (contains version history, be careful)",
    "build": "Build artifacts (usually safe if not actively building)",
    "dist": "Distribution files (usually safe if not needed)",
    "logs": "Log files (usually safe to delete old logs)",
    ".nuget": "NuGet package cache (safe if not actively developing)",
    ".gradle": "Gradle build system cache (safe if not actively developing)",
    ".m2": "Maven repository (safe if not actively developing)",
    "AppData": "Application data (may contain important settings)",
}

# System critical folders that should not be deleted
PROTECTED_FOLDERS = {
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
    "System32", "System Volume Information", "$Recycle.Bin", "$WINDOWS.~BT",
    "pagefile.sys", "hiberfil.sys", "swapfile.sys", "bootmgr"
}

def is_admin() -> bool:
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def run_as_admin():
    """Restart the script with administrator privileges."""
    if sys.argv[0].endswith('.py'):
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{item}"' for item in sys.argv[1:]])
        # Use ShellExecuteW to elevate privileges
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)
    else:
        # If running as compiled executable
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, ' '.join(sys.argv), None, 1)
        sys.exit(0)

def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format (KB, MB, GB, etc.)."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f}{size_names[i]}"

def is_path_protected(path: str) -> bool:
    """Check if a path contains or is a protected system folder."""
    path_parts = pathlib.Path(path).parts
    
    # Check if any part of the path matches a protected folder name
    for part in path_parts:
        if part in PROTECTED_FOLDERS:
            return True
    
    return False

def is_safe_to_delete(path: str) -> Tuple[bool, str]:
    """
    Determine if a path is likely safe to delete and provide a reason.
    
    Returns:
        Tuple[bool, str]: (is_safe, reason)
    """
    if is_path_protected(path):
        return False, "System protected"
    
    path_obj = pathlib.Path(path)
    name = path_obj.name
    
    # Check if it matches any known space hog patterns
    for pattern, description in SPACE_HOGS.items():
        if name == pattern or name.lower() == pattern.lower():
            if "safe" in description.lower():
                return True, description
            else:
                return False, description
    
    # Default to not safe if we can't determine
    return False, "Unknown"

def get_long_path_name(path: str) -> str:
    """Handle Windows long paths by prefixing with \\?\\ if needed."""
    if path.startswith("\\\\?\\"):
        return path
    
    abs_path = os.path.abspath(path)
    if len(abs_path) >= 260:  # MAX_PATH is 260 in Windows
        return f"\\\\?\\{abs_path}"
    return abs_path

def scan_directory(
    path: str, 
    only_hidden: bool = False,
    threshold: int = 0
) -> List[Tuple[str, int, bool, bool, str]]:
    """
    Scan a directory recursively and collect size information.
    
    Args:
        path: Directory path to scan
        only_hidden: If True, only include hidden files/folders
        threshold: Minimum size threshold in bytes
        
    Returns:
        List of tuples (path, size, is_file, is_safe, reason)
    """
    results = []
    path = get_long_path_name(path)
    
    try:
        # For files, just get their size directly
        if os.path.isfile(path):
            try:
                size = os.path.getsize(path)
                is_safe, reason = is_safe_to_delete(path)
                if size >= threshold:
                    is_hidden = bool(os.stat(path).st_file_attributes & 2) if os.name == 'nt' else False
                    if not only_hidden or is_hidden:
                        results.append((path, size, True, is_safe, reason))
                return results
            except (PermissionError, FileNotFoundError):
                return results
        
        # For directories, scan recursively
        total_size = 0
        items_to_scan = []
        
        try:
            for entry in os.scandir(path):
                try:
                    is_hidden = bool(entry.stat().st_file_attributes & 2) if os.name == 'nt' else entry.name.startswith('.')
                    
                    if only_hidden and not is_hidden:
                        continue
                    
                    if entry.is_file():
                        file_size = entry.stat().st_size
                        total_size += file_size
                        
                        if file_size >= threshold:
                            is_safe, reason = is_safe_to_delete(entry.path)
                            results.append((entry.path, file_size, True, is_safe, reason))
                    else:
                        items_to_scan.append(entry.path)
                except (PermissionError, FileNotFoundError):
                    continue
        except (PermissionError, FileNotFoundError):
            pass
        
        # Process subdirectories
        for item_path in items_to_scan:
            try:
                # Recursive call to scan subdirectories
                sub_results = scan_directory(item_path, only_hidden, threshold)
                
                # Sum up the size of all items in the subdirectory
                sub_size = sum(size for _, size, _, _, _ in sub_results)
                
                # Add subdirectory results to our list
                results.extend(sub_results)
                
                # Add directory itself if it meets the threshold
                if sub_size >= threshold:
                    is_safe, reason = is_safe_to_delete(item_path)
                    results.append((item_path, sub_size, False, is_safe, reason))
                
                total_size += sub_size
            except (PermissionError, FileNotFoundError):
                continue
        
    except Exception as e:
        console.print(f"[bold red]Error scanning {path}: {str(e)}[/bold red]")
    
    return results

def delete_item(path: str) -> bool:
    """
    Delete a file or directory with proper error handling.
    
    Args:
        path: Path to delete
        
    Returns:
        bool: True if deletion was successful
    """
    try:
        path = get_long_path_name(path)
        
        if os.path.isfile(path):
            os.remove(path)
            return True
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return True
        return False
    except PermissionError:
        console.print(f"[bold red]Permission denied when trying to delete {path}[/bold red]")
        if not is_admin():
            if Confirm.ask("Would you like to retry with administrator privileges?"):
                run_as_admin()
        return False
    except Exception as e:
        console.print(f"[bold red]Error deleting {path}: {str(e)}[/bold red]")
        return False

def generate_report(results: List[Tuple[str, int, bool, bool, str]], output_file: str):
    """
    Generate a report file with scan results.
    
    Args:
        results: List of scan results
        output_file: Path to save the report
    """
    try:
        with open(output_file, 'w') as f:
            f.write("Disk Cleaner Scan Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("Path,Size,Type,Safe To Delete,Reason\n")
            for path, size, is_file, is_safe, reason in results:
                f.write(f'"{path}",{size},{"File" if is_file else "Directory"},{is_safe},"{reason}"\n')
        
        console.print(f"[green]Report saved to: {output_file}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error generating report: {str(e)}[/bold red]")

@app.command()
def analyze(
    path: str = typer.Option(DEFAULT_PATH, "--path", "-p", help="Directory path to scan"),
    only_hidden: bool = typer.Option(False, "--only-hidden", "-h", help="Only show hidden files and folders"),
    threshold: str = typer.Option("1MB", "--threshold", "-t", help="Minimum size threshold (e.g., 100KB, 10MB, 1GB)"),
    top: int = typer.Option(DEFAULT_TOP_COUNT, "--top", "-n", help="Show top N largest items"),
    delete: bool = typer.Option(False, "--delete", "-d", help="Enable deletion mode"),
    report: str = typer.Option("", "--report", "-r", help="Generate a CSV report file")
):
    """
    Analyze disk usage in the specified directory and display the largest items.
    """
    # Validate and convert path
    if not os.path.exists(path):
        console.print(f"[bold red]Error: Path '{path}' does not exist.[/bold red]")
        raise typer.Exit(1)
    
    # Parse threshold size
    threshold_bytes = DEFAULT_THRESHOLD
    if threshold:
        units = {'b': 1, 'kb': 1024, 'mb': 1024**2, 'gb': 1024**3, 'tb': 1024**4}
        threshold = threshold.lower()
        
        # Extract numeric value and unit
        if threshold[-2:] in units:
            threshold_value = float(threshold[:-2])
            threshold_unit = threshold[-2:]
        elif threshold[-1:] in [k[0] for k in units.keys()]:
            threshold_value = float(threshold[:-1])
            threshold_unit = [k for k in units.keys() if k.startswith(threshold[-1:])][0]
        else:
            # Assume bytes if no unit specified
            threshold_value = float(threshold)
            threshold_unit = 'b'
        
        threshold_bytes = int(threshold_value * units[threshold_unit])
    
    # Show scan info
    console.print(Panel(
        f"[bold]Disk Cleaner Scan[/bold]\n"
        f"Path: [cyan]{path}[/cyan]\n"
        f"Threshold: [cyan]{format_size(threshold_bytes)}[/cyan]\n"
        f"Mode: [cyan]{'Hidden Only' if only_hidden else 'All Items'}[/cyan]",
        title="Scan Configuration",
        border_style="blue"
    ))
    
    # Use Progress to show scanning progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[bold green]{task.fields[items]} items scanned"),
        console=console
    ) as progress:
        scan_task = progress.add_task("[bold]Scanning directories...", items=0)
        
        # Counter to update progress
        items_scanned = 0
        
        def update_progress():
            nonlocal items_scanned
            items_scanned += 1
            if items_scanned % 100 == 0:  # Update progress every 100 items
                progress.update(scan_task, items=items_scanned)
        
        # Modified scan function that updates progress
        def scan_with_progress(path, only_hidden, threshold):
            results = []
            path = get_long_path_name(path)
            
            try:
                if os.path.isfile(path):
                    update_progress()
                    try:
                        size = os.path.getsize(path)
                        is_safe, reason = is_safe_to_delete(path)
                        if size >= threshold:
                            is_hidden = bool(os.stat(path).st_file_attributes & 2) if os.name == 'nt' else False
                            if not only_hidden or is_hidden:
                                results.append((path, size, True, is_safe, reason))
                        return results
                    except (PermissionError, FileNotFoundError):
                        return results
                
                total_size = 0
                items_to_scan = []
                
                try:
                    for entry in os.scandir(path):
                        update_progress()
                        try:
                            is_hidden = bool(entry.stat().st_file_attributes & 2) if os.name == 'nt' else entry.name.startswith('.')
                            
                            if only_hidden and not is_hidden:
                                continue
                            
                            if entry.is_file():
                                file_size = entry.stat().st_size
                                total_size += file_size
                                
                                if file_size >= threshold:
                                    is_safe, reason = is_safe_to_delete(entry.path)
                                    results.append((entry.path, file_size, True, is_safe, reason))
                            else:
                                items_to_scan.append(entry.path)
                        except (PermissionError, FileNotFoundError):
                            continue
                except (PermissionError, FileNotFoundError):
                    pass
                
                for item_path in items_to_scan:
                    try:
                        sub_results = scan_with_progress(item_path, only_hidden, threshold)
                        sub_size = sum(size for _, size, _, _, _ in sub_results)
                        results.extend(sub_results)
                        
                        if sub_size >= threshold:
                            is_safe, reason = is_safe_to_delete(item_path)
                            results.append((item_path, sub_size, False, is_safe, reason))
                        
                        total_size += sub_size
                    except (PermissionError, FileNotFoundError):
                        continue
                
            except Exception as e:
                console.print(f"[bold red]Error scanning {path}: {str(e)}[/bold red]")
            
            return results
        
        # Start the scan with progress tracking
        start_time = time.time()
        results = scan_with_progress(path, only_hidden, threshold_bytes)
        scan_time = time.time() - start_time
    
    # Filter out duplicate directory entries
    # (When we have both a directory and its contents, keep only the directory)
    path_dict = {}
    for result in results:
        path, size, is_file, is_safe, reason = result
        if path not in path_dict or (path in path_dict and size > path_dict[path][1]):
            path_dict[path] = result
    
    filtered_results = list(path_dict.values())
    
    # Sort by size (largest first)
    filtered_results.sort(key=lambda x: x[1], reverse=True)
    
    # Limit to top N results
    top_results = filtered_results[:top]
    
    # Display results in a table
    table = Table(title=f"Largest Items in {path} (scan time: {scan_time:.2f}s)")
    table.add_column("#", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Type", style="yellow")
    table.add_column("Safe to Delete", style="red")
    table.add_column("Notes", style="magenta")
    
    total_scan_size = sum(item[1] for item in filtered_results)
    displayed_size = sum(item[1] for item in top_results)
    
    for i, (item_path, size, is_file, is_safe, reason) in enumerate(top_results, 1):
        # Format path to be more readable (relative to scanned directory when possible)
        try:
            rel_path = os.path.relpath(item_path, path)
            display_path = rel_path if rel_path != "." else os.path.basename(item_path)
        except ValueError:  # Can happen on Windows with different drives
            display_path = item_path
        
        # If the path is too long, truncate it
        if len(display_path) > 50:
            display_path = "..." + display_path[-47:]
        
        row_style = ""
        safe_text = ""
        
        if is_safe:
            safe_text = "[green]Yes[/green]"
            row_style = "green"
        elif is_protected(item_path):
            safe_text = "[bold red]PROTECTED[/bold red]"
        else:
            safe_text = "[red]No[/red]"
        
        table.add_row(
            str(i),
            display_path,
            format_size(size),
            "File" if is_file else "Directory",
            safe_text,
            reason,
            style=row_style
        )
    
    console.print(table)
    
    # Show summary
    console.print(
        f"\n[bold]Summary:[/bold] Scanned {items_scanned} items, found {len(filtered_results)} items "
        f"above threshold, total size: [green]{format_size(total_scan_size)}[/green]"
    )
    
    # Avoid division by zero error when no items were found
    if total_scan_size > 0:
        percentage = displayed_size/total_scan_size * 100
        console.print(
            f"Displaying top {len(top_results)} items, "
            f"representing [green]{format_size(displayed_size)}[/green] "
            f"([green]{percentage:.1f}%[/green] of found space)"
        )
    else:
        console.print(
            f"Displaying top {len(top_results)} items, "
            f"representing [green]{format_size(displayed_size)}[/green]"
        )
    
    # Generate report if requested
    if report:
        generate_report(filtered_results, report)
    
    # Handle deletion if requested
    if delete:
        console.print("\n[bold yellow]Deletion Mode Enabled[/bold yellow]")
        console.print("[yellow]Enter the number of an item to delete it, or 'q' to quit[/yellow]")
        
        while True:
            choice = console.input("\nItem to delete (or 'q' to quit): ")
            
            if choice.lower() == 'q':
                break
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(top_results):
                    item_path, _, is_file, is_safe, reason = top_results[index]
                    
                    if is_protected(item_path):
                        console.print("[bold red]WARNING: This is a protected system item![/bold red]")
                        if not Confirm.ask("Are you ABSOLUTELY sure you want to delete this protected item?"):
                            continue
                    elif not is_safe:
                        console.print(f"[bold yellow]Warning: This item may not be safe to delete.[/bold yellow]")
                        console.print(f"Reason: {reason}")
                        if not Confirm.ask("Are you sure you want to delete this item?"):
                            continue
                    else:
                        if not Confirm.ask(f"Delete {item_path}?"):
                            continue
                    
                    # Try to delete the item
                    if delete_item(item_path):
                        console.print(f"[green]Successfully deleted {item_path}[/green]")
                        # Remove the item from our results
                        top_results.pop(index)
                    else:
                        console.print(f"[red]Failed to delete {item_path}[/red]")
                else:
                    console.print("[red]Invalid item number[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number or 'q'[/red]")

def is_protected(path: str) -> bool:
    """Check if a path is protected system directory."""
    path_lower = path.lower()
    
    for protected in PROTECTED_FOLDERS:
        protected_lower = protected.lower()
        # Check if the path contains a protected folder name
        if (f"\\{protected_lower}\\" in path_lower or 
            path_lower.endswith(f"\\{protected_lower}") or
            f"/{protected_lower}/" in path_lower or
            path_lower.endswith(f"/{protected_lower}")):
            return True
    
    return False

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        if not is_admin() and "Access is denied" in str(e):
            console.print("[yellow]Trying to run with administrator privileges...[/yellow]")
            run_as_admin()
