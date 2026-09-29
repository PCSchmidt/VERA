"""Gate `scaffold_ready`: the schema version in code matches docs/03 and has a changelog line."""

from __future__ import annotations

import re

from _common import block, ok, repo_root_arg


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    doc = args.root / "docs" / "03-interfaces.md"
    code = args.root / "vera" / "schemas" / "__init__.py"
    if not doc.exists():
        block(f"{doc} not found")
    if not code.exists():
        block("vera/schemas/__init__.py not found; the schemas package does not exist yet")

    doc_text = doc.read_text(encoding="utf-8")
    doc_match = re.search(r"^Version\s+(\d+\.\d+)", doc_text, re.MULTILINE)
    if not doc_match:
        block("docs/03-interfaces.md has no 'Version X.Y' line")
    doc_version = doc_match.group(1)

    code_match = re.search(r"""^SCHEMA_VERSION\s*=\s*["'](\d+\.\d+)["']""", code.read_text(encoding="utf-8"), re.MULTILINE)
    if not code_match:
        block("vera/schemas/__init__.py does not define SCHEMA_VERSION = \"X.Y\"")
    code_version = code_match.group(1)

    if code_version != doc_version:
        block(f"schema version mismatch: docs/03 says {doc_version}, code says {code_version}")
    if not re.search(rf"^-\s+{re.escape(doc_version)}\b", doc_text, re.MULTILINE):
        block(f"docs/03 changelog has no line for version {doc_version}")
    ok(f"schema version {doc_version} matches docs/03")


if __name__ == "__main__":
    main()
