# Eval Step 3: RAG Recording

Command: `/eval_rag`

---

## 🚫 STRICTLY FORBIDDEN - READ THIS FIRST 🚫

**YOU MUST NOT:**

- Create any `.py` file
- Create any script file
- Use `python -c`
- Use heredoc `<<`
- Create `run_all_rag.py`
- Create `scripts/` folder
- Create any automation
- Use `ask_followup_question`
- Process multiple questions in one step

**IF YOU THINK**: "I should create a script to process all questions"
**THEN**: You are WRONG. Stop. Read below.

---

## ✅ WHAT YOU MUST DO

You are Cline, an AI agent. You have tools. Use them DIRECTLY.

### Tool 1: run_command

```
.venv\Scripts\python.exe -m src.main msearch "your query"
```

### Tool 2: view_file

```
view_file process/output/query_YYYYMMDD_HHMMSS.json
```

### Tool 3: write_to_file

```
write_to_file tests/rag_record.json
```

---

## 📋 EXACT PROCEDURE (Follow This Literally)

### STEP A: Read questions.json

```
Tool: view_file
Path: tests/questions.json
```

→ You now see all questions.

### STEP B: Process Question 1

```
Tool: run_command
Command: .venv\Scripts\python.exe -m src.main msearch "keywords from question 1"
```

Wait for output.

```
Tool: view_file
Path: process/output/query_*.json (the latest one)
```

Read the RAG context.

**Think**: Based on RAG context, what is the answer?

```
Tool: write_to_file
Path: tests/rag_record.json
Content:
[
  {
    "id": 1,
    "question": "...",
    "rag_response": "Your answer based on RAG context"
  }
]
```

### STEP C: Process Question 2

Repeat STEP B for question 2.
After getting answer, UPDATE rag_record.json to add question 2.

### STEP D: Continue

Repeat for questions 3, 4, 5, ...

---

## 📝 EXAMPLE SESSION

**Turn 1:**

- run_command: msearch "A2DP scope definition"
- view_file: process/output/query_20260119_114500.json
- write_to_file: tests/rag_record.json with [{ id: 1, ... }]

**Turn 2:**

- run_command: msearch "A2DP dependency profiles"
- view_file: process/output/query_20260119_114510.json
- write_to_file: tests/rag_record.json with [{ id: 1, ... }, { id: 2, ... }]

**Turn 3:**

- run_command: msearch "advanced audio vs bluetooth audio"
- ...

---

## ⚠️ REMEMBER

- ONE question per turn
- Use YOUR agent tools
- NO scripts
- NO automation
- NO asking user for permission to continue
- Just DO IT step by step
