"""
visualize.py — render a reasoning trail as an inspectable "ledger view".

Takes a parsed trail (from check.parse_rl) plus mechanical detections and produces a
self-contained HTML audit timeline: one card per hop, with constraints, derivation
conclusions, claims (status-colored), verifications, and trust, and every mechanically
detected anomaly highlighted at the hop and item where it occurs.

This is the venture proof-of-concept and the paper figure. It uses no external assets.
"""

import html

_LEGEND = {
    "constraint_drift": ("#b45309", "constraint drift"),
    "status_inflation": ("#b91c1c", "status inflation"),
    "trust_laundering": ("#7c3aed", "trust laundering"),
    "dangling_reference": ("#0e7490", "dangling reference"),
    "verification_inconsistency": ("#be123c", "verification inconsistency"),
}
_STATUS_COLOR = {"confirmed": "#166534", "open": "#a16207", "denied": "#991b1b"}


def _esc(s):
    return html.escape(str(s))


def render_html(parsed, detections, title="Reasoning Ledger", subtitle=""):
    by_hop = {}
    for d in detections:
        by_hop.setdefault(d["hop"], []).append(d)

    def anomaly_badge(hop_n, item):
        out = ""
        for d in by_hop.get(hop_n, []):
            if str(d["item"]) == str(item):
                color, label = _LEGEND.get(d["error_class"], ("#b91c1c", d["error_class"]))
                out += (f'<span class="badge" style="background:{color}">'
                        f'{_esc(label)}</span>')
        return out

    parts = []
    parts.append(f"""<!doctype html><html><head><meta charset="utf-8">
<title>{_esc(title)}</title><style>
:root{{--ink:#1c1917;--mut:#78716c;--line:#e7e5e4;--bg:#fafaf9;--card:#ffffff}}
*{{box-sizing:border-box}}
body{{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);
background:var(--bg);margin:0;padding:32px}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:20px;margin:0 0 2px}} .sub{{color:var(--mut);margin:0 0 20px}}
.summary{{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:12px 16px;margin-bottom:20px}}
.hop{{position:relative;background:var(--card);border:1px solid var(--line);
border-radius:10px;padding:16px 18px;margin:0 0 14px}}
.hop.flag{{border-color:#fca5a5;box-shadow:0 0 0 1px #fecaca inset}}
.hop h2{{font-size:13px;letter-spacing:.03em;text-transform:uppercase;color:var(--mut);
margin:0 0 10px}}
.row{{display:flex;gap:8px;padding:3px 0;border-top:1px dashed var(--line)}}
.row:first-of-type{{border-top:none}}
.k{{color:var(--mut);min-width:150px;flex:0 0 150px}}
.v{{flex:1}}
.status{{font-weight:600}}
.badge{{display:inline-block;color:#fff;font-size:11px;font-weight:600;border-radius:5px;
padding:1px 7px;margin-left:8px;vertical-align:middle}}
.legend{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px;font-size:12px;color:var(--mut)}}
.legend span::before{{content:"";display:inline-block;width:10px;height:10px;border-radius:3px;
margin-right:5px;vertical-align:middle;background:var(--dot)}}
code{{background:#f5f5f4;border-radius:4px;padding:0 4px}}
</style></head><body><div class="wrap">""")
    parts.append(f"<h1>{_esc(title)}</h1><p class='sub'>{_esc(subtitle)}</p>")

    n_flags = len(detections)
    verdict = ("no anomalies detected" if n_flags == 0
               else f"{n_flags} anomaly{'ies' if n_flags != 1 else ''} detected by mechanical audit")
    parts.append(f"<div class='summary'><b>Mechanical audit:</b> {_esc(verdict)}. "
                 f"Highlights mark where the ledger's cross-hop consistency broke.</div>")

    for hop in parsed["hops"]:
        n = hop["n"]
        flagged = "flag" if n in by_hop else ""
        parts.append(f"<div class='hop {flagged}'><h2>Hop {n}</h2>")
        for con in hop["constraints"]:
            parts.append(f"<div class='row'><div class='k'>constraint [{_esc(con['id'])}]</div>"
                         f"<div class='v'>{_esc(con['text'])} "
                         f"<code>{_esc(con.get('basis'))}</code>{anomaly_badge(n, con['id'])}</div></div>")
        for d in hop["derivations"]:
            parts.append(f"<div class='row'><div class='k'>derivation [{_esc(d['id'])}]</div>"
                         f"<div class='v'>&rarr;&rarr; {_esc(d.get('conclusion'))}"
                         f"{anomaly_badge(n, d['id'])}</div></div>")
        for cl in hop["claims"]:
            col = _STATUS_COLOR.get(cl["status"], "#57534e")
            parts.append(f"<div class='row'><div class='k'>claim [{_esc(cl['id'])}]</div>"
                         f"<div class='v'><span class='status' style='color:{col}'>"
                         f"{_esc(cl['status'])}</span>{anomaly_badge(n, cl['id'])}</div></div>")
        for v in hop["verifications"]:
            res = ", ".join(f"{r['step']}:{r['result']}" for r in v["results"])
            parts.append(f"<div class='row'><div class='k'>verify [{_esc(v['deriv'])}]</div>"
                         f"<div class='v'>{_esc(res)}{anomaly_badge(n, v['deriv'])}</div></div>")
        for t in hop["trust"]:
            parts.append(f"<div class='row'><div class='k'>trust [{_esc(t['item'])}]</div>"
                         f"<div class='v'>{_esc(t['label'])}{anomaly_badge(n, t['item'])}</div></div>")
        parts.append("</div>")

    parts.append("<div class='legend'>")
    for _, (color, label) in _LEGEND.items():
        parts.append(f"<span style='--dot:{color}'>{_esc(label)}</span>")
    parts.append("</div>")

    parts.append("</div></body></html>")
    return "".join(parts)


if __name__ == "__main__":
    from canonical import seed_chains
    from render import render_rl
    from inject import constraint_drift
    from check import parse_rl, check
    corrupt, gt = constraint_drift(seed_chains()[0])
    trail = render_rl(corrupt)
    parsed = parse_rl(trail)
    dets = check(trail, "rl")
    open("/tmp/led.html", "w").write(render_html(parsed, dets, "Reasoning Ledger", "demo"))
    print("wrote /tmp/led.html; detections:", dets)
