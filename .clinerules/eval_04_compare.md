# Eval Step 4: Compare & Evaluate

Command: `/eval_compare`

## 🎯 Purpose

Merge 3 files (test cases, baseline, rag) and evaluate responses against ground truth.

## 🔄 Workflow

**Command**: `/eval_compare`

### Step-by-Step:

1. **Read 3 Input Files**:

   - `tests/ground_truth.json` - contains ground_truth (id, question, ground_truth)
   - `tests/baseline_record.json`
   - `tests/rag_record.json`

2. **Merge by ID**:

   - For each `id`, combine data from all 3 files into one record.

3. **Evaluate Each Pair**:

   - Compare `baseline_response` with `ground_truth`:
     - `score_percent`: 0-100%
     - `right_info_no_hallucication`: true/false
     - `assessment`: Brief comment
   - Compare `rag_response` with `ground_truth`:
     - Same metrics as above
   - Calculate `improvement_delta`: RAG score - Baseline score

4. **Save Output**:

**JSON** (`tests/evaluation_result_{YYYYMMDD_HHMMSS}.json`):

```json
[
  {
    "id": "q_01",
    "question": "What does A2DP stand for?",
    "ground_truth": "Advanced Audio Distribution Profile",
    "baseline_response": "...",
    "rag_response": "...",
    "evaluation": {
      "baseline": {
        "score_percent": 70,
        "right_info_no_hallucication": true,
        "assessment": "Correct but lacks detail"
      },
      "rag": {
        "score_percent": 95,
        "right_info_no_hallucication": true,
        "assessment": "Accurate with source citations"
      },
      "improvement_delta": 25
    }
  }
]
```

**CSV** (`tests/evaluation_result_{YYYYMMDD_HHMMSS}.csv`):

- **IMPORTANT**: Use `utf-8-sig` (BOM) so Excel can read Vietnamese text.
- Columns: `id`, `question`, `ground_truth`, `baseline_response`, `rag_response`, `baseline_score`, `baseline_right_info_no_hallucication`, `rag_score`, `rag_right_info_no_hallucication`, `improvement`

## 📁 Output

- **Location**: `tests/evaluation_result_{timestamp}.json` and `.csv`
- **Notify User**: Report completion and output file paths.

## ⚠️ Evaluation Guidelines

- **Score 100%**: Completely correct, matches ground_truth.
- **Score 0%**: Completely wrong or hallucination.
- **Hallucination = false for right_info**: If response contains fabricated info, `right_info_no_hallucication` = false.
- **Be Objective**: Evaluate fairly, no bias toward RAG or Baseline.
