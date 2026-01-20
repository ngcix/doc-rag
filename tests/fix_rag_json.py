import json
import re

def fix_rag_json(file_path):
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        # Strip trailing newline characters but preserve indentation
        lines = [line.rstrip('\n') for line in f.readlines()]

    # Filter empty lines
    lines = [line for line in lines if line.strip()]

    fixed_lines = []
    in_rag_response = False
    rag_response_buffer = []
    current_indentation = ""

    for i, line in enumerate(lines):
        stripped = line.strip()

        if in_rag_response:
            # Check for end of object
            # Use lookahead to ensure it's really the object end and not code inside the string
            
            is_object_end = False
            # Check for standard object end signatures
            if stripped == '}' or stripped == '},':
                 # Check next non-empty line to confirm context
                 if i + 1 < len(lines):
                     next_line_stripped = lines[i+1].strip()
                     # If next line starts a new object or ends the array/file, it's likely an object end
                     if next_line_stripped.startswith('{') or next_line_stripped.startswith(']'):
                         is_object_end = True
                 else:
                     # End of file? likely end of last object if it's } or }]
                     if stripped.startswith('}'):
                         is_object_end = True
            
            if is_object_end:
                # End of block detected, process the buffer
                
                # Join buffer lines with newlines
                full_content_raw = "\n".join(rag_response_buffer)
                
                content = full_content_raw
                
                # The raw content typically includes the closing quote/comma if it was semi-valid
                # We need to strip the "frame" if present
                if content.endswith('",'):
                    content = content[:-2]
                elif content.endswith('"'):
                    content = content[:-1]
                
                # Fix any double-escaping that might exist if we are re-running on mixed content
                # e.g. \\" -> "
                content = content.replace('\\"', '"')
                
                # Use json.dumps to handle ALL escaping (quotes, newlines, control chars) safely
                # ensure_ascii=False to keep Vietnamese characters readable
                fixed_content_json = json.dumps(content, ensure_ascii=False)
                
                # Reconstruct the line
                new_line = f'{current_indentation}"rag_response": {fixed_content_json}'
                
                fixed_lines.append(new_line)
                fixed_lines.append(line) # The }, line
                
                in_rag_response = False
                rag_response_buffer = []
            else:
                rag_response_buffer.append(line)
        else:
            if '"rag_response": "' in line:
                in_rag_response = True
                # Extract starting content
                key_pattern = '"rag_response": "'
                start_idx = line.find(key_pattern) + len(key_pattern)
                
                # Capture indentation for reconstruction
                current_indentation = line[:line.find('"rag_response"')]
                
                # Content is everything after the key pattern
                start_content = line[start_idx:]
                rag_response_buffer.append(start_content)
            else:
                fixed_lines.append(line)

    print("Writing fixed content...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    
    # Validation
    print("Validating JSON...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully fixed {file_path}. JSON is valid.")
        print(f"Total records: {len(data)}")
    except json.JSONDecodeError as e:
        print(f"Failed to fix: {e}")
        print(f"Error at line {e.lineno}, column {e.colno}")
        # if 0 <= e.lineno - 1 < len(lines):
        #    print(f"Line {e.lineno}: {lines[e.lineno-1].strip()}")

if __name__ == "__main__":
    fix_rag_json(r'd:\AI-PROJECT\RAG\SpecRag\tests\rag_record.json')
