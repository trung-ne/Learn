"""M16 A1 outline blueprint generation and validation."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from english_master.schema_validation import validate_instance, load_document
from english_master.lesson_generation.canonical import sha256_json

DIMS=("grammar","vocabulary_senses","functions","pronunciation","discourse","pragmatics","collocations","lexical_chunks","topics","skills")
TIERS=("A1.1","A1.2")

def build(population:dict[str,Any], edition="m16a1-v1") -> dict[str,Any]:
    nodes={n["id"]:n for n in population["nodes"]}
    for tier in TIERS:
        for d in DIMS:
            if f"kg_{tier.lower().replace('.','_')}_{d}" not in nodes: raise ValueError(f"missing M15 target: {tier}/{d}")
    units=[]; lessons=[]; reviews=[]; assessments=[]
    for u in range(1,11):
        tier=TIERS[(u-1)//5]; uid=f"{edition}-a1-u{u:02d}"
        lids=[]
        for l in range(1,6):
            lid=f"{uid}-l{l:02d}"; lids.append(lid)
            targets=[{"node_id":f"kg_{tier.lower().replace('.','_')}_{d}","dimension":d} for d in DIMS]
            prior=[]
            if l>1: prior=[f"{uid}-l{l-1:02d}"]
            elif u>1: prior=[f"{edition}-a1-u{u-1:02d}-l05"]
            rid=f"{edition}-a1-r{u:02d}"
            lessons.append({"id":lid,"unit_id":uid,"tier":tier,"sequence":l,"title":f"{tier} learning focus {u}.{l}","objectives":[f"Use the {tier} targets in a controlled learning sequence."],"targets":targets,"prerequisite_lesson_ids":prior,"review_ids":[rid],"assessment_ids":[f"{edition}-a1-assess-unit-{u:02d}"]})
        units.append({"id":uid,"tier":tier,"sequence":u,"title":f"{tier} Unit {u}","lesson_ids":lids,"assessment_ids":[f"{edition}-a1-assess-unit-{u:02d}"]})
        reviews.append({"id":f"{edition}-a1-r{u:02d}","tier":tier,"placement_after_lesson_id":lids[-1],"target_lesson_ids":lids,"target_dimensions":list(DIMS)})
        assessments.append({"id":f"{edition}-a1-assess-unit-{u:02d}","kind":"unit_check","tier":tier,"placement_after_unit_id":uid,"assessed_lesson_ids":lids,"target_dimensions":list(DIMS)})
    for tier, u in zip(TIERS,(5,10)):
        uid=f"{edition}-a1-u{u:02d}"
        ls=[x["id"] for x in lessons if x["tier"]==tier]
        assessments.append({"id":f"{edition}-a1-assess-tier-{u:02d}","kind":"tier_check","tier":tier,"placement_after_unit_id":uid,"assessed_lesson_ids":ls,"target_dimensions":list(DIMS)})
    return {"schema_version":"1.0","record_type":"m16_a1_curriculum_blueprint","edition":edition,"status":"OUTLINE_ONLY","source_population_id":population["population_id"],"source_population_sha256":sha256_json(population),"tiers":list(TIERS),"units":units,"lessons":lessons,"reviews":reviews,"assessments":assessments}

def validate(value:dict[str,Any], population:dict[str,Any])->dict[str,Any]:
    validate_instance(value,"m16-a1-curriculum-blueprint")
    expected=build(population,value["edition"])
    if value != expected: raise ValueError("blueprint is not canonical or is drifted from M15 population")
    return value

def run(population_path:Path, output:Path)->Path:
    pop=load_document(population_path); validate_instance(pop,"m15-knowledge-graph-population")
    value=build(pop)
    if output.exists(): raise FileExistsError(f"refusing to overwrite immutable blueprint: {output}")
    output.parent.mkdir(parents=True,exist_ok=True); tmp=output.with_name("."+output.name+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8"); tmp.replace(output)
    return output

def main() -> int:
    import argparse
    p=argparse.ArgumentParser(description="Build or validate the M16 A1 outline blueprint")
    s=p.add_subparsers(dest="command",required=True)
    b=s.add_parser("build"); b.add_argument("population",type=Path); b.add_argument("output",type=Path)
    v=s.add_parser("validate"); v.add_argument("population",type=Path); v.add_argument("blueprint",type=Path)
    a=p.parse_args(); pop=load_document(a.population)
    if a.command == "build": run(a.population,a.output)
    else: validate(load_document(a.blueprint),pop)
    return 0

if __name__ == "__main__": raise SystemExit(main())
