<task name="RAG Feedback Collection">

<task_objective>
Collect user evaluation of RAG search results and save to JSON file in the results_trial folder. This workflow is called after RAG backend search to gather user feedback on answer quality, collect accuracy ratings (1-10), and store the feedback in structured JSON format. Uses the `ask_followup_question` tool for user interaction and standard file operations for JSON storage.
</task_objective>

<detailed_sequence_steps>

# RAG Feedback Collection Process - Detailed Sequence of Steps

## 1. Show Answer Quality Assessment

1. Display the RAG search results and final answer to the user
   - Present the complete search results from the RAG backend
   - Show the final synthesized answer that was provided to the user
   - Include any image analysis or additional context that was part of the response

2. Ask if the answer quality is acceptable
   - Use clear language to prompt user evaluation
   - Provide context about what aspects to consider (accuracy, completeness, relevance)

## 2. Get User Rating (1-10)

1. Use `ask_followup_question` to collect accuracy rating from 1-10
   - Present a clear rating scale question
   - Example: "How would you rate the accuracy of this answer? (1 = completely wrong, 10 = completely accurate)"

2. Optionally collect additional feedback comments
   - Ask if user has any additional comments about the response
   - Provide open text field for detailed feedback
   - Make this step optional to not burden the user

## 3. Save Question and Results

1. Capture the original question that was asked
   - Store the exact query string
   - Include any context or follow-up information

2. Capture the final results/answer provided
   - Store the complete response that was generated
   - Include any supporting evidence or sources cited
   - Preserve formatting and structure of the answer

3. Get document names from /data/documents directory
   - Use `list_files` to get document names (without reading file contents)
   - Store only the filenames, not full paths
   - This provides source document information for feedback context

4. Prepare data structure for JSON storage
   - Organize captured information in a structured format
   - Ensure all data is serializable to JSON
   - Include timestamp for when feedback was collected

## 4. Write to JSON File in results_trial Folder

1. Check if results_trial directory exists, create if needed
   - Use `list_files` to check for directory existence
   - Use `execute_command` with `mkdir -p results_trial` to create the folder if it doesn't exist
   - The results_trial folder will store all feedback JSON files

2. Generate JSON file with required structure:
   ```json
   {
     "question": "original question text",
     "final_result": "complete answer text",
     "accuracy": 8,
     "timestamp": "2026-01-26T16:30:45",
     "additional_comments": "optional user comments",
     "documents": ["document1.pdf", "document2.pdf"]
   }
   ```

3. Save to results_trial folder with descriptive filename
   - Use timestamp-based naming to avoid conflicts
   - Example: `feedback_20260126_163045.json`
   - Use `write_to_file` tool for JSON file creation
   - All feedback files are stored in the results_trial directory

4. Confirm successful storage in results_trial folder
   - Verify file was created successfully in results_trial folder
   - Log completion message with file location
   - Use `attempt_completion` to present final confirmation

## 5. Upload JSON File to Server

1. Use curl to upload the JSON file to the feedback server
   - Execute curl command without reading file contents
   - Command format: `curl -F "file=@results_trial/filename.json" http://107.98.72.59:8888/RAG/feedback/`
   - This sends the file directly without loading it into memory

2. Verify successful upload
   - Check server response for confirmation
   - Log the server response URI for reference
   - Handle any upload errors appropriately

3. Complete the workflow
   - Present final confirmation including server upload status
   - Use `attempt_completion` to present complete process results

</detailed_sequence_steps>

</task>
