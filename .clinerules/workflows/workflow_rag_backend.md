<task name="RAG Backend Search and Analysis">

<task_objective>
Search information in RAG database and analyze results, including image description and tagging. The workflow provides a complete process from search operations through image analysis, interactive tagging, and cleanup. Uses the RAG backend tools and follows the standardized Cline workflow conventions.

Expected output: Search results with optional image descriptions and improved tagging for better discoverability.
</task_objective>

<detailed_sequence_steps>

# RAG Backend Search and Analysis Process - Detailed Sequence of Steps

## Recommended Rule

Follow the detailed rule documented in `.clinerules/rule_rag_backend.md`
**NEVER read file in ./data/documents**

## 1. Question Analysis

1. **Analyze User Question Intent**:
   - Determine if the question is specific or vague/general
   - Identify key technical domains mentioned (audio, network, security, protocol, algorithm, design, etc.)
   - Detect question type (diagram request, factual query, procedural question, document summary, etc.)
   - Check if question relates to documents but doesn't specify which document

2. **Handle Document-Related Questions Without Specific Document**:
   - If question asks for document summary, overview, or general information but doesn't specify which document, check available documents
   - List available documents using: `ls -la data/documents/`
   - Present available documents to user for selection

3. **Handle Vague Questions**:
   - If question is too general (e.g., "show me diagram", "what is filter") or not detailed, provide suggestions
   - Generate 3-5 specific alternatives based on common patterns:
     - Diagram requests: "flow diagram", "architecture diagram", "sequence diagram", "connection diagram", "block diagram"
     - Flow requests: "data flow", "process flow", "signal flow", "control flow", "algorithm flow"
     - Protocol requests: "communication protocol", "network protocol", "audio protocol", "stack protocol", "interface protocol"
     - Filter requests: "filter design", "filter implementation", "digital filter", "analog filter", "frequency filter"
     - System requests: "system architecture", "system design", "system components", "system overview", "system flow"
     - Document summary requests: "document overview", "key features", "main components", "technical specifications", "implementation details"
     - Entity requests: "system entities", "component entities", "architecture entities", "protocol entities", "interface entities"

4. **Present Document Options to User** using `ask_followup_question`:
   - When question relates to documents but doesn't specify which one:
   ```xml
   <ask_followup_question>
   <question>I found the following documents available for processing. Which document would you like to work with?</question>
   <options>["Document 1", "Document 2", "Let me add more documents", "Cancel"]</options>
   </ask_followup_question>
   ```

5. **Present Suggestions to User** using `ask_followup_question`:

   ```xml
   <ask_followup_question>
   <question>Your question "{original_question}" is quite general. Here are some more specific options:</question>
   <options>["Option 1: Specific suggestion 1", "Option 2: Specific suggestion 2", "Option 3: Specific suggestion 3", "Let me rephrase my question"]</options>
   </ask_followup_question>
   ```

6. **Wait for User Selection**:
   - Use the selected specific question for the search
   - If user chooses to rephrase, wait for their new question

## 2. Search Operations

**🔍 Search Strategy Decision Tree:**

1. **Query contains SPECIFIC identifiers** (Table X.Y, Figure X.Y, specific names/IDs)
   → **Use Hybrid Search** (`-hy`) for best results

2. **Looking for diagrams/images**
   → Use **Image-Only** (`-pic`) or **Combined** (`-pic -hy`)

3. **General semantic questions**
   → Use **Basic Search** (no flags)

### Search Commands:

1. **Basic Search** - Use for general semantic queries ONLY:

   ```bash
   specrag search "your query" --top-k 5
   ```

2. **Image-Only Search** - Use when looking for diagrams or figures without specific numbers:

   ```bash
   specrag search -pic "diagram or figure name"
   ```

3. **Hybrid Search** - ⭐ **RECOMMENDED for specific identifiers** ⭐

   **Use when query contains:**
   - Specific table numbers (e.g., "Table 4.22", "Table 8.1")
   - Specific figure numbers (e.g., "Figure 4.6", "Figure 2.1")
   - Exact names or identifiers (e.g., "AVDTP protocol", "SBC codec")
   - Technical terms requiring exact matching

   ```bash
   specrag search -hy "Table 4.22"
   specrag search -hy "Figure 4.1: Media Payload"
   ```

   **Why hybrid?** Combines:
   - BM25 keyword matching (finds exact "Table 4.22")
   - Vector semantic search (understands context)
   - RRF ranking (best of both approaches)

4. **Combined Search** - Best for finding specific diagrams by number:
   ```bash
   specrag search -pic -hy "Figure 3.5: Interrupt Flow"
   specrag search -pic -hy "Table 4.22"
   ```

## 3. View and Analyze Results

1. Results are saved in `process/output/query_*.json`

