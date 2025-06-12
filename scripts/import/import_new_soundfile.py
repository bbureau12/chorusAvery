import os
import shutil
import sqlite3
from datetime import datetime

# CONFIG
DATABASE_PATH = './db/chorusAvery.db'  # adjust path if needed
RAW_DIRECTORY = './recordings/raw'
SUPPORTED_EXTENSIONS = ('.wav',)  # expand as needed

def get_imported_filenames(conn):
    """Fetch all imported filenames from SourceFiles table."""
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM SourceFiles")
    rows = cursor.fetchall()
    imported_files = set(row[0] for row in rows)
    return imported_files

def scan_directory(directory):
    """Scan directory for supported files."""
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                files.append(os.path.join(root, filename))
    return files

def copy_and_import_file(source_path, destination_folder, conn):
    """Copy file and insert record into SourceFiles."""
    filename = os.path.basename(source_path)
    destination_path = os.path.join(destination_folder, filename)

    # Copy the file
    shutil.copy2(source_path, destination_path)
    print(f"✅ Copied: {filename} -> {destination_path}")
    
    print(f"✅ Imported record into SourceFiles: {filename}")

def main():
    target_directory = input("Enter the path to the folder to scan: ").strip()
    if not os.path.exists(target_directory):
        print("❌ Directory does not exist.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    imported_files = get_imported_filenames(conn)

    all_files = scan_directory(target_directory)
    new_files = [f for f in all_files if os.path.basename(f) not in imported_files]

    if not new_files:
        print("🎉 No new files to import!")
        return

    print("\n📋 New files found:")
    for idx, f in enumerate(new_files, 1):
        print(f"{idx}. {os.path.basename(f)}")

    try:
        choice = int(input("\nEnter the number of the file to import (0 to cancel): "))
        if choice == 0:
            print("❌ Import cancelled.")
            return

        selected_file = new_files[choice - 1]
        copy_and_import_file(selected_file, RAW_DIRECTORY, conn)

    except (ValueError, IndexError):
        print("❌ Invalid selection. Exiting.")

    conn.close()

if __name__ == "__main__":
    main()
