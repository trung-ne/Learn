import pytest
from english_master.curriculum_blueprint import build, validate
from english_master.knowledge_graph.service import build_population

def test_a1_shape_and_resolution():
    p=build_population(); b=build(p)
    assert len(b['units'])==10 and len(b['lessons'])==50
    validate(b,p)

def test_population_drift_rejected():
    p=build_population(); b=build(p); p['nodes'][0]['name']='drifted'
    with pytest.raises(ValueError): validate(b,p)

def test_blueprint_tamper_rejected():
    p=build_population(); b=build(p); b['status']='APPROVED'
    with pytest.raises(Exception): validate(b,p)
