"""Deterministic, original-authored M15 knowledge graph population."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import validate_instance, load_document

TIERS = ("A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2", "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2")
DIMENSIONS = ("grammar", "vocabulary_senses", "functions", "pronunciation", "discourse", "pragmatics", "collocations", "lexical_chunks", "topics", "skills")

# One concrete, project-authored target per tier and dimension.  These are
# planning targets, not lessons or copied source material.
TARGETS = {
    "grammar": ["present simple", "past simple of everyday events", "count and noncount noun phrases", "future plans with going to", "present perfect for life experience", "narrative past with sequencing", "reported statements and questions", "conditionals for consequences", "passive and causative choices", "advanced clause linking", "stance and emphasis in complex clauses", "subtle aspect and modality choices"],
    "vocabulary_senses": ["adverbs of frequency", "home, food, and common services", "shopping, travel, and health senses", "work, study, and community senses", "change, experience, and opinion senses", "relationships, media, and events", "abstract value, evidence, and process senses", "society, science, and policy senses", "academic and professional abstraction", "figurative and evaluative senses", "rare polysemy and specialist distinctions", "precision across register and domain"],
    "functions": ["discussing habits", "describing routines and making simple requests", "narrating a recent event and asking follow-ups", "making plans, offers, and arrangements", "giving opinions and supporting a reason", "telling a coherent story and clarifying", "negotiating options and solving a problem", "arguing a position and qualifying claims", "leading a formal discussion and synthesizing", "evaluating proposals and managing disagreement", "interpreting implied intent in debate", "adapting persuasive communication to audience"],
    "pronunciation": ["final consonants and clear word stress", "sentence stress in short routine phrases", "past-tense endings and thought groups", "weak forms in planned speech", "contrastive stress for meaning", "intonation for narrative structure", "connected speech across word boundaries", "rhythm and reduction in extended turns", "prosodic framing of complex claims", "fine-grained prominence and stance", "variety-aware phonological flexibility", "controlled expressive prosody"],
    "discourse": ["linking sentences with and, but, and because", "ordering a short description", "sequencing a personal account", "organizing plans and reasons", "cohesive paragraphs with reference", "topic development across a story", "claim-evidence-counterpoint structure", "signposting a multi-part argument", "synthesizing sources and viewpoints", "managing long-form exposition", "rhetorical framing and inference", "genre-sensitive discourse architecture"],
    "pragmatics": ["polite greetings and personal boundaries", "requests with appropriate directness", "apologies, thanks, and repair", "offers and invitations with social fit", "agreement and disagreement tactfully", "register choices in unfamiliar settings", "hedging advice and negotiating face", "power, distance, and indirectness", "institutional politeness and stance", "irony, implication, and rapport", "cross-cultural interpretation of intent", "strategic identity and audience alignment"],
    "collocations": ["make and do with daily activities", "take, have, and get in services", "set phrases for travel and health", "plan, attend, and achieve goals", "reach, raise, and express an opinion", "build, maintain, and damage relationships", "pose, assess, and address a problem", "conduct, implement, and evaluate policy", "draw, yield, and account for conclusions", "deeply, highly, and broadly modified claims", "fine lexical selection in formal prose", "domain-specific combinatorial precision"],
    "lexical_chunks": ["How are you? and basic social openings", "Could you ...? and everyday request frames", "I went ... and event-reporting frames", "Would you like ...? and arrangement frames", "In my view ... because ... opinion frames", "What I mean is ... repair frames", "On the one hand ... negotiation frames", "The evidence suggests ... argument frames", "It is worth noting ... academic frames", "That said ... concession frames", "Not so much X as Y ... reframing frames", "Taken together ... synthesis frames"],
    "topics": ["daily routines", "food, shopping, and neighborhood", "health, transport, and local services", "study, work, and future plans", "experiences, media, and relationships", "community events and personal change", "technology, environment, and decision-making", "society, education, and public policy", "research, institutions, and global issues", "culture, ethics, and competing values", "specialist knowledge and uncertainty", "complex systems, identity, and worldviews"],
    "skills": ["understand and produce short routine exchanges", "handle predictable everyday transactions", "follow and retell a simple event", "coordinate a plan in clear speech", "explain an opinion in connected language", "participate in extended familiar discussion", "evaluate information and respond strategically", "sustain an evidence-based interaction", "integrate sources in a formal task", "control precision across demanding tasks", "interpret nuanced expert communication", "create and critique sophisticated communication"],
}

def _node_id(tier: str, dimension: str) -> str:
    return f"kg_{tier.lower().replace('.', '_')}_{dimension}"

def build_population() -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    for ti, tier in enumerate(TIERS):
        for di, dimension in enumerate(DIMENSIONS):
            node_id = _node_id(tier, dimension)
            prerequisites: list[str] = []
            edges: list[dict[str, str]] = []
            # Every dimension develops cumulatively through the tier sequence.
            if ti:
                prior = _node_id(TIERS[ti - 1], dimension)
                prerequisites.append(prior)
                edges.append({"source": prior, "target": node_id, "relation": "PREREQUISITE"})
            node = {"schema_version": "1.0", "record_type": "m15_knowledge_graph_node", "id": node_id, "tier": tier, "dimension": dimension, "name": TARGETS[dimension][ti], "description": f"Original project-authored curriculum target: {TARGETS[dimension][ti]}. This {tier} target is a planning node, not lesson content.", "prerequisites": prerequisites, "dependency_edges": edges, "status": "DRAFT", "authorship": "PROJECT_AUTHORED"}
            nodes.append(node)
    # Explicit cross-dimension learning chain requested by the curriculum contract.
    chain = [(_node_id("A1.1", "grammar"), _node_id("A1.1", "vocabulary_senses")), (_node_id("A1.1", "vocabulary_senses"), _node_id("A1.1", "topics")), (_node_id("A1.1", "topics"), _node_id("A1.1", "functions"))]
    by_id = {n["id"]: n for n in nodes}
    for source, target in chain:
        by_id[target]["prerequisites"].append(source)
        by_id[target]["dependency_edges"].append({"source": source, "target": target, "relation": "PREREQUISITE"})
    value = {"schema_version": "1.0", "record_type": "m15_knowledge_graph_population", "population_id": "PENDING", "nodes": nodes, "tiers": list(TIERS), "dimensions": list(DIMENSIONS), "content_status": "UNREVIEWED", "fixture_only": True, "external_content_used": False}
    value["population_id"] = "kgpop_" + sha256_json({k: v for k, v in value.items() if k != "population_id"})
    validate_instance(value, "m15-knowledge-graph-population")
    return value

def validate_population(value: dict[str, Any]) -> dict[str, Any]:
    validate_instance(value, "m15-knowledge-graph-population")
    if len(value["nodes"]) != 120 or len({n["id"] for n in value["nodes"]}) != 120:
        raise ValueError("population must contain 120 unique nodes")
    if value != build_population():
        raise ValueError("population is not the canonical deterministic population")
    return value

def run(output: Path) -> Path:
    output = Path(output)
    if output.exists(): raise FileExistsError(f"refusing to overwrite immutable population: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    population = build_population()
    tmp = output.with_name("." + output.name + ".tmp")
    try:
        tmp.write_text(json.dumps(population, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"); tmp.replace(output)
        digest = sha256_json(population)
        manifest = {"schema_version":"1.0","record_type":"m15_knowledge_graph_run_manifest","run_id":"kg_run_"+digest,"population_sha256":digest,"node_count":120,"tier_count":12,"dimension_count":10,"result":"PASS","fixture_only":True,"external_content_used":False}
        mp = output.with_name("m15-run-manifest.json")
        if mp.exists(): raise FileExistsError(f"refusing to overwrite immutable manifest: {mp}")
        mp.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"); validate_instance(manifest, "m15-knowledge-graph-run-manifest")
    finally:
        if tmp.exists(): tmp.unlink()
    return output
