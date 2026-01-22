# Eval Step 2: Baseline Recording

Command: `/eval_baseline [filename]`

## 🎯 Purpose

Read questions from a file and record Cline's answers **WITHOUT using RAG**.

> ⚠️ **DATA LEAKAGE PREVENTION**: Reads only from questions file (NO read ground_truth.json) to ensure fair evaluation.

## 🔄 Workflow

**Command**: `/eval_baseline [filename]`

- If `filename` is provided: use `tests/<filename>`
- If no filename: default to `tests/questions.json`

**Examples**:

- `/eval_baseline` → reads `tests/questions.json`
- `/eval_baseline custom_questions.json` → reads `tests/custom_questions.json`

### Step-by-Step:

1. **Read Questions**:

   - Open file `tests/<filename>` using `view_file`.
   - Parse JSON to get list of questions (only `id` and `question`).

2. **Answer Each Question (NO RAG)**:

   - For each item in dataset:
     - Read `question`.
     - **DO NOT use msearch or any search tool**.
     - Answer based on model's internal knowledge only.
     - Record the answer in `baseline_response`.

3. **Save Output**:
   - Create file `tests/baseline_record.json` with structure:

```json
[
  {
    "id": "q_01",
    "question": "What does A2DP stand for?",
    "baseline_response": "A2DP stands for Advanced Audio Distribution Profile..."
  }
]
```

## 📁 Input/Output

- **Input**: `tests/<filename>` (default: `tests/questions.json`)
- **Output**: `tests/baseline_record.json`

## ⚠️ Critical Rules

- **NO RAG**: Absolutely no `msearch` or any search tools allowed.
- **NO GOLDEN FILE**: Do not read the ground_truth file.
- **Pure Model Knowledge**: Only use model's internal knowledge.
- **Be Honest**: If unsure, answer "I am not certain about this information".
