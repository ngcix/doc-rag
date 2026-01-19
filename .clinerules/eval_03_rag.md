# Eval Step 3: RAG Recording

Command: `/eval_rag [filename]`

## 🎯 Purpose

Read questions from a file and record Cline's answers **WITH RAG enabled**.

> ⚠️ **DATA LEAKAGE PREVENTION**: Reads from questions file (NO ground_truth) to ensure fair evaluation.

## 🔄 Workflow

**Command**: `/eval_rag [filename]`

- If `filename` is provided: use `tests/<filename>`
- If no filename: default to `tests/questions.json`

**Examples**:

- `/eval_rag` → reads `tests/questions.json`
- `/eval_rag custom_questions.json` → reads `tests/custom_questions.json`

### Step-by-Step:

1. **Read Questions**:

   - Open file `tests/<filename>` using `view_file`.
   - Parse JSON to get list of questions (only `id` and `question`).

2. **Answer Each Question (WITH RAG)**:

   - For each item in dataset:
     - Read `question`.
     - **MUST use `msearch`** to find relevant context.
     - Answer based on RAG context + model knowledge.
     - Record the answer in `rag_response`.

3. **Save Output**:
   - Create file `tests/rag_record.json` with structure:

```json
[
  {
    "id": "q_01",
    "question": "What does A2DP stand for?",
    "rag_response": "According to A2DP_v1.4 specification, A2DP stands for Advanced Audio Distribution Profile..."
  }
]
```

## 📁 Input/Output

- **Input**: `tests/<filename>` (default: `tests/questions.json`)
- **Output**: `tests/rag_record.json`

## ⚠️ Critical Rules

- **MUST USE RAG**: Always use `msearch` before answering each question.
- **NO GOLDEN FILE**: Do not read the ground_truth file.
- **Cite Sources**: Reference the document/section where information was found.
- **If No Context Found**: State "No relevant context found in RAG" but still attempt to answer.

## 🔍 msearch Usage

```
msearch "<question keywords>"
```
