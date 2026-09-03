"""Fail-closed M7 preflight and type-specific semantic validation."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import SchemaValidationError, validate_instance

from .authority import VerifiedM6DevelopmentAuthority
from .builders import build_authorization, build_request
from .models import ExerciseIssue, JsonObject

M8_TERMS = ("ai tutor", "system prompt", "pronunciation evaluator", "spaced repetition", "placement test", "level test")


def _issue(code: str, path: str, message: str) -> ExerciseIssue:
    return ExerciseIssue(code, path, message)


def _schema(value: Any, name: str, code: str) -> list[ExerciseIssue]:
    try:
        validate_instance(dict(value) if isinstance(value, Mapping) else value, name)
    except (SchemaValidationError, TypeError, ValueError) as error:
        if isinstance(error, SchemaValidationError):
            return [_issue(code, item.instance_path, item.message) for item in error.issues]
        return [_issue(code, "$", str(error))]
    return []


def preflight_issues(request: Mapping[str, Any], authority: VerifiedM6DevelopmentAuthority) -> tuple[ExerciseIssue, ...]:
    issues = _schema(request, "exercise-generation-request", "REQUEST_SCHEMA")
    if issues:
        return tuple(sorted(set(issues)))
    binding = request["lesson_binding"]
    lesson_id = binding["lesson_id"]
    try:
        authorization = build_authorization(authority)
        config = request["generation_config"]
        constraints = request["constraints"]
        from .builders import ExerciseGenerationConfig
        rebuilt_config = ExerciseGenerationConfig(
            generator=config["generator"], generator_version=config["generator_version"],
            prompt_version=config["prompt_version"], curriculum_version=config["curriculum_version"],
            parameters=config["parameters"], seed=config["seed"], revision=config["revision"],
            permitted_types=tuple(constraints["permitted_types"]),
        )
        expected = build_request(authority, authorization, lesson_id, rebuilt_config).as_dict()
    except (ValueError, KeyError, TypeError) as error:
        return (_issue("M6_AUTHORITY_INVALID", "$", type(error).__name__),)
    if request["authorization_id"] != authorization["authorization_id"] or request["authorization_sha256"] != sha256_json(authorization):
        issues.append(_issue("AUTHORIZATION_BINDING_MISMATCH", "$.authorization_id", "request must bind the full independently derived authorization"))
    if request["m6_batch_id"] != authority.batch["batch_id"] or request["lesson_binding"] != expected["lesson_binding"]:
        issues.append(_issue("M6_BINDING_MISMATCH", "$.lesson_binding", "request lesson binding differs from verified M6 batch"))
    comparison = dict(request)
    comparison["request_id"] = expected["request_id"]
    if comparison != expected or request["request_id"] != identity("m7req", request, "request_id"):
        issues.append(_issue("REQUEST_DERIVATION_MISMATCH", "$", "request must exactly equal authority-derived content and canonical identity"))
    return tuple(sorted(set(issues)))


def backend_candidate_issues(candidate: Mapping[str, Any]) -> tuple[ExerciseIssue, ...]:
    return tuple(sorted(set(_schema(candidate, "exercise-backend-candidate", "BACKEND_RESPONSE_INVALID"))))


def _payload_issue(item: Mapping[str, Any], index: int) -> list[ExerciseIssue]:
    payload, kind = item.get("payload"), item.get("exercise_type")
    path = f"$.items[{index}].payload"
    if not isinstance(payload, Mapping):
        return [_issue("TYPE_CONTRACT", path, "payload must be an object")]
    issues: list[ExerciseIssue] = []
    def required(*names: str) -> None:
        for name in names:
            if name not in payload or payload[name] in (None, "", [], {}):
                issues.append(_issue("TYPE_CONTRACT", f"{path}.{name}", f"{kind} requires {name}"))
    if kind == "multiple_choice":
        required("options", "primary_option_id", "explanation")
        options = payload.get("options")
        if isinstance(options, list):
            ids = [option.get("id") for option in options if isinstance(option, Mapping)]
            texts = [str(option.get("text", "")).casefold().strip() for option in options if isinstance(option, Mapping)]
            if len(options) < 3 or len(ids) != len(options) or len(set(ids)) != len(ids) or payload.get("primary_option_id") not in ids:
                issues.append(_issue("MCQ_ANSWER_INVALID", path, "options must be distinct, sufficient, and contain one primary option"))
            if len(texts) != len(set(texts)) or any(not text for text in texts):
                issues.append(_issue("MCQ_DISTRACTOR_INVALID", path, "option text must be nonempty and nonduplicate"))
        else: issues.append(_issue("MCQ_ANSWER_INVALID", f"{path}.options", "options must be a list"))
    elif kind == "fill_blank":
        required("stimulus", "blank_marker", "primary_answer", "acceptable_variants", "explanation", "spelling_policy")
        marker = payload.get("blank_marker")
        if not isinstance(marker, str) or marker not in str(payload.get("stimulus", "")):
            issues.append(_issue("FILL_BLANK_AMBIGUITY", path, "stimulus must contain its declared blank marker"))
    elif kind == "matching":
        required("left", "right", "mapping", "explanation")
        left, right, mapping = payload.get("left"), payload.get("right"), payload.get("mapping")
        if isinstance(left,list) and isinstance(right,list) and isinstance(mapping,list):
            left_ids = [x.get("id") for x in left if isinstance(x, Mapping)]
            right_ids = [x.get("id") for x in right if isinstance(x, Mapping)]
            left_texts = [str(x.get("text", "")).casefold().strip() for x in left if isinstance(x, Mapping)]
            right_texts = [str(x.get("text", "")).casefold().strip() for x in right if isinstance(x, Mapping)]
            pairs = [(x.get("left_id"), x.get("right_id")) for x in mapping if isinstance(x, Mapping)]
            if (
                len(left_ids) < 2
                or len(left_ids) != len(left)
                or len(right_ids) != len(right)
                or len(left_ids) != len(right_ids)
                or len(left_ids) != len(set(left_ids))
                or len(right_ids) != len(set(right_ids))
                or not all(left_texts)
                or not all(right_texts)
                or len(left_texts) != len(set(left_texts))
                or len(right_texts) != len(set(right_texts))
                or set(left_ids) != {a for a, _ in pairs}
                or set(right_ids) != {b for _, b in pairs}
                or len(pairs) != len(set(pairs))
                or len(pairs) != len(left_ids)
            ):
                issues.append(_issue("MATCHING_MAPPING_INVALID",path,"mapping must be a complete one-to-one relation"))
        else: issues.append(_issue("MATCHING_MAPPING_INVALID",path,"left, right, and mapping must be lists"))
    elif kind == "ordering":
        required("segments", "valid_order", "ordering_principle", "explanation")
        segments, order=payload.get("segments"),payload.get("valid_order")
        segment_ids = [x.get("id") for x in segments if isinstance(x, Mapping)] if isinstance(segments, list) else []
        segment_texts = [str(x.get("text", "")).casefold().strip() for x in segments if isinstance(x, Mapping)] if isinstance(segments, list) else []
        if (
            not isinstance(segments, list)
            or not isinstance(order, list)
            or len(segment_ids) != len(segments)
            or len(segment_ids) != len(set(segment_ids))
            or not all(segment_texts)
            or len(segment_texts) != len(set(segment_texts))
            or set(segment_ids) != set(order)
            or len(order) != len(set(order))
        ):
            issues.append(_issue("ORDERING_INVALID",path,"valid order must contain every unique segment exactly once"))
    elif kind == "error_correction":
        required("erroneous_sentence", "error_span", "correction", "corrected_sentence", "explanation")
        if str(payload.get("error_span","")) not in str(payload.get("erroneous_sentence","")) or payload.get("erroneous_sentence")==payload.get("corrected_sentence"):
            issues.append(_issue("ERROR_CORRECTION_INVALID",path,"deliberate error span and changed corrected sentence are required"))
    elif kind == "sentence_construction":
        required("required_words", "target_structure", "primary_answer", "acceptable_variants", "scoring_guidance")
    elif kind == "translation":
        required("direction", "register", "source_text", "intended_meaning", "primary_answer", "acceptable_variants", "scoring_guidance")
        if payload.get("direction") not in {"vi_to_en","en_to_vi"}: issues.append(_issue("TRANSLATION_DIRECTION_INVALID",path,"direction must be vi_to_en or en_to_vi"))
    elif kind in {"reading","listening"}:
        required("stimulus" if kind=="reading" else "transcript", "questions", "answers", "origin")
        if kind=="listening" and payload.get("media_required") is not False: issues.append(_issue("UNSUPPORTED_MEDIA",path,"listening must be transcript-only with media_required false"))
        if payload.get("origin")!="PROJECT_AUTHORED": issues.append(_issue("EXTERNAL_STIMULUS_FORBIDDEN",path,"only project-authored inline stimuli are allowed"))
    elif kind in {"speaking","writing"}:
        required("communicative_goal", "constraints", "expected_output", "rubric")
        if item.get("scoring_mode")!="RUBRIC": issues.append(_issue("SUBJECTIVE_RUBRIC_REQUIRED",path,"speaking/writing must use RUBRIC scoring"))
        rubric=payload.get("rubric")
        if not isinstance(rubric,list) or len(rubric)<2:
            issues.append(_issue("SUBJECTIVE_RUBRIC_REQUIRED",f"{path}.rubric","analytic rubric must contain at least two dimensions"))
        else:
            dimensions = [row.get("dimension") for row in rubric if isinstance(row, Mapping)]
            criteria = [row.get("criterion") for row in rubric if isinstance(row, Mapping)]
            if (len(dimensions) != len(rubric) or any(not isinstance(value, str) or not value.strip() for value in dimensions)
                    or len(set(dimensions)) != len(dimensions)
                    or any(not isinstance(value, str) or not value.strip() for value in criteria)):
                issues.append(_issue("SUBJECTIVE_RUBRIC_REQUIRED", f"{path}.rubric", "each analytic dimension must be unique and have a usable criterion"))
    return issues


def candidate_semantic_issues(request: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[ExerciseIssue, ...]:
    issues = list(backend_candidate_issues(candidate))
    if issues: return tuple(sorted(set(issues)))
    spec, constraints = request["lesson_spec"], request["constraints"]
    allowed, targets, reviews = set(spec["allowed_references"]), set(spec["targets"]), set(spec["review_references"])
    counts: Counter[str] = Counter(); normalized: list[str] = []
    for index, item in enumerate(candidate["items"]):
        kind = item["exercise_type"]; counts[kind] += 1
        path=f"$.items[{index}]"
        if kind not in constraints["permitted_types"] or counts[kind] > constraints["maximum_counts"].get(kind, 0): issues.append(_issue("TYPE_LIMIT",f"{path}.exercise_type","exercise type is not permitted or exceeds its maximum"))
        if len(item["instructions"])>constraints["max_prompt_chars"]: issues.append(_issue("SIZE_LIMIT",f"{path}.instructions","instructions exceed trusted maximum"))
        refs=set(item["target_references"]+item["review_references"])
        if not refs or not refs <= allowed: issues.append(_issue("REFERENCE_SCOPE_MISMATCH",path,"references must be nonempty and within lesson scope"))
        if not set(item["target_references"]) <= targets or not set(item["review_references"]) <= reviews: issues.append(_issue("TARGET_REVIEW_MISMATCH",path,"target/review categories must match derived lesson scope"))
        if any(i < 0 or i >= len(spec["objectives"]) for i in item["objective_indices"]):
            issues.append(_issue("OBJECTIVE_ALIGNMENT",f"{path}.objective_indices","objective index is outside lesson objectives"))
        words=(item["title"]+" "+item["instructions"]+" "+str(item["payload"])).casefold()
        if any(term.casefold() in words for term in M8_TERMS): issues.append(_issue("M8_LEAKAGE",path,"M8 or later-milestone behavior is forbidden"))
        if any(term.casefold() in words for term in constraints["forbidden_terms"]): issues.append(_issue("FORBIDDEN_TERM",path,"contains a request-forbidden term"))
        normalized.append(re.sub(r"\W+"," ",words).strip())
        issues.extend(_payload_issue(item,index))
    for i, left in enumerate(normalized):
        for j, right in enumerate(normalized[:i]):
            a,b=set(left.split()),set(right.split()); similarity=len(a&b)/max(1,len(a|b))
            if left==right or similarity>=0.9: issues.append(_issue("DUPLICATE_EXERCISE",f"$.items[{i}]","exact or near-duplicate exercise padding is forbidden"))
    return tuple(sorted(set(issues)))


def assembled_issues(request: Mapping[str, Any], value: Mapping[str, Any]) -> tuple[ExerciseIssue, ...]:
    issues=_schema(value,"exercise-set","EXERCISE_SET_SCHEMA")
    if issues: return tuple(sorted(set(issues)))
    base = dict(value)
    base.pop("output_sha256", None)
    base.pop("exercise_set_id", None)
    expected_hash = sha256_json(base)
    if value["output_sha256"] != expected_hash:
        issues.append(_issue("OUTPUT_HASH_MISMATCH","$.output_sha256","output hash must bind the complete set excluding its hash and identity fields"))
    if value["exercise_set_id"] != f"m7set_{expected_hash}":
        issues.append(_issue("EXERCISE_SET_ID_MISMATCH","$.exercise_set_id","set ID must be canonical"))
    ids=[item["id"] for item in value["exercises"]]
    if len(ids)!=len(set(ids)) or [item["sequence"] for item in value["exercises"]] != list(range(1,len(ids)+1)):
        issues.append(_issue("NONCANONICAL_ORDER","$.exercises","exercise IDs and sequence must be deterministic"))
    return tuple(sorted(set(issues)))
