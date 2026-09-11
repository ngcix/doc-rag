# Knowledge

Knowledge is a longer annotation for one indexed item. It is useful when a
person or a vision-capable agent inspects a rendered page and can add a clearer
description than the raw extracted text.

## Commands

```bash
specrag addknowledge <identifier> <knowledge_text>
specrag updateknowledge <identifier> <knowledge_text>
specrag getknowledge <identifier>
```

`identifier` can be a chunk id or an image path that resolves to a stored item.

Examples:

```bash
specrag addknowledge HID_p42 "This page shows the Bluetooth connection state machine."
specrag updateknowledge HID_p42 "Corrected description of the state transitions."
specrag getknowledge HID_p42
```

## Behavior

When knowledge changes, SpecRAG:

1. Loads the item's current content and metadata.
2. Appends or replaces the `Knowledge:` section.
3. Calls the remote embedding service for the updated content.
4. Replaces the item in FAISS and saves metadata.

CLI responses are JSON.

## Tags vs knowledge

| Need | Use |
| --- | --- |
| Short keywords for retrieval | Tags |
| Detailed explanation or correction | Knowledge |
| A vision model's description of an image | Knowledge |
| Category labels shared by many items | Tags |

## Good knowledge text

- Describe what is visible or stated in the source.
- Include important protocol names, figure names and state names.
- Mention uncertainty or corrections explicitly.
- Keep it concise enough to stay useful in retrieval context.

Example:

```bash
specrag addknowledge doc_id "
This diagram shows the authentication flow between the host and device.
Main states: idle, challenge, response validation and authenticated.
The timeout branch returns the flow to idle.
"
```