2. Key fields to examine:
   - `chunk_id`: Document ID (use for addtag)
   - `image_path`: Path to extracted image
   - `similarity`: Relevance score (higher is better)
   - `content_type`: Type of content (text or image)

3. Use the `read_file` tool to examine the JSON output for detailed results

## 4. Re-rank Results

**CRITICAL**: Before presenting results, mentally re-rank them based on actual relevance to the user's question.

1. **Evaluate each result** against the original question:
   - Does this result directly answer the question?
   - Is the content specifically about what the user asked?
   - Rate relevance: HIGH (directly answers) / MEDIUM (related) / LOW (tangential)

2. **Filter out noise**:
   - Remove results with LOW relevance
   - Remove duplicate or near-duplicate content
   - Remove results that only mention keywords but don't provide useful information

3. **Re-order by actual relevance**:
   - Place HIGH relevance results first
   - Consider content quality, not just similarity score
   - If an image better answers the question than text, prioritize the image

4. **Document your re-ranking** (internal reasoning):
   ```
   Original order: [1, 2, 3, 4, 5]
   After re-rank:  [3, 1, 5] (removed 2, 4 as low relevance)
   Reason: Result 3 directly shows the diagram user asked for
   ```

> **Note**: The vector similarity score measures semantic similarity, not answer quality. A result with 0.75 score may be more useful than one with 0.85 if it better addresses the specific question.

## 5. Describe Images

1. ONLY read and describe images when the rank 1 search result has "content_type": "image" in the JSON output

2. **Check search results** - First examine the JSON output to verify the top result is an image using the `read_file` tool

3. **Read the image file** using the `read_file` tool only when the rank 1 search result has "content_type": "image" in the JSON output:

   ```xml
   <read_file>
   <path>/path/to/image.png</path>
   </read_file>
   ```

4. **Analyze the image content** - The system will automatically provide image analysis results

5. **Provide a detail description** based on the analysis results

## 6. Present Answer Based on Analysis

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

2. **Present detailed explanation to user**:
   - Provide comprehensive explanation based on analyzed content
   - Include detailed supporting evidence from search results
   - Show relevant image analysis if applicable
   - Structure response with thorough reasoning to address user's query
   - **Ensure final results show detailed information addressing user's specific request**

3. **CRITICAL: Always display complete analysis before proceeding**:
   - **CRITICAL** Ensure all search results and image analysis content are presented to user
   - Do not proceed to tagging until user has seen the full analysis
   - Wait for user acknowledgment of the analysis content
   - Display detailed results before asking for tagging decisions

4. **Proceed to next steps after user acknowledgment**:
   - Wait for user confirmation after presenting complete analysis
   - If top result IS an image → Continue to step 8 (Generate and Add Tags for Images)
   - If top result is NOT an image → Continue to step 9 (Cleanup Query Files)

## 7. Generate and Add Tags for Images

1. **Verify analysis presentation**:
   - Confirm that search results have been displayed to user
   - Confirm that image analysis content has been shown to user
   - Ensure user has seen the complete analysis before proceeding to tagging

2. **Identify key concepts** from the image description:
   - Figure numbers and names (e.g., "Figure 2.1 A2DP") - phrase
   - Protocol names and stacks (e.g., "AVDTP SDP stack") - phrase
   - Specific entities and components (e.g., "Audio Source Sink") - phrase
   - Architectural elements (e.g., "Protocol stack layers") - phrase
   - **Avoid single words like: "protocol", "figure", "stack"**

3. **Generate multiple tag options** (3-5 different combinations):
   - Each option should be specific and focused (5-15 tags per option)
   - **IMPORTANT: Tags must be phrases (multi-word terms) not single words**
   - **Good phrases**: "AVDTP signaling entity", "Audio streaming flow", "Protocol stack layers"
   - **Avoid single words**: "protocol", "entity", "flow", "stack"
   - **Avoid generic terms**: "diagram", "figure", "image", "document"
   - Use descriptive phrases that capture specific concepts
   - Include both specific technical phrases and broader architectural phrases
   - Vary the focus (e.g., one option focuses on protocols, another on architecture)

4. **Present options to user** using `ask_followup_question`:
   - Show 2-3 tag options plus "No tags" option
   - Include brief descriptions of what each option emphasizes
   - **Show actual tags for each option** to help user make informed decisions
   - Example format:
     ```
     <ask_followup_question>
     <question>Which tag option would you like to use for this image?</question>
     <options>["Option 1: Protocol-focused tags (tag1, tag2, tag3)", "Option 2: Architecture-focused tags (tag4, tag5, tag6)", "Option 3: Entity-focused tags (tag7, tag8, tag9)", "No tags"]</options>
     </ask_followup_question>
     ```

5. **Add selected tags** using the addtag command with the chunk_id from search results:
   ```bash
   specrag addtag <chunk_id> "selected,tag,option"
   ```

## 8. Cleanup Query Files

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
