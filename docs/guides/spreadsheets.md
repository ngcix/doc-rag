# Spreadsheets

Large workbooks such as channel plans are matrices: one row per entity
(country), one column per attribute (channel), with group headers spread over
several merged header rows. Splitting the rows as plain text loses the headers,
so a chunk like `Greece … Yes indoor only Yes …` no longer says which channel
each value belongs to.

SpecRAG reads `.xlsx` and `.csv` files as tables instead.

## Table detection

- A table starts where two or more header cells are merged vertically; the
  merge height is the number of header rows and the merged columns are the row
  label columns (`#`, country, codes). A sheet can hold several stacked tables.
- Without such merges, the first row with three or more distinct values is a
  one-row header (CSV files always use their first row).
- Group headers written once ("U-NII-1") apply to the columns on their right
  up to an empty separator column. Each value column gets a header path such
  as `5GHz CHANNEL PLAN › U-NII-2C › 5720 › 144`.
- Rows that fill too few distinct label values (footnotes, URLs, remarks) are
  kept as sheet notes instead of records.
- Label columns without a heading are named by their letter (`column D`).

## Chunks

One chunk per record, repeating the file, sheet and row label, then each value
with its header path. Neighbouring columns with the same header prefix and the
same value are merged and their last header level is listed:

```text
plan.xlsx › 5GHz
#: 10 | 국가 이름(Country) 1): 그리스 / Greece | column D: 300 | Country Code (alpha-3): GRC | Country Code (alpha-2): GR
5GHz CHANNEL PLAN › U-NII-1 › 5180–5240 › 36, 40, 44, 48: Yes indoor only
5GHz CHANNEL PLAN › U-NII-2C › 5720 › 144: No
```

Chunk metadata includes `sheet`, `table`, `row` and `row_label`. Notes become
`<file> › <sheet> › notes` chunks.

## Exact lookup

Every record cell is also stored in `tables.sqlite` beside the FAISS index, so
an agent can read a value without relying on search ranking:

```text
GET /api/v1/tables/lookup?row=GR&column=144&sheet=5GHz
GET /api/v1/tables
```

```bash
specrag lookup --row GR --column 144 --sheet 5GHz
specrag tables
```

`row` matches any cell of a row exactly (case-insensitive), falling back to a
substring of the label cells; `column` matches one header level exactly,
falling back to a substring of the header path. The response reports which
mode matched.

## Limits

- `.xls` files are still read as plain rows.
- Formula cells use the value cached by Excel when the file was last saved.
- Vertical merges inside the data area that start on the same row in two or
  more columns are read as a new table header.

On `Samsung_WLAN_Channel_Plan_for_Mobile_ver.2.9.1.xlsx` (16 sheets) this yields
1,383 chunks and about 23,000 cells in under 4 seconds.
