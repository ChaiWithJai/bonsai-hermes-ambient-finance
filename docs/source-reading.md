# Inspect the analyst evidence

The position tool returns the report catalog alongside the source document. PDF text includes page numbers, and CSV contents include row numbers. A SHA-256 hash identifies the file that was read. The catalog summary is retained separately so a reviewer can see when it disagrees with the document.

Install Poppler before using PDF sources. On macOS, run `brew install poppler`; on Ubuntu, install `poppler-utils`. The tool uses `pdftotext` from the MCP process's PATH. An extraction failure is an error, rather than a fallback to the catalog summary. Scanned pages without extractable text require OCR, which is not implemented.

With the local model, proxy and Hermes profile running, ask:

> Read the actual analyst source documents for FIC-AST and FIC-CIR. For each position, quote its thesis and risk with a PDF page or CSV row citation. Distinguish extracted document contents from the catalog summary, and report whether they agree. Do not calculate an allocation, save a draft, or claim an investment decision.

In the [recorded baseline](../evidence/source-read-session.json), the agent cited Aster's thesis and risk on PDF page 1 and Cirrus's thesis and risk in CSV rows 4 and 5. It reported that the extracted text agreed with the catalog. The [manifest](../evidence/source-read-manifest.json) records the code, instructions and source hashes.

A separate [development case](../evidence/source-conflict-session.json) changed Cirrus's source risk while preserving the catalog. The agent identified the disagreement and asked for reconciliation. That case also split the changed text across CSV cells because the replacement included an unquoted comma. It establishes observed conflict detection on that input, not a clean single-cell comparison. Repeated source reads increased the model work.

The scheduled calculation now includes report-file hashes in its source record. A historical work item created before that change lacks those hashes, so its source snapshot cannot be established from the new document read alone. The recorded source-reading runs were direct Hermes requests, not new scheduled runs. Neither received human investment review.
