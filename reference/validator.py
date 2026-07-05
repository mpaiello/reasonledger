#!/usr/bin/env python3
# Reasonledger v1.0 — reference validator
# Copyright (c) 2026 Michael Patrick Aiello. Licensed under Apache 2.0 (see LICENSE-APACHE).
#
# Checks a Reasonledger document against the v1.0 grammar:
#   - block headers use a recognized block type
#   - @LOGIC blocks declare a valid `basis` (AXIOM | DERIVED | EMPIRICAL)
#   - @TAXONOMY entries use a valid status marker (confirmed | open | denied)
#   - @DERIVE blocks terminate in a forced-conclusion marker (arrow)
#   - @VERIFY results use a valid result code (holds | fails | uncertain)
# and, as warnings, that named references resolve to a defined label.
#
# Usage:  python validator.py FILE.rl [FILE2.rl ...]
# Exit:   0 if no errors (warnings allowed), 1 if any errors, 2 on usage/IO error.

import re
import sys

CONTENT = {"FORMAL", "LOGIC", "DERIVE", "TAXONOMY", "ANCHOR"}
EXCHANGE = {"STATE", "VERIFY", "OUTPUT"}
TRANSFER = {"PROVENANCE", "TRANSFER_REPORT", "DERIVATION_TRACE",
            "SCOPE", "CONFIDENCE", "TRUST_TRANSFORMATION"}
KNOWN = CONTENT | EXCHANGE | TRANSFER

BASIS = {"AXIOM", "DERIVED", "EMPIRICAL"}
STATUS = {"confirmed", "open", "denied"}
RESULT = {"holds", "fails", "uncertain"}
CONCLUSION = "\u2192\u2192"  # the forced-conclusion arrow

HEADER_RE = re.compile(r"^@(?P<type>[A-Z_]+)\b(?P<rest>.*)$")
LABEL_RE = re.compile(r"\[\s*(?P<label>[^\]]*?)\s*\]")
BASIS_RE = re.compile(r"\bbasis\s*:\s*(?P<v>\w+)", re.IGNORECASE)
ENTRY_RE = re.compile(r"^\s*(?P<key>[^:]+?)\s*:\s*(?P<val>[A-Za-z_]+)\s*$")

# reference patterns scanned across block bodies
REF_PATTERNS = {
    "FORMAL": re.compile(r"@FORMAL\[\s*([^\]]+?)\s*\]"),
    "LOGIC": re.compile(r"@LOGIC\[\s*([^\]]+?)\s*\]"),
    "TAXONOMY": re.compile(r"@TAXONOMY\[\s*([^\]]+?)\s*\]"),
    "SCOPE": re.compile(r"@SCOPE\[\s*([^\]]+?)\s*\]"),
    "CONFIDENCE": re.compile(r"@CONFIDENCE\[\s*([^\]]+?)\s*\]"),
}
# derivation refs: §name or §name(3), name must start with a letter (skip §3 section refs)
DERIVE_REF_RE = re.compile(r"\u00a7([A-Za-z]\w*)")


class Block:
    __slots__ = ("type", "label", "header_line", "rest", "body", "body_start")

    def __init__(self, btype, label, header_line, rest):
        self.type = btype
        self.label = label
        self.header_line = header_line
        self.rest = rest
        self.body = []          # list of (line_no, text)
        self.body_start = None


def parse(lines):
    """Split lines (list of str) into Block objects. Line numbers are 1-based."""
    blocks = []
    current = None
    for i, raw in enumerate(lines, start=1):
        m = HEADER_RE.match(raw)
        if m:
            btype = m.group("type")
            rest = m.group("rest")
            lm = LABEL_RE.search(rest)
            label = lm.group("label") if lm else None
            current = Block(btype, label, i, rest)
            blocks.append(current)
        elif current is not None:
            current.body.append((i, raw))
    return blocks


def collect_labels(blocks):
    """Map reference-kind -> set of defined labels."""
    defined = {"FORMAL": set(), "LOGIC": set(), "DERIVE": set(),
               "TAXONOMY": set(), "SCOPE": set(), "CONFIDENCE": set()}
    for b in blocks:
        if b.label is None:
            continue
        lab = b.label.lstrip("\u00a7").strip()  # a label may be written as [§name]
        if b.type in defined:
            defined[b.type].add(lab)
    return defined


def validate(path):
    errors, warnings = [], []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as e:
        return [f"{path}: cannot read file: {e}"], []

    blocks = parse(lines)
    if not blocks:
        warnings.append(f"{path}:0: no Reasonledger blocks found")

    defined = collect_labels(blocks)

    for b in blocks:
        loc = f"{path}:{b.header_line}"

        # 1. recognized block type
        if b.type not in KNOWN:
            errors.append(f"{loc}: unknown block type @{b.type}")
            continue

        # 2. @LOGIC must declare a valid basis
        if b.type == "LOGIC":
            bm = BASIS_RE.search(b.rest)
            if not bm:
                errors.append(f"{loc}: @LOGIC block missing required 'basis:' attribute")
            elif bm.group("v").upper() not in BASIS:
                errors.append(f"{loc}: @LOGIC basis '{bm.group('v')}' not in "
                              f"{{AXIOM, DERIVED, EMPIRICAL}}")

        # 3. @TAXONOMY entries must use a valid status marker
        if b.type == "TAXONOMY":
            for ln, text in b.body:
                em = ENTRY_RE.match(text)
                if em and em.group("val").lower() not in STATUS:
                    errors.append(f"{path}:{ln}: @TAXONOMY status "
                                  f"'{em.group('val')}' not in {{confirmed, open, denied}}")

        # 4. @DERIVE must terminate in a forced-conclusion marker
        if b.type == "DERIVE":
            if not any(CONCLUSION in text for _, text in b.body):
                errors.append(f"{loc}: @DERIVE block has no forced-conclusion marker "
                              f"({CONCLUSION})")

        # 5. @VERIFY results must use a valid result code
        if b.type == "VERIFY":
            for ln, text in b.body:
                em = ENTRY_RE.match(text)
                if em and em.group("val").lower() not in RESULT:
                    # only flag lines that look like a result line (ref : code)
                    errors.append(f"{path}:{ln}: @VERIFY result "
                                  f"'{em.group('val')}' not in {{holds, fails, uncertain}}")

    # 6. reference resolution (warnings)
    for b in blocks:
        body_text = "\n".join(t for _, t in b.body)
        # label of a @VERIFY block is itself a derivation reference, e.g. [§circular_velocity]
        header_refs = b.label if (b.label and b.label.startswith("\u00a7")) else ""
        scan = header_refs + "\n" + body_text
        for kind, pat in REF_PATTERNS.items():
            for name in pat.findall(scan):
                if name.strip() not in defined[kind]:
                    warnings.append(f"{path}:{b.header_line}: unresolved @{kind}[{name}] reference")
        for name in DERIVE_REF_RE.findall(scan):
            if name not in defined["DERIVE"]:
                warnings.append(f"{path}:{b.header_line}: unresolved \u00a7{name} derivation reference")

    return errors, warnings


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: python validator.py FILE.rl [FILE2.rl ...]\n")
        return 2
    total_err = 0
    for path in argv[1:]:
        errors, warnings = validate(path)
        for w in warnings:
            print(f"WARNING  {w}")
        for e in errors:
            print(f"ERROR    {e}")
        if errors:
            total_err += len(errors)
            print(f"FAIL     {path}: {len(errors)} error(s), {len(warnings)} warning(s)")
        else:
            print(f"OK       {path}: valid ({len(warnings)} warning(s))")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
