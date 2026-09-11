"""M16 A1 outline blueprint generation and validation."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from english_master.schema_validation import validate_instance, load_document
from english_master.lesson_generation.canonical import sha256_json
from english_master.knowledge_graph.service import validate_population

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

def _unique_by_id(records:list[dict[str,Any]], kind:str)->dict[str,dict[str,Any]]:
    by_id={record["id"]:record for record in records}
    if len(by_id)!=len(records): raise ValueError(f"duplicate {kind} IDs")
    return by_id

def validate(value:dict[str,Any], population:dict[str,Any])->dict[str,Any]:
    """Validate M16 references and ordering without requiring builder equality."""
    validate_instance(value,"m16-a1-curriculum-blueprint")
    validate_population(population)
    if value["source_population_id"]!=population["population_id"]:
        raise ValueError("blueprint source population ID does not match M15 population")
    if value["source_population_sha256"]!=sha256_json(population):
        raise ValueError("blueprint source population hash does not match M15 population")

    population_nodes={node["id"]:node for node in population["nodes"]}
    units=_unique_by_id(value["units"],"unit")
    lessons=_unique_by_id(value["lessons"],"lesson")
    reviews=_unique_by_id(value["reviews"],"review")
    assessments=_unique_by_id(value["assessments"],"assessment")

    unit_order:dict[str,int]={}
    for unit in units.values():
        if unit["tier"] not in TIERS:
            raise ValueError(f"unit {unit['id']} has unsupported tier {unit['tier']}")
        sequence=unit["sequence"]
        if sequence in unit_order.values():
            raise ValueError(f"duplicate unit sequence: {sequence}")
        unit_order[unit["id"]]=sequence
        if len(unit["lesson_ids"])!=len(set(unit["lesson_ids"])):
            raise ValueError(f"unit {unit['id']} has duplicate lesson references")
        for lesson_id in unit["lesson_ids"]:
            if lesson_id not in lessons:
                raise ValueError(f"unit {unit['id']} references missing lesson {lesson_id}")
            lesson=lessons[lesson_id]
            if lesson["unit_id"]!=unit["id"] or lesson["tier"]!=unit["tier"]:
                raise ValueError(f"lesson {lesson_id} does not agree with unit {unit['id']}")
        for assessment_id in unit["assessment_ids"]:
            if assessment_id not in assessments:
                raise ValueError(f"unit {unit['id']} references missing assessment {assessment_id}")

    lesson_order:dict[str,tuple[int,int]]={}
    for lesson in lessons.values():
        unit=units.get(lesson["unit_id"])
        if unit is None:
            raise ValueError(f"lesson {lesson['id']} references missing unit {lesson['unit_id']}")
        if lesson["id"] not in unit["lesson_ids"]:
            raise ValueError(f"unit {unit['id']} does not reference lesson {lesson['id']}")
        if lesson["tier"]!=unit["tier"]:
            raise ValueError(f"lesson {lesson['id']} tier does not agree with its unit")
        order=(unit_order[unit["id"]],lesson["sequence"])
        if order in lesson_order.values():
            raise ValueError(f"duplicate lesson order: {order}")
        lesson_order[lesson["id"]]=order
        if len(lesson["prerequisite_lesson_ids"])!=len(set(lesson["prerequisite_lesson_ids"])):
            raise ValueError(f"lesson {lesson['id']} has duplicate prerequisites")
        for target in lesson["targets"]:
            node=population_nodes.get(target["node_id"])
            if node is None:
                raise ValueError(f"lesson {lesson['id']} references missing target {target['node_id']}")
            if node["tier"]!=lesson["tier"] or node["dimension"]!=target["dimension"]:
                raise ValueError(f"lesson {lesson['id']} target {target['node_id']} tier/dimension disagrees")
        for review_id in lesson["review_ids"]:
            if review_id not in reviews:
                raise ValueError(f"lesson {lesson['id']} references missing review {review_id}")
            if lesson["id"] not in reviews[review_id]["target_lesson_ids"]:
                raise ValueError(f"review {review_id} does not target lesson {lesson['id']}")
        for assessment_id in lesson["assessment_ids"]:
            if assessment_id not in assessments:
                raise ValueError(f"lesson {lesson['id']} references missing assessment {assessment_id}")
            if lesson["id"] not in assessments[assessment_id]["assessed_lesson_ids"]:
                raise ValueError(f"assessment {assessment_id} does not assess lesson {lesson['id']}")

    adjacency={lesson_id:set() for lesson_id in lessons}
    for lesson in lessons.values():
        for prerequisite_id in lesson["prerequisite_lesson_ids"]:
            if prerequisite_id not in lessons:
                raise ValueError(f"lesson {lesson['id']} references missing prerequisite {prerequisite_id}")
            if lesson_order[prerequisite_id]>=lesson_order[lesson["id"]]:
                raise ValueError(f"lesson {lesson['id']} has a forward prerequisite {prerequisite_id}")
            adjacency[prerequisite_id].add(lesson["id"])

    for review in reviews.values():
        placement=lessons.get(review["placement_after_lesson_id"])
        if placement is None:
            raise ValueError(f"review {review['id']} has missing placement lesson")
        if review["tier"]!=placement["tier"]:
            raise ValueError(f"review {review['id']} tier disagrees with placement lesson")
        for lesson_id in review["target_lesson_ids"]:
            lesson=lessons.get(lesson_id)
            if lesson is None:
                raise ValueError(f"review {review['id']} targets missing lesson {lesson_id}")
            if lesson["tier"]!=review["tier"] or lesson_order[lesson_id]>lesson_order[placement["id"]]:
                raise ValueError(f"review {review['id']} has an invalid target lesson {lesson_id}")
            if review["id"] not in lesson["review_ids"]:
                raise ValueError(f"lesson {lesson_id} does not reference review {review['id']}")

    for assessment in assessments.values():
        unit=units.get(assessment["placement_after_unit_id"])
        if unit is None:
            raise ValueError(f"assessment {assessment['id']} has missing placement unit")
        if assessment["tier"]!=unit["tier"]:
            raise ValueError(f"assessment {assessment['id']} tier disagrees with placement unit")
        for lesson_id in assessment["assessed_lesson_ids"]:
            lesson=lessons.get(lesson_id)
            if lesson is None:
                raise ValueError(f"assessment {assessment['id']} references missing lesson {lesson_id}")
            if lesson["tier"]!=assessment["tier"] or lesson_order[lesson_id][0]>unit_order[unit["id"]]:
                raise ValueError(f"assessment {assessment['id']} has an invalid lesson {lesson_id}")
        if assessment["kind"]=="unit_check":
            if assessment["id"] not in unit["assessment_ids"]:
                raise ValueError(f"unit {unit['id']} does not reference assessment {assessment['id']}")
            for lesson_id in assessment["assessed_lesson_ids"]:
                if assessment["id"] not in lessons[lesson_id]["assessment_ids"]:
                    raise ValueError(f"lesson {lesson_id} does not reference assessment {assessment['id']}")

    indegree={lesson_id:0 for lesson_id in lessons}
    for targets in adjacency.values():
        for target in targets: indegree[target]+=1
    ready=[lesson_id for lesson_id,degree in indegree.items() if degree==0]
    visited=0
    while ready:
        lesson_id=ready.pop(); visited+=1
        for target in adjacency[lesson_id]:
            indegree[target]-=1
            if indegree[target]==0: ready.append(target)
    if visited!=len(lessons): raise ValueError("lesson prerequisite graph contains a cycle")
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
