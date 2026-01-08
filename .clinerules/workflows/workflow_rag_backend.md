<task name="RAG Backend Search and Analysis">

<task_objective>
Search information in RAG database and analyze results, including image description and tagging. The workflow provides a complete process from environment setup through search operations, image analysis, interactive tagging, and cleanup. Uses the RAG backend tools and follows the standardized Cline workflow conventions.

Expected output: Search results with optional image descriptions and improved tagging for better discoverability.
</task_objective>

<detailed_sequence_steps>
# RAG Backend Search and Analysis Process - Detailed Sequence of Steps

## Recommended Rule
Follow the detailed rule documented in `.clinerules/rule_rag_backend.md`

## 1. Environment Setup

1. Always activate the virtual environment before running any commands using the `execute_command` tool:
   ```bash
   source .venv/bin/activate
   ```

## 2. Search Operations

1. **Basic Search** - Use for general queries:
   ```bash
   python -m src.main search "your query" --top-k 5
   ```

2. **Image-Only Search** - Use when looking for diagrams or figures:
   ```bash
   python -m src.main search -pic "diagram or figure name"
   ```

3. **Hybrid Search** - Use for specific figure/table names with exact-match priority:
   ```bash
   python -m src.main search -hy "Figure 4.1: Media Payload"
   ```

4. **Combined Search** - Best for finding specific diagrams:
   ```bash
   python -m src.main search -pic -hy "Interrupt IN Flow Chart"
   ```

## 3. View and Analyze Results

1. Results are saved in `process/output/query_*.json`

2. Key fields to examine:
   - `chunk_id`: Document ID (use for addtag)
   - `image_path`: Path to extracted image
   - `similarity`: Relevance score (higher is better)
   - `content_type`: Type of content (text or image)

3. Use the `read_file` tool to examine the JSON output for detailed results

## 4. Describe Images

1. Only read and describe images when the rank 1 search result has "content_type": "image" in the JSON output

2. **Check search results** - First examine the JSON output to verify the top result is an image using the `read_file` tool

3. **Read the image file** using the `read_file` tool only when content_type is image:
   ```xml
   <read_file>
   <path>/path/to/image.png</path>
   </read_file>
   ```

4. **Analyze the image content** - The system will automatically provide image analysis results

5. **Provide a detail description** based on the analysis results

## 5. Present Answer Based on Analysis

1. **Synthesize information** from search results and image analysis:
   - Extract key information from `process/output/query_*.json`
   - Incorporate image analysis content if top result is an image
   - **CRITICAL: The information contained in the image is relevant to the user's question and Filter out noise and irrelevant information not related to user's question**
     - Focus only on content that directly answers the user's specific query
     - Remove boilerplate text, headers, footers, and page numbers
     - Ignore generic document metadata and formatting elements
     - When images contain multiple elements, only describe the relevant parts
     - Cross-reference multiple search results to verify information accuracy
   - Formulate comprehensive answer addressing user's original question specifically
   - Note that images may contain extraneous text or elements not relevant to the query

2. **Present detailed explanation to user** using `attempt_completion` tool:
   - Provide comprehensive explanation based on analyzed content
   - Include detailed supporting evidence from search results
   - Show relevant image analysis if applicable
   - Structure response with thorough reasoning to address user's query

4. **Proceed to next steps**:
   - If top result IS an image → Continue to step 6 (Generate and Add Tags for Images)
   - If top result is NOT an image → Continue to step 7 (Cleanup Query Files)

## 6. Generate and Add Tags for Images

1. **Identify key concepts** from the image description:
   - Figure numbers and names (e.g., "Figure 2.1 A2DP") - phrase
   - Protocol names and stacks (e.g., "AVDTP SDP stack") - phrase
   - Specific entities and components (e.g., "Audio Source Sink") - phrase
   - Architectural elements (e.g., "Protocol stack layers") - phrase
   - **Avoid single words like: "protocol", "figure", "stack"**

2. **Generate multiple tag options** (3-5 different combinations):
   - Each option should be specific and focused (5-15 tags per option)
   - **IMPORTANT: Tags must be phrases (multi-word terms) not single words**
   - **Good phrases**: "AVDTP signaling entity", "Audio streaming flow", "Protocol stack layers"
   - **Avoid single words**: "protocol", "entity", "flow", "stack"
   - **Avoid generic terms**: "diagram", "figure", "image", "document"
   - Use descriptive phrases that capture specific concepts
   - Include both specific technical phrases and broader architectural phrases
   - Vary the focus (e.g., one option focuses on protocols, another on architecture)

3. **Present options to user** using `ask_followup_question`:
   - Show 2-3 tag options plus "No tags" option
   - Include brief descriptions of what each option emphasizes
   - Example format:
     ```
     <ask_followup_question>
     <question>Which tag option would you like to use for this image?</question>
     <options>["Option 1: Protocol-focused tags", "Option 2: Architecture-focused tags", "Option 3: Entity-focused tags", "No tags"]</options>
     </ask_followup_question>
     ```

4. **Add selected tags** using the addtag command with the chunk_id from search results:
   ```bash
   python -m src.main addtag <chunk_id> "selected,tag,option"
   ```

## 7. Cleanup Query Files

1. **Identify query files** in both directories:
   - `process/input/` - Contains query parameter files
   - `process/output/` - Contains search results

2. **Ask user for cleanup preference** using `ask_followup_question`:
   ```xml
   <ask_followup_question>
   <question>Found X query files. Would you like to delete them?</question>
   <options>["Yes, delete all query files", "Yes, delete only recent files", "No, keep all files", "Let me choose specific files"]</options>
   </ask_followup_question>
   ```

3. **Execute cleanup based on user choice** using the `execute_command` tool:
   - **All files**: `rm -f process/input/*.json process/output/*.json`
   - **Recent files**: Delete files from current session only
   - **Specific files**: Delete user-selected files
   - **No files**: Keep all files for future reference

4. **Verify deletion** by checking directories are empty when expected using the `list_files` tool

5. Use the `attempt_completion` tool to present the final results
</detailed_sequence_steps>

</task>
