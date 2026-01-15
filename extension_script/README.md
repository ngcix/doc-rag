# Extension Scripts

This directory contains additional scripts that extend the functionality of the Simple RAG system.

## analyze_extracted_images.py

A script that automatically analyzes extracted images using Gauss AI and adds the analysis results as knowledge and tags to the RAG system.

### Features

- **Batch Processing**: Automatically processes all images in the `data/extracted_images` directory
- **Detailed Analysis**: Uses Gauss AI to provide comprehensive technical analysis of diagrams and images
- **Smart Tagging**: Generates relevant tags from the analysis results
- **RAG Integration**: Automatically adds knowledge and tags to the vector database
- **Dry Run Mode**: Test the process without actually calling APIs

### Requirements

- Gauss API credentials set as environment variables:
  - `GAUSS_CLIENT_KEY`
  - `GAUSS_TOKEN`
  - `GAUSS_ENDPOINT_URL`
  - `GAUSS_USER_EMAIL`

### Setup Credentials

To use this script, you need to set the Gauss API credentials as environment variables:

```bash
# Linux/Mac
export GAUSS_CLIENT_KEY="your_client_key"
export GAUSS_TOKEN="your_token"
export GAUSS_ENDPOINT_URL="your_endpoint_url"
export GAUSS_USER_EMAIL="your_email"

# Windows (Command Prompt)
set GAUSS_CLIENT_KEY=your_client_key
set GAUSS_TOKEN=your_token
set GAUSS_ENDPOINT_URL=your_endpoint_url
set GAUSS_USER_EMAIL=your_email

# Windows (PowerShell)
$env:GAUSS_CLIENT_KEY="your_client_key"
$env:GAUSS_TOKEN="your_token"
$env:GAUSS_ENDPOINT_URL="your_endpoint_url"
$env:GAUSS_USER_EMAIL="your_email"
```

### Usage

```bash
# Process all images (requires Gauss API credentials)
python extension_script/analyze_extracted_images.py

# Process with limit (good for testing)
python extension_script/analyze_extracted_images.py --limit 10

# Dry run to see what would be processed (no credentials needed)
python extension_script/analyze_extracted_images.py --dry-run

# Specify custom images directory
python extension_script/analyze_extracted_images.py --images-dir /path/to/images
```

### Workflow

1. **Image Analysis**: Each image is analyzed with a detailed technical prompt
2. **Tag Generation**: Tags are generated from the analysis results
3. **Knowledge Addition**: Analysis text is added to the RAG system using `addknowledge`
4. **Tag Addition**: Generated tags are added using `addtag`

### Example Output

```
Processing image: A2DP_v1.4.1_p14_0.png
  Analyzing image with Gauss AI...
  ✅ Image analysis completed
  Generating tags from analysis...
  ✅ Generated tags: ['connection flow', 'bluetooth diagram', 'audio streaming']
  Adding knowledge for chunk_id: A2DP_v1.4.1_p14_0
  ✅ Knowledge added successfully
  Adding tags to RAG system...
    ✅ Added tag: connection flow
    ✅ Added tag: bluetooth diagram
    ✅ Added tag: audio streaming
  🎉 Completed processing A2DP_v1.4.1_p14_0.png
```

### Alternative: Manual Knowledge Addition

If you don't have Gauss API credentials, you can manually add knowledge and tags using the RAG system's built-in commands:

```bash
# Add knowledge manually
python -m src.main addknowledge A2DP_v1.4.1_p14_0 "Detailed description of the image content..."

