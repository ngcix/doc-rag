# Rule: Use RAG Backend for Information Retrieval

## Overview

This Simple RAG system provides a vector database backend for semantic search. ClineSR should use this system to:

1. Search for relevant documents/images before answering questions
2. Use `addtag` to boost important documents for future retrieval
3. Leverage hybrid search for exact-match queries (e.g., figure names)

## Quick Reference

| Action | Command |
|--------|---------|
| Search text | `python -m src.main search "query"` |
| Search images only | `python -m src.main search -pic "query"` |
| Hybrid search (exact-match) | `python -m src.main search -hy "Figure 4.1"` |
| Multi-query search | `python -m src.main msearch "q1" "q2" "q3"` |
| Add tag to boost | `python -m src.main addtag <doc_id> "tag"` |

## When to Use Options

| User Intent | Use `-pic`? | Use `-hy`? | Example |
|-------------|-------------|------------|---------|
| Looking for diagram/chart/figure | ✅ Yes | Optional | `search -pic "connection flow"` |
| Asking about specific figure name | ✅ Yes | ✅ Yes | `search -pic -hy "Figure 4.2"` |
| General text question | ❌ No | ❌ No | `search "what is HID protocol"` |
| Looking for exact phrase/title | ❌ No | ✅ Yes | `search -hy "Interrupt IN Flow Chart"` |
| Vague question, need broad recall | ❌ No | ❌ No | Use `msearch` with multiple queries |

### Decision Rules

1. **Use `-pic`** when:
   - User asks for "diagram", "figure", "chart", "image", "flowchart"
   - User wants visual explanation
   - Question contains "show me", "picture of", "hình ảnh"

2. **Use `-hy`** when:
   - Query contains specific names: "Figure X.Y", "Table X", title in quotes
   - User references exact document/section names
   - Semantic search is returning irrelevant results

3. **Use `msearch`** when:
   - User question is vague or has multiple interpretations
   - Single query returns no results
   - Need to cover different phrasings

---

## Search Strategies

### 1. General Search (Semantic)
```bash
python -m src.main search "what is the HID protocol" --top-k 5
```

### 2. Image-Only Search
When you need diagrams, charts, or figures:
```bash
python -m src.main search -pic "connection diagram"
```
Returns only image results with paths to PNG files.

### 3. Hybrid Search (BM25 + Vector)
When searching for **specific figure/table names** or exact text:
```bash
python -m src.main search -hy "Figure 4.2: Media Payload Format"
```
Hybrid mode gives **higher priority to exact-match** terms.

### 4. Combined: Image + Hybrid

Best for finding specific diagrams:

```bash
python -m src.main search -pic -hy "Interrupt IN Flow Chart"
```

---

## Multi-Query Search Strategy (Recommended)

Instead of searching one query, **generate 2-4 keyword variations** and use `msearch`:

### Why Multi-Query is Better

| Single Query | Multi-Query |
|--------------|-------------|
| May miss relevant docs | Covers different phrasings |
| Depends on exact wording | Robust to terminology |

### Usage

```bash
python -m src.main msearch "query1" "query2" "query3" -pic
```

### Example

User asks: "How does Bluetooth reconnect after disconnection?"

**Generate queries:**

```bash
python -m src.main msearch \
  "connection re-establishment" \
  "link loss recovery" \
  "bluetooth reconnect" \
  -pic -hy
```

Results show **matched X/N queries** to indicate confidence.

---

## Vision-Powered Tag Enhancement (Core Workflow)

**Cline has vision capability.** When image results are found, Cline should:

### Step 1: Search for Images
```bash
python -m src.main search -pic "your query"
```

### Step 2: Analyze the Image
Read the image file at `image_path` from the result metadata. 

Example result:
```json
{
  "chunk_id": "HID_SPEC_V10.pdf_p42",
  "image_path": "data/extracted_images/HID_SPEC_V10.pdf_p42.png"
}
```

**👁️ Use vision to analyze the actual image content:**
- What does this diagram show?
- What are the key components/flows?
- What technical terms are visible?

### Step 3: Add Descriptive Tags
Based on your visual analysis, add tags that accurately describe the image:

```bash
python -m src.main addtag HID_SPEC_V10.pdf_p42 "connection-re-establishment-diagram"
python -m src.main addtag HID_SPEC_V10.pdf_p42 "bluetooth-reconnection-flow"
```

> **Why this matters**: The original OCR/context extraction may miss important visual information. Your vision analysis adds semantic understanding that improves future search accuracy.

### Step 4: Verify Improvement
Search again to confirm the document now ranks higher:
```bash
python -m src.main search -pic "bluetooth reconnection flow"
```

---

## Tag Enhancement Examples

| Image Content | Suggested Tags |
|---------------|----------------|
| Flowchart showing auth steps | `authentication-flow`, `oauth-diagram`, `login-sequence` |
| Network topology diagram | `network-architecture`, `server-client-diagram` |
| Bluetooth state machine | `bluetooth-state-machine`, `connection-states` |
| API request/response flow | `api-flow`, `request-response-sequence` |

### Best Practices for Tags:
- Use **lowercase with hyphens** (e.g., `connection-flow`)
- Be **specific and descriptive** (avoid generic tags like `diagram`)
- Add **multiple tags** covering different aspects of the image
- Include **domain-specific terms** visible in the image

---

## Result Format

Search results are saved in `process/output/query_YYYYMMDD_HHMMSS.json`:

```json
{
  "query": "HID protocol",
  "result_count": 5,
  "results": [
    {
      "rank": 1,
      "similarity": 0.85,
      "document": "Content preview...",
      "metadata": {
        "source_file": "HID_SPEC.pdf",
        "content_type": "image",
        "image_path": "data/extracted_images/HID_SPEC_p42.png",
        "page_number": 42
      },
      "chunk_id": "HID_SPEC.pdf_p42"
    }
  ]
}
```

### Key Metadata Fields:
- `content_type`: `"text"` or `"image"`
- `image_path`: Path to extracted image (if image result)
- `page_number`: Source page in PDF
- `chunk_id`: Use this for `addtag` command

---

## When to Use Each Mode

| Scenario | Recommended Command |
|----------|---------------------|
| General question | `search "query"` |
| Finding diagrams/charts | `search -pic "diagram"` |
| Searching exact figure name | `search -hy "Figure 4.1"` |
| Finding specific image | `search -pic -hy "exact title"` |
| Boosting relevant result | `addtag <id> "keyword"` |

---

## Usage Guidelines for ClineSR

1. **Before answering questions about documents**: Search the RAG first
2. **If search returns images**: Check the `image_path` and analyze the image
3. **If result is relevant but wrong rank**: Use `addtag` to improve future searches
4. **For exact-match queries**: Always use `-hy` flag
