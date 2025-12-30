# Rule: Search Information in Database

## Overview
This rule describes the steps to search for information in the vector database using the Simple RAG system. The database is assumed to be already created and populated with documents.

## Prerequisites
- Python 3.11+
- All dependencies installed from `requirements.txt`

## Rule Steps

### 1. Search Information
```bash
python -m src.main search "your query" --top-k 1
```
This command performs semantic search in the vector database and returns only the best match.

### 2. View Results
Search results are saved in JSON format in `process/output/` directory.

Example result format:
```json
{
  "query": "authentication flow",
  "result_count": 1,
  "results": [
    {
      "rank": 1,
      "similarity": 0.85,
      "document": "Matched content...",
      "metadata": {
        "source_file": "docs/api.md",
        "type": "text"
      }
    }
  ]
}
```

### 3. Analyze Images (If Found)
If the search result contains images (charts, diagrams), analyze them using AI:
```bash
python src/analyze_image.py "query_id"
```

### 4. Clean Up
After completing the analysis, clean up input and output files to maintain system performance:
```bash
python -m src.main clean --logs
```
This command removes all search input and output logs from the process directory.

## Example Search Result: "Typical Bluetooth HID Software Stacks"

When searching for "Typical Bluetooth HID Software Stacks", the system found a relevant diagram:

**Query:** "Typical Bluetooth HID Software Stacks"
**Result:**
- Rank: 1
- Similarity: 0.932
- Document: "Figure 2.2: Typical Bluetooth HID Software Stacks"
- Source: HID_v1.1.1.pdf (Page 23)
- Image: pdf_HID_v1.1.1_23_0_fb144109.png

This result contains a diagram showing the typical Bluetooth HID software stack architecture, which is highly relevant to the query.

## Usage Guidelines

Whenever you need to check for specific information, use this search workflow to verify if the information exists in the database. This approach allows you to quickly find relevant content without manually searching through documents.

### Example Usage:
```bash
python -m src.main search "HID protocol specification"
python -m src.main search "authentication flow details"
python -m src.main search "error handling procedures"
```

### Interpreting Results:
- Check the similarity score to assess relevance (higher is better)
- Review the matched document content for accuracy
- Verify the source file to understand context

### Analyzing Images:
When search results contain images (charts, diagrams), the system automatically extracts and saves them. You can analyze these images using the AI image analysis tool:
```bash
python src/analyze_image.py "query_id" --prompt "Describe this image in detail"
```

The query_id is automatically generated and saved in the process/output directory as a JSON file.
