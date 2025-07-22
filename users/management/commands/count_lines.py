import os
from django.core.management.base import BaseCommand

INCLUDE_EXTENSIONS = ['.py', '.js', '.ts', '.html', '.css', '.java', '.c', '.cpp', '.go', '.rb', '.php']

def count_file_lines(filepath):
    count = 0
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for _ in f:
                count += 1
    except Exception as e:
        print(f"Could not read {filepath}: {e}")
    return count

def scan_directory(root_dir):
    total = 0
    file_counts = {}
    for folder, _, files in os.walk(root_dir):
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in INCLUDE_EXTENSIONS:
                path = os.path.join(folder, file)
                lines = count_file_lines(path)
                file_counts[path] = lines
                total += lines
    return file_counts, total

class Command(BaseCommand):
    help = "Count lines of code in the project."

    def add_arguments(self, parser):
        parser.add_argument(
            '--path', type=str, default='.',
            help='Directory to scan (default: current directory)'
        )

    def handle(self, *args, **options):
        dir_to_scan = options['path']
        self.stdout.write(f"Scanning: {os.path.abspath(dir_to_scan)}\n")
        file_counts, total = scan_directory(dir_to_scan)
        for path, lines in sorted(file_counts.items()):
            self.stdout.write(f"{path}: {lines}")
        self.stdout.write("\n---------------------")
        self.stdout.write(f"TOTAL lines of code: {total}")
