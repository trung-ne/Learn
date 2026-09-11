import json
import pytest
from english_master.curriculum_blueprint import build, validate
from english_master.knowledge_graph.service import build_population


def test_a1_shape_resolution_and_noncanonical_text():
    population=build_population(); blueprint=build(population)
    assert len(blueprint["units"])==10 and len(blueprint["lessons"])==50
    blueprint["lessons"][0]["title"]="Alternative outline title"
    assert validate(blueprint,population) is blueprint


def test_population_hash_and_id_drift_rejected():
    population=build_population(); blueprint=build(population)
    drifted=json.loads(json.dumps(population)); drifted["nodes"][0]["name"]="drifted"
    with pytest.raises(ValueError,match="hash"):
        validate(blueprint,drifted)

    wrong_id=json.loads(json.dumps(blueprint)); wrong_id["source_population_id"]="kgpop_"+"0"*64
    with pytest.raises(ValueError,match="population ID"):
        validate(wrong_id,population)


def test_unit_lesson_review_and_assessment_refs_are_checked():
    population=build_population(); blueprint=build(population)

    broken_unit=json.loads(json.dumps(blueprint))
    broken_unit["units"][0]["lesson_ids"][0]="missing-lesson"
    with pytest.raises(ValueError,match="missing lesson"):
        validate(broken_unit,population)

    broken_review=json.loads(json.dumps(blueprint))
    broken_review["lessons"][0]["review_ids"][0]="missing-review"
    with pytest.raises(ValueError,match="missing review"):
        validate(broken_review,population)

    broken_assessment=json.loads(json.dumps(blueprint))
    broken_assessment["lessons"][0]["assessment_ids"][0]="missing-assessment"
    with pytest.raises(ValueError,match="missing assessment"):
        validate(broken_assessment,population)


def test_target_resolution_tier_and_dimension_agreement():
    population=build_population(); blueprint=build(population)

    missing=json.loads(json.dumps(blueprint))
    missing["lessons"][0]["targets"][0]["node_id"]="kg_missing"
    with pytest.raises(ValueError,match="missing target"):
        validate(missing,population)

    mismatched=json.loads(json.dumps(blueprint))
    mismatched["lessons"][0]["targets"][0]["dimension"]="skills"
    with pytest.raises(ValueError,match="tier/dimension disagrees"):
        validate(mismatched,population)


def test_forward_and_cyclic_lesson_prerequisites_are_rejected():
    population=build_population(); blueprint=build(population)
    altered=json.loads(json.dumps(blueprint))
    first=altered["lessons"][0]; second=altered["lessons"][1]
    first["prerequisite_lesson_ids"]=[second["id"]]
    second["prerequisite_lesson_ids"]=[first["id"]]
    with pytest.raises(ValueError,match="forward prerequisite|cycle"):
        validate(altered,population)


def test_blueprint_schema_tamper_rejected():
    population=build_population(); blueprint=build(population); blueprint["status"]="APPROVED"
    with pytest.raises(Exception):
        validate(blueprint,population)
