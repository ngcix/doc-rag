# Tagging

Tags are short user-supplied keywords that become part of one indexed item's
searchable content.

When a tag changes, SpecRAG:

1. Resolves the chunk/image id.
2. Builds updated content from original text plus tags.
3. Calls the remote embedding service for one new vector.
4. Replaces the item in FAISS and persists metadata.

## Commands

```bash
specrag listtag <doc_id>
specrag addtag <doc_id> <tag>
specrag removetag <doc_id> <tag>
specrag resettags <doc_id>
```

Examples:

```bash
specrag listtag HID_v1.1.1.pdf_p30
specrag addtag HID_v1.1.1.pdf_p30 "security diagram"
specrag removetag HID_v1.1.1.pdf_p30 "security diagram"
specrag resettags HID_v1.1.1.pdf_p30
```

CLI responses are JSON and include the updated tag state and embedding time when
the item was re-embedded.

## Original vs user tags

| Type | Source | Removable |
| --- | --- | --- |
| Original | Auto-extracted captions such as `Figure 4.1` or `Table 2`. | No |
| User | Added through `addtag`. | Yes |

## Tag boosting

For image items, tags are repeated in the vectorization text to make exact tag
queries more likely to retrieve the inspected image/page.

Use specific phrases:

| Better | Avoid |
| --- | --- |
| `authentication flow` | `important` |
| `state machine` | `diagram` |
| `bluetooth security` | `tag1` |

## Operational notes

- The embedding service must be reachable.
- The FAISS store allows one writer per data volume.
- For many corpus-wide tag changes, consider scripting them during a maintenance
  window and re-running search quality checks.
