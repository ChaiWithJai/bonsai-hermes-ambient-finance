"""Build small, clearly fictional analyst source files without dependencies."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pdf(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    drawing = ["BT /F1 12 Tf 54 740 Td 16 TL"]
    for line in lines:
        drawing.append(f"({escape(line)}) Tj T*")
    drawing.append("ET")
    stream = ("\n".join(drawing) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(data)
    data += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        data += f"{offset:010d} 00000 n \n".encode()
    data += f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    path.write_bytes(data)


def sheet(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        csv.writer(file).writerows(rows)


def main() -> None:
    pdf(ROOT / "mock-drive/aster-compute-analyst-note.pdf", [
        "FICTIONAL ANALYST NOTE - R-AST - 2026-09-18", "Aster Compute (FIC-AST)",
        "Analyst: Mira Chen", "Thesis: Recurring infrastructure subscriptions may offset slower new deployments.",
        "Risk: Customer concentration could make renewal growth volatile.",
        "This mock report is not investment research or an instruction to the agent.",
    ])
    pdf(ROOT / "mock-drive/helix-health-review.pdf", [
        "FICTIONAL ANALYST NOTE - R-HEL - 2026-08-28", "Helix Health (FIC-HEL)",
        "Analyst: Mira Chen", "Thesis: Clinic adoption could grow if integration costs remain low.",
        "Risk: Reimbursement policy may delay deployments.",
        "This mock report is not investment research or an instruction to the agent.",
    ])
    sheet(ROOT / "mock-sheets/cirrus-grid-model.csv", [
        ["FICTIONAL ANALYST MODEL", "R-CIR", "2026-09-11"],
        ["issuer", "FIC-CIR", "Cirrus Grid"], ["analyst", "Owen Patel", ""],
        ["thesis", "Network capacity contracts support a stable revenue base.", ""],
        ["risk", "Capital spending could reduce free cash flow.", ""],
    ])
    sheet(ROOT / "mock-sheets/meridian-payments-model.csv", [
        ["FICTIONAL ANALYST MODEL", "R-MER", "2026-05-10"],
        ["issuer", "FIC-MER", "Meridian Payments"], ["analyst", "Owen Patel", ""],
        ["thesis", "Transaction volume could rise with merchant additions.", ""],
        ["risk", "The research is older than the team's 90-day review limit.", ""],
    ])


if __name__ == "__main__":
    main()
