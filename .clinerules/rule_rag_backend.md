# Rule: Use RAG Backend for Information Retrieval

## ⚠️ CRITICAL INSTRUCTION: ALWAYS SEARCH FIRST

Before answering ANY technical question, you **MUST** query the RAG backend to get the latest context.
**DO NOT rely on your internal knowledge** unless the search returns nothing.

### Core Workflow
1. **Analyze Intent**: What is the user looking for? (Diagram, Fact, Code, Concept)
2. **Select Command**: Use the Decision Matrix below.
3. **Execute Search**: Run the CLI command.
4. **Read Output**: 
   - Check terminal summary.
   - **CRITICAL**: Use `read_file` on the generated JSON file in `process/output/` to get full content.
5. **Answer**: Synthesize information from the search results.

### 🚫 PROHIBITED ACTIONS
- **DO NOT** convert PDF to text using python libraries (e.g., PyPDF2, pdfminer).
- **DO NOT** try to read raw PDF files directly.
- **DO NOT** bypass the RAG backend to search files manually.
- **REASON**: The RAG backend is optimized for chunking, vectorization, and retrieval. Manual reading is slow, error-prone, and loses semantic context.

---

## 🧠 Command Decision Matrix

Choose the best search strategy based on User Intent:

| User Intent | Recommended Command | Why? |
|-------------|---------------------|------|
| **General Question**<br>_"What is HID protocol?"_ | `python -m src.main search "query"` | Standard semantic search. |
| **Visual/Diagrams**<br>_"Show me connection flow", "Figure of stack"_ | `python -m src.main search -pic "query"` | Filters for images/charts only. |
| **Exact Name/Title**<br>_"Figure 4.1", "Table 2-3", "A2DP Spec"_ | `python -m src.main search -hy "exact title"` | Hybrid search ranks exact text matches higher. |
| **Specific Diagram**<br>_"The 'Link Loss' flowchart"_ | `python -m src.main search -pic -hy "Link Loss"` | Compiles image filter + exact match. |
| **Hard/Vague Query**<br>_"How to reconnect bluetooth..."_ (complex) | `python -m src.main msearch "q1" "q2" "q3"` | **Multi-Query**: Increases chance of finding info by checking variations. |

---

## 🔄 Search Troubleshooting & Fallback

If your initial search returns **0 results** or irrelevant info, **DO NOT give up**. Follow this path:

1. **Relax Constraints**: 
   - If using `-hy` (Hybrid), try without it (Standard Semantic).
   - If using `-pic` (Image), try standard text search to find context first.
   
2. **Expand Query (`msearch`)**:
   - Generate synonyms and broader terms.
   - Example: _"reconnection"_ -> _"link loss", "connection establishment", "recovery"_
   - Run: `python -m src.main msearch "term1" "term2" "term3"`

3. **Check Processing**:
   - Verify if documents are listed: `python -m src.main list`
   - If doc is missing, ask user to `process` it.

---

## 📄 Handling Search Results

Results are saved to `process/output/query_YYYYMM_HHMMSS.json`.

**JSON Structure:**
```json
{
  "results": [
    {
      "rank": 1,
      "similarity": 0.85,
      "document": "Full text content...", 
      "metadata": {
        "content_type": "image", 
        "image_path": "data/extracted/file_p1.png"
      }
    }
  ]
}
```

**Actionable Steps:**
1. **Read JSON**: Always read the JSON content for the full text (Terminal output is truncated).
2. **Analyze Images**: If `content_type` is "image", use your **Vision** capabilities to look at `image_path`.
   - *Describe what you see in the image to the user.*

---

## 🔧 Maintenance: Tagging & Processing

### Vision-Powered Tagging (Improvement Loop)
If you find an image that is relevant but hard to find, **add tags** to help future searches.

1. **Analyze**: Look at image `data/extracted_images/xyz.png`.
2. **Tag**: `python -m src.main addtag <chunk_id> "descriptive-tag-name"`
   - *Example: `addtag HID_p42 "connection-state-machine"`*

### Processing Priority
When adding new files, prioritize full-page extraction:

| Priority | Flag | Usage |
|----------|------|-------|
| **High** | `-fp` | `process -fp` (Default/Best for RAG) |
| **Med** | `-pymu`| `process -pymu` (Asset extraction only) |

