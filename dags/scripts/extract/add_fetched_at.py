import json
import glob
import re
import os
import argparse

def process_file(file_path):
    filename = os.path.basename(file_path)
    match = re.search(r"feature-(\d{4}-\d{2}-\d{2})\.json", filename)
    if not match:
        print(f"Skipping {file_path}: Does not match feature-date.json pattern")
        return

    date = match.group(1)
    print(f"Processing {file_path} with date: {date}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj['fetched_at'] = date
            new_lines.append(json.dumps(obj, ensure_ascii=False) + '\n')
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        print(f"Successfully updated {file_path}")
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Add fetched_at field to feature-date.json files")
    parser.add_argument(
        '--file', 
        type=str, 
        help="Path to a specific feature-date.json file. If not provided, processes all feature-*.json files in data/audio_feature/"
    )
    args = parser.parse_args()

    if args.file:
        process_file(args.file)
    else:
        # Process all feature files
        pattern = "data/audio_feature/feature-*.json"
        files = glob.glob(pattern)
        if not files:
            print(f"No files found matching {pattern}")
        for file_path in files:
            process_file(file_path)

if __name__ == "__main__":
    main()
