"""Snapshot-bound M7 exercise generation orchestration."""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from english_master.lesson_generation.canonical import canonical_json, sha256_json, sha256_text
from english_master.schema_validation import validate_instance

from .authority import VerifiedM6DevelopmentAuthority
from .models import CapturedExerciseResponse, ExerciseBackend, ExerciseGenerationRequest, ExerciseGenerationResult, ExerciseIssue, JsonObject
from .storage import publish, publish_rejection
from .validator import assembled_issues, backend_candidate_issues, candidate_semantic_issues, preflight_issues

CHECKS=("request_schema","m6_authority","authorization","identity","constraints","backend_contract","candidate_schema","reference_scope","cefr_prerequisite","answer_ambiguity","duplicate","provenance_copyright","m8_exclusion","exercise_set_schema","publication")

class ExerciseGenerator:
    def __init__(self, backend: ExerciseBackend, authority: VerifiedM6DevelopmentAuthority, *, clock: Callable[[],datetime]|None=None)->None:
        self.backend=backend; self.authority=authority; self._clock=clock or (lambda: datetime.now(timezone.utc))

    def _timestamp(self)->str:
        now=self._clock()
        if now.tzinfo is None or now.utcoffset() is None: raise ValueError("clock must be timezone-aware")
        return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

    @staticmethod
    def _safe_hash(value: Any)->str|None:
        try:return sha256_json(value)
        except (TypeError,ValueError,OverflowError):return None

    @staticmethod
    def build_prompt(request: Mapping[str,Any])->str:
        return "Return exactly one JSON object with only items. The host assigns IDs, authority bindings, hashes, statuses, timestamps, provenance, and QA. Do not create AI tutors, evaluators, media, approvals, or M8 behavior. REQUEST="+canonical_json(request)

    @staticmethod
    def _capture_issues(capture: Any,prompt:str,parameters:Mapping[str,Any],seed:int|None)->tuple[ExerciseIssue,...]:
        if not isinstance(capture,CapturedExerciseResponse):return (ExerciseIssue("CAPTURE_MISMATCH","$","backend must return CapturedExerciseResponse"),)
        if capture.prompt_sha256!=sha256_text(prompt) or capture.response_sha256!=sha256_json(capture.content):return (ExerciseIssue("CAPTURE_MISMATCH","$","capture hashes must bind exact prompt and response"),)
        if dict(capture.parameters)!=dict(parameters) or capture.seed!=seed:return (ExerciseIssue("CAPTURE_MISMATCH","$","capture parameters/seed differ from trusted request"),)
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T.*(?:Z|[+-][0-9]{2}:[0-9]{2})",capture.observed_at):return (ExerciseIssue("CAPTURE_MISMATCH","$.observed_at","capture timestamp must be ISO 8601"),)
        return ()

    def _audit(self,request:Mapping[str,Any],*,accepted:bool,stage:str,issues:tuple[ExerciseIssue,...],output_hash:str|None,capture:CapturedExerciseResponse|None=None)->JsonObject:
        failed={issue.code for issue in issues}
        def result(name:str)->str:
            if not accepted and stage=="PREFLIGHT" and name not in {"request_schema","m6_authority","authorization","identity","constraints"}: return "NOT_RUN"
            if not accepted and stage=="PROVIDER" and name not in CHECKS[:6]: return "NOT_RUN"
            if name=="publication" and stage!="PUBLICATION" and not accepted:return "NOT_RUN"
            return "FAIL" if failed else "PASS"
        request_id=request.get("request_id") if isinstance(request.get("request_id"),str) else "m7req_"+"0"*64
        lesson=request.get("lesson_binding",{}).get("lesson_id") if isinstance(request.get("lesson_binding"),Mapping) else "A1-U01-L01"
        value:JsonObject={"schema_version":"1.0","record_type":"exercise_generation_audit","request_id":request_id,"lesson_id":lesson,"status":"ACCEPTED" if accepted else "REJECTED","validation_stage":"COMPLETE" if accepted else stage,"input_hashes":{"request":self._safe_hash(request),"m6_batch":self._safe_hash(self.authority.batch),"snapshot":self._safe_hash(self.authority.m5.snapshot)},"checks":{name:result(name) for name in CHECKS},"output_hash":output_hash,"qa_status":"UNREVIEWED" if accepted else "REJECTED","qa_reviewer":"english_master.m7_automated_validator","qa_timestamp":self._timestamp(),"qa_outcome":"AUTOMATED_CHECKS_PASSED_PENDING_INDEPENDENT_REVIEW" if accepted else "AUTOMATED_CHECKS_FAILED","qa_checks_performed":[name for name in CHECKS if result(name)!="NOT_RUN"],"qa_issues_found":[issue.as_dict() for issue in issues],"outstanding_independent_reviews":["CEFR","GRAMMAR_LEXICAL","LANGUAGE_QUALITY","PEDAGOGICAL"],"provenance_copyright":{"external_payload_used":False,"external_media_used":False,"decision":"PROJECT_AUTHORED_NO_EXTERNAL_RIGHTS_EXERCISED","limitations":["No external text, audio, video, transcript, clip, transformation, extraction, or redistribution right was exercised.","No Internet-wide copyright or plagiarism search was performed."]},"response_provenance":capture.provenance() if capture else None,"unresolved_issues":[issue.as_dict() for issue in issues]}
        validate_instance(value,"exercise-generation-audit"); return value

    def _rejection(self,request:Mapping[str,Any],stage:str,issues:tuple[ExerciseIssue,...],candidate:JsonObject|None,capture:CapturedExerciseResponse|None)->JsonObject:
        lesson=request.get("lesson_binding",{}).get("lesson_id") if isinstance(request.get("lesson_binding"),Mapping) else "A1-U01-L01"
        value:JsonObject={"schema_version":"1.0","record_type":"exercise_generation_rejection","request_id":request.get("request_id","m7req_"+"0"*64),"lesson_id":lesson,"stage":stage,"rejected_at":self._timestamp(),"reasons":[issue.as_dict() for issue in issues],"request_hash":self._safe_hash(request),"candidate_output_hash":self._safe_hash(candidate) if candidate else None,"candidate_output":copy.deepcopy(candidate),"published":False,"response_provenance":capture.provenance() if capture else None}
        validate_instance(value,"exercise-generation-rejection"); return value

    @staticmethod
    def _metadata(request:Mapping[str,Any],capture:CapturedExerciseResponse)->JsonObject:
        config=request["generation_config"]
        value:JsonObject={"generator":config["generator"],"generator_version":config["generator_version"],"prompt_version":config["prompt_version"],"generated_at":capture.observed_at,"curriculum_version":config["curriculum_version"],"qa_status":"UNREVIEWED","qa_notes":"Automated M7 checks passed; independent review remains required."}
        if capture.model:value["model"]=capture.model
        return value

    def _assemble(self,request:Mapping[str,Any],candidate:Mapping[str,Any],capture:CapturedExerciseResponse)->JsonObject:
        binding,spec=request["lesson_binding"],request["lesson_spec"]
        exercises=[]
        for sequence,item in enumerate(candidate["items"],1):
            exercises.append({"id":f"ex_{binding['lesson_id']}_{sequence:03d}","sequence":sequence,"title":item["title"],"exercise_type":item["exercise_type"],"cefr_level":spec["cefr_level"],"difficulty":item["difficulty"],"instructions":item["instructions"],"objective_indices":copy.deepcopy(item["objective_indices"]),"target_references":sorted(item["target_references"]),"review_references":sorted(item["review_references"]),"scoring_mode":item["scoring_mode"],"payload":copy.deepcopy(item["payload"]),"generation_metadata":self._metadata(request,capture)})
        base:JsonObject={"schema_version":"1.0","record_type":"exercise_set","exercise_set_id":"PENDING","request_id":request["request_id"],"lesson_id":binding["lesson_id"],"lesson_sha256":binding["lesson_sha256"],"m6_batch_id":request["m6_batch_id"],"status":"UNREVIEWED","exercises":exercises,"output_sha256":"PENDING","provenance":{"origin":"PROJECT_AUTHORED","external_payload_used":False,"media_used":False,"notes":"All stimuli and response options are original project-authored text."},"generation_metadata":self._metadata(request,capture)}
        identity_base=copy.deepcopy(base); identity_base.pop("exercise_set_id"); identity_base.pop("output_sha256")
        digest=sha256_json(identity_base); base["output_sha256"]=digest; base["exercise_set_id"]=f"m7set_{digest}"
        return base

    def _reject(self,request:JsonObject,stage:str,issues:tuple[ExerciseIssue,...],candidate:JsonObject|None,rejection_directory:Path|None,capture:CapturedExerciseResponse|None=None)->ExerciseGenerationResult:
        audit=self._audit(request,accepted=False,stage=stage,issues=issues,output_hash=self._safe_hash(candidate) if candidate else None,capture=capture); rejection=self._rejection(request,stage,issues,candidate,capture); paths=()
        if rejection_directory is not None:
            try: paths=publish_rejection(rejection_directory,rejection,audit)
            except (OSError,ValueError,TypeError): pass
        return ExerciseGenerationResult(False,None,audit,rejection,paths)

    def generate(self,request:ExerciseGenerationRequest,*,output_directory:Path|None=None,rejection_directory:Path|None=None)->ExerciseGenerationResult:
        payload=request.as_dict(); issues=preflight_issues(payload,self.authority)
        if issues:return self._reject(payload,"PREFLIGHT",issues,None,rejection_directory)
        config=payload["generation_config"]; prompt=self.build_prompt(payload)
        try:capture=self.backend.generate(prompt,parameters=config["parameters"],seed=config["seed"])
        except Exception as error:return self._reject(payload,"PROVIDER",(ExerciseIssue("PROVIDER_FAILURE","$",type(error).__name__),),None,rejection_directory)
        issues=self._capture_issues(capture,prompt,config["parameters"],config["seed"])
        if issues:return self._reject(payload,"PROVIDER",issues,None,rejection_directory)
        issues=backend_candidate_issues(capture.content)
        if issues:return self._reject(payload,"PROVIDER",issues,capture.content,rejection_directory,capture)
        issues=candidate_semantic_issues(payload,capture.content)
        if issues:return self._reject(payload,"POSTVALIDATION",issues,capture.content,rejection_directory,capture)
        value=self._assemble(payload,capture.content,capture); issues=assembled_issues(payload,value)
        if issues:return self._reject(payload,"POSTVALIDATION",issues,value,rejection_directory,capture)
        audit=self._audit(payload,accepted=True,stage="COMPLETE",issues=(),output_hash=value["output_sha256"],capture=capture)
        if output_directory is None:return ExerciseGenerationResult(True,value,audit,None,())
        try:paths=publish(output_directory,value,audit)
        except (OSError,ValueError,TypeError):return self._reject(payload,"PUBLICATION",(ExerciseIssue("PUBLICATION_FAILURE","$","accepted exercise bundle could not be published atomically"),),value,rejection_directory,capture)
        return ExerciseGenerationResult(True,value,audit,None,paths)
