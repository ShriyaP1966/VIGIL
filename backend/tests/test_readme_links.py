"""The README is the first thing judges read: its links and images must resolve, screenshots need alt text, the table of
contents must point at real headings, and the guided tour must describe things that exist in the hosted demo's data."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")
DEMO = ROOT / "frontend" / "public" / "demo-data"
LIVE = "https://vigil-demo-eta.vercel.app"

IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)")
HREF = re.compile(r'href="([^"]+)"')


def slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens."""
    text = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s", "-", text)


HEADINGS = {slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", README, re.M)}


def targets():
    for m in IMAGE.finditer(README):
        yield "image", m.group(2)
    for m in LINK.finditer(README):
        yield "link", m.group(2)
    for m in HREF.finditer(README):
        yield "href", m.group(1)


def test_every_relative_link_and_image_points_at_a_file_in_the_repo():
    missing = []
    for kind, target in targets():
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = target.split("#")[0]
        if path and not (ROOT / path).exists():
            missing.append(f"{kind}: {target}")
    assert not missing, missing


def test_every_anchor_in_the_readme_matches_a_heading():
    bad = [t for _, t in targets() if t.startswith("#") and t[1:] not in HEADINGS]
    assert not bad, f"anchors without a heading: {bad} (headings: {sorted(HEADINGS)})"


def test_every_image_has_alt_text():
    empty = [target for alt, target in ((m.group(1), m.group(2)) for m in IMAGE.finditer(README)) if not alt.strip()]
    assert not empty, empty
    assert len(IMAGE.findall(README)) >= 10                   # badges, overview, eight screenshots, the chart


def test_external_links_are_only_the_ones_we_expect_and_none_is_a_search_redirect():
    hosts = {re.match(r"https?://([^/:]+)", t).group(1) for _, t in targets() if t.startswith("http")}
    assert hosts <= {"vigil-demo-eta.vercel.app", "img.shields.io", "github.com", "localhost"}, hosts
    assert "google.com" not in README


def test_the_readme_has_a_table_of_contents_and_the_licence_badge_and_no_video_placeholder():
    assert "**Contents:**" in README
    assert "Video: coming" not in README and "https://…" not in README       # the owner adds the real link later
    assert "[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)" in README
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_the_top_of_the_readme_is_short_and_the_collapsed_sections_exist():
    top = README.split("## Try it in 2 minutes")[0]
    assert len(top.splitlines()) <= 35                        # description, summary, links and contents fit above the fold
    assert README.count("<details>") == README.count("</details>") >= 5
    for needle in ("Architecture", "Full benchmark tables", "API at a glance", "Privacy and safety notes"):
        assert needle in README


def test_there_is_exactly_one_mermaid_diagram_and_it_is_well_formed():
    blocks = re.findall(r"```mermaid\n(.*?)```", README, re.S)
    assert len(blocks) == 1
    body = blocks[0]
    assert body.startswith("flowchart LR")
    assert body.count("subgraph") == body.count("\n  end") == 2       # every subgraph is closed
    assert body.count("[") == body.count("]") and body.count("(") == body.count(")") and body.count("{") == body.count("}")


def test_the_ai_assistants_section_names_the_three_stages_and_keeps_the_honesty_statements():
    section = README.split("## Built with AI coding assistants")[1].split("## More detail")[0]
    flat = " ".join(section.split())                                   # line breaks do not matter
    for hedge in ("according to the owner", "owner's account", "do not record a detail"):
        assert hedge not in flat, hedge                                    # the statements are made flatly
    for needle in ("drafted with Claude in a chat", "Google Antigravity", "using Gemini and Claude Sonnet 4.6", "Phase 0 and most of Phase 1",
                   "hand-typed demo values", "a `.gitignore` rule that had kept the ORM package out of git", "(log, Session 2)",
                   "Claude Code", "Phases 2 to 7", "CLAUDE.md", "DEVELOPMENT_LOG.md", "Every metric comes from a script",
                   "pre-registered", "drafted by a different language model (not Claude)", "reviewed, edited and labelled by the owner",
                   "rather than taking this README's word"):
        assert needle in flat, needle


def test_the_limitations_and_ai_note_sections_are_easy_to_find():
    for heading in ("limitations-please-read", "built-with-ai-coding-assistants"):
        assert heading in HEADINGS
        assert f"#{heading}" in README or heading == "built-with-ai-coding-assistants"
    assert "[Limitations](#limitations-please-read)" in README and "[Built with AI coding assistants](#built-with-ai-coding-assistants)" in README


def test_the_readme_makes_no_claims_the_code_cannot_back_up():
    lowered = README.lower()
    for phrase in ("production-ready", "production ready", "real-time call protection", "guilty", "criminal",
                   "state-of-the-art", "accurate in the real world"):
        assert phrase not in lowered, phrase
    # "confirmed campaign" may appear only in the sentence that says nothing is ever called that automatically
    assert lowered.count("confirmed campaign") == lowered.count("called a confirmed campaign automatically")
    assert "does not listen to calls" in README or "does not listen to or intercept" in README or "VIGIL does not listen" in README


# ---------------------------------------------------------------------------------------------
# the guided tour is checked against the hosted demo's own data
# ---------------------------------------------------------------------------------------------

def load(name):
    return json.loads((DEMO / name).read_text(encoding="utf-8"))


def test_tour_the_graph_has_a_blue_an_amber_and_a_disputed_link_exactly_as_described():
    expect = {1: ("OBSERVED_MATCH", 1, 2), 2: ("CANDIDATE_ASSOCIATION", 1, 4), 3: ("DISPUTED_ASSOCIATION", 3, 5), 4: ("DISPUTED_ASSOCIATION", 6, 7)}
    edges = {e["id"]: e for e in load("graph.json")["edges"]}
    for assoc_id, (status, a, b) in expect.items():
        edge = edges[f"assoc_{assoc_id}"]
        assert edge["type"] == status and {edge["source"], edge["target"]} == {f"incident_{a}", f"incident_{b}"}, assoc_id
        assert f"{LIVE}/graph?assoc={assoc_id}" in README or f"`?assoc={assoc_id}`" in README
    assert [c["rule_id"] for c in load("association_3.json")["counter_evidence"] if c["severity"] == "HIGH"] == ["CE-3"]
    assert [c["rule_id"] for c in load("association_4.json")["counter_evidence"] if c["severity"] == "HIGH"] == ["CE-1"]
    assert load("association_2.json")["match_type"] == "PLAYBOOK" and load("association_1.json")["match_type"] == "EXACT_IDENTIFIER"


def test_tour_two_unreviewed_hypotheses_and_the_first_has_three_incidents():
    campaigns = load("campaigns.json")
    assert len(campaigns) == 2
    assert all(c["status"] == "HYPOTHESIS_UNREVIEWED" for c in campaigns)
    assert len(load("campaign_1.json")["members"]) == 3


def test_tour_the_scenario_lab_slider_goes_from_three_observed_links_to_three_candidates():
    r0, r1 = load("scenario_digital_arrest_cbi__r0.json"), load("scenario_digital_arrest_cbi__r100.json")
    assert (r0["summary"]["observed_links"], r0["summary"]["candidate_links"]) == (3, 0)
    assert (r1["summary"]["observed_links"], r1["summary"]["candidate_links"]) == (0, 3)
    assert r0["title"] == "Digital arrest: central-agency impersonation"
    assert "Digital arrest: central-agency impersonation" in README


def test_tour_there_are_nine_cases_an_incident_with_a_timeline_and_the_injection_script():
    assert len(load("incidents.json")) == 9 and "Nine synthetic cases" in README and "9 synthetic incidents" in README
    assert load("incident_1.json")["evidence_items"][0]["utterances"]
    scripts = {s["name"]: s for s in load("simulations.json")}
    assert scripts["injection_attempt"]["title"] == "Scam call with an injected instruction"
    assert "Scam call with an injected instruction" in README


@pytest.mark.parametrize("path", ["/graph", "/campaigns", "/scenarios", "/incidents/1", "/simulated-call"])
def test_tour_deep_links_are_real_routes(path):
    from_the_router = (ROOT / "frontend" / "src" / "router" / "routes.ts").read_text(encoding="utf-8")
    assert f"'{path}'" in from_the_router or path == "/incidents/1"        # /incidents/<id> is a pattern route
    assert f"{LIVE}{path}" in README
