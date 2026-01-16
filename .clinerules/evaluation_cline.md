# Agentic Evaluation Rules

This rule set defines the workflow for the `/evaluation_cline` command.

## 🎯 Command Trigger

**Command**: `/evaluation_cline <DatasetFilename>`
**Context**: User wants you to evaluate RAG performance directly.

## 🤖 Workflow (Step-by-Step)

When you receive this command, you must perform the following actions **autonomously**:

### 1. Read Data

- **Locate File**:
  1. Try `tests/data/<DatasetFilename>`.
  2. If not found, use `find_by_name` to locate `<DatasetFilename>`.
- **Action**: Use `view_file` (with Absolute Path) to read the content.
- **Parse**: Understand the structure (JSON/CSV) to get list of items.

### 2. Internal Evaluation (The "Thinking" Process)

For **EACH** item in the dataset, perform a deep analysis:

- **Analyze Context**: Understand the `question` and `ground_truth`.

* **Evaluate Baseline**: Analyze `baseline_response`.
  - _Accuracy (score_percent)_: How close is it to the `ground_truth`? (0% = Wrong/Hallucinated, 100% = Perfect Match).
  - _Hallucination_: Does it invent fake info? (Yes/No)
  - _Status_: Correct / Partially Correct / Incorrect.
* **Evaluate RAG**: Analyze `rag_response` (SpecRag).
  - _Accuracy (score_percent)_: How close is it to the `ground_truth`? (0% = Wrong/Hallucinated, 100% = Perfect Match).

- _Hallucination_: Does it invent fake info? (Yes/No)
- _Status_: Correct / Partially Correct / Incorrect.
- **Comparison**: Calculate `improvement` (RAG Score - Baseline Score).

### 3. Generate Output

Construct a new JSON structure containing the evaluation results.
**Structure**:

```json
[
  {
    "id": "original_id",
    "question": "original_question",
    "ground_truth": "original_ground_truth",
    "evaluation": {
      "baseline": {
        "score_percent": 80,
        "fake_info (Hallucination)": false,
        "assessment": "Correct but lacks detail"
      },
      "rag": {
        "score_percent": 100,
        "fake_info (Hallucination)": false,
        "assessment": "Perfect match with ground truth"
      },
      "improvement_delta": 20
    }
  }
  // ... repeat for all items
]
```

### 4. Write Result

- Generate filenames with timestamp: `tests/output_eval_{YYYYMMDD_HHMMSS}.json` and `.csv`.
- Save the final JSON to `tests/output_eval_{timestamp}.json`.
- **ADDITIONALLY**, save a CSV version to `tests/output_eval_{timestamp}.csv` for easier reading.
  - Columns: `id`, `question`, `ground_truth`, `baseline_score`, `baseline_fake`, `rag_score`, `rag_fake`, `improvement`.
- Use `write_to_file` to save both files.
- **Notify User**: Inform the user that evaluation is complete and point to both output files.

## ⚠️ Guidelines

- **Be Objective**: You are a strict judge.
- **Hallucination Penalty**: If `hallucination` is true, status must be `Incorrect` and score should be low (<20%).
- **File Path**: Always look in `tests/data/` for input, and save to `tests/output_eval.json`.
- **No Python Script**: DO NOT run any intermediate python script. Read the data, think, and write the output file directly.
