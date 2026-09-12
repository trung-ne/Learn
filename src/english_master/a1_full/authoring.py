"""Retained-source compiler for the repaired Full A1 content revision."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

from .service import _canonical_bytes, _sha256_file

_LEGACY_PHRASES = (
    "no detail is provided",
    "a different routine appears",
    "target phrase in",
    "communication goal in",
    "put the three learning steps",
    "take the learner role",
    "clear final sounds and stress",
)

# Each card supplies deliberately authored, target-specific listening content and
# pronunciation focus. The compiler only validates, groups, and hashes cards; it
# does not invent learner-facing prose from lesson titles or target identifiers.
_DETAILS: tuple[tuple[str, str, str, str, str], ...] = (
    ("m16a1-v1-a1-u01-l01", "Hi, I'm Lan. Nice to meet you.", "What is the speaker's name?", "Lan", "Word stress: HEL-lo. Clap once on HEL, then say hello smoothly."),
    ("m16a1-v1-a1-u01-l02", "Hello. My name is Minh, and I am in class 6A.", "What is Minh's class?", "6A", "Link My name is; do not pause between name and is."),
    ("m16a1-v1-a1-u01-l03", "A: Where are you from? B: I'm from Da Nang.", "Where is B from?", "Da Nang", "Make from short and clear; stress the place name: Da NANG."),
    ("m16a1-v1-a1-u01-l04", "A: Is your name Mai? B: Yes. M-A-I.", "How does B spell the name?", "M-A-I", "Say letter names separately: /em/ - /eɪ/ - /aɪ/."),
    ("m16a1-v1-a1-u01-l05", "My practice number is zero, eight, one, four. It is not a real number.", "What is the second digit?", "eight", "Keep one beat for each digit: ZERO | EIGHT | ONE | FOUR."),
    ("m16a1-v1-a1-u02-l01", "Please put an eraser and a pen on the desk.", "Which item uses an?", "an eraser", "Link an eraser and keep the /n/ sound at the start of an."),
    ("m16a1-v1-a1-u02-l02", "Open your notebook, listen, and write one word.", "What should the learner do after listening?", "write one word", "Stress the action words: OPEN, LIS-ten, WRITE."),
    ("m16a1-v1-a1-u02-l03", "This is my sister. Her name is Hoa, and she is ten.", "What is the sister's name?", "Hoa", "Say my and her clearly; do not add a vowel before the /h/ in her."),
    ("m16a1-v1-a1-u02-l04", "I get up at six. I have breakfast, then I walk to school.", "What does the speaker do after breakfast?", "walk to school", "Join get up as two short beats; stress BREAKfast."),
    ("m16a1-v1-a1-u02-l05", "I always do my homework after dinner, but I sometimes watch TV first.", "What does the speaker sometimes do first?", "watch TV", "Stress the first syllable: AL-ways, SOME-times."),
    ("m16a1-v1-a1-u03-l01", "This is my uncle. His daughter is my cousin, Mai.", "Who is Mai?", "the speaker's cousin", "Keep his and her short; stress COU-sin."),
    ("m16a1-v1-a1-u03-l02", "My family has a small dog. I have a cat.", "What animal does the speaker have?", "a cat", "Pronounce has with /z/ and have with /v/."),
    ("m16a1-v1-a1-u03-l03", "The sofa is in the living room. The kitchen has a small table.", "Where is the sofa?", "in the living room", "Stress the first syllable: LIV-ing, KITCH-en."),
    ("m16a1-v1-a1-u03-l04", "There are two chairs by the window, but there is one lamp.", "How many lamps are there?", "one", "Contrast there IS and there ARE; make the final /z/ in is audible."),
    ("m16a1-v1-a1-u03-l05", "Welcome to our home. My mother has tea in the kitchen.", "Where does the mother have tea?", "in the kitchen", "Use a friendly falling tone in Welcome, then stress HOME."),
    ("m16a1-v1-a1-u04-l01", "I love noodles, but I do not like coffee.", "What does the speaker not like?", "coffee", "Link do not; stress LIKE and COF-fee."),
    ("m16a1-v1-a1-u04-l02", "For breakfast, I have bread and milk. At lunch, I have rice.", "What does the speaker have for lunch?", "rice", "Stress BREAKfast and LUNCH; keep have short."),
    ("m16a1-v1-a1-u04-l03", "We have some fruit. Do we have any juice?", "What do they ask about?", "juice", "Contrast some /sʌm/ and any /ˈeni/."),
    ("m16a1-v1-a1-u04-l04", "How much water do we need? We need two bottles.", "How many bottles do they need?", "two", "Say how MUCH and how MAN-y with stress on the last word."),
    ("m16a1-v1-a1-u04-l05", "A: What would you like? B: I'd like tea, please.", "What would B like?", "tea", "Link I'd like; use a polite falling tone on please."),
    ("m16a1-v1-a1-u05-l01", "I go to the market on Saturday. The post office is near it.", "Where does the speaker go on Saturday?", "the market", "Stress MAR-ket and POST office."),
    ("m16a1-v1-a1-u05-l02", "The bank is opposite the park. The cafe is next to the bank.", "What is next to the bank?", "the cafe", "Stress the middle syllable in op-PO-site."),
    ("m16a1-v1-a1-u05-l03", "The museum opens at ten and closes at four on Sunday.", "What time does the museum open?", "ten", "Make the final /z/ in opens and closes clear."),
    ("m16a1-v1-a1-u05-l04", "You can go straight to the park. You cannot park here.", "What can the listener do?", "go straight to the park", "Use weak can /kən/ in a statement; say cannot clearly in the negative."),
    ("m16a1-v1-a1-u05-l05", "A: Excuse me, where is the bus stop? B: Go past the bank. It is next to the park.", "What should A go past?", "the bank", "Use rising polite tone in Excuse me; stress PAST and PARK."),
    ("m16a1-v1-a1-u06-l01", "My brother works in a cafe, and I study English every evening.", "What does the speaker study?", "English", "Make the third-person ending in works /s/ clear."),
    ("m16a1-v1-a1-u06-l02", "Do you work on Saturday? No, I don't. I study at home.", "Does the speaker work on Saturday?", "No", "Link do you; make does sound /dʌz/ in does questions."),
    ("m16a1-v1-a1-u06-l03", "Mai does not drink tea in the morning. She drinks water.", "What does Mai drink?", "water", "Link does not; do not say the final -s on drink after does not."),
    ("m16a1-v1-a1-u06-l04", "I usually visit my aunt on Sunday afternoon.", "When does the speaker visit the aunt?", "on Sunday afternoon", "Stress US-u-al-ly and SUN-day."),
    ("m16a1-v1-a1-u06-l05", "I usually cook on Monday, but I eat out on Friday because I meet friends.", "Why does the speaker eat out on Friday?", "because the speaker meets friends", "Pause lightly before but and because; stress FRIENDS."),
    ("m16a1-v1-a1-u07-l01", "I need a blue T-shirt and black shoes for school.", "What colour are the shoes?", "black", "Stress the colour before the noun: BLUE T-shirt, BLACK shoes."),
    ("m16a1-v1-a1-u07-l02", "These jeans are too long. That skirt is small, but this one is right.", "Which item is right?", "this one", "Contrast this /ðɪs/ and these /ðiːz/."),
    ("m16a1-v1-a1-u07-l03", "How much is this hat? It is five pounds. How much are these socks? They are three pounds.", "How much are the socks?", "three pounds", "Use is for one item and are for more than one item."),
    ("m16a1-v1-a1-u07-l04", "Could I try on this green jacket, please? Yes, the fitting room is there.", "What does the speaker want to try on?", "this green jacket", "Link could I; use a polite rising tone on please."),
    ("m16a1-v1-a1-u07-l05", "A: Can I have the red shirt in medium? B: Yes. It is twelve pounds. A: Thank you.", "What size does A want?", "medium", "Stress the useful chunks: CAN I HAVE, RED SHIRT, THANK YOU."),
    ("m16a1-v1-a1-u08-l01", "It is rainy and cold today, so I have my umbrella.", "What does the speaker have?", "an umbrella", "Link it is; stress RAIN-y and COLD."),
    ("m16a1-v1-a1-u08-l02", "It is windy, so I wear a warm coat.", "Why does the speaker wear a coat?", "because it is windy", "Stress WIND-y and WARM; connect so I."),
    ("m16a1-v1-a1-u08-l03", "I have a headache, so I feel tired today.", "How does the speaker feel?", "tired", "Stress HEAD-ache and TIRED; keep have a linked."),
    ("m16a1-v1-a1-u08-l04", "Would you like to watch a film tonight? Sorry, I can't. I feel ill.", "Why can the person not come?", "because the person feels ill", "Link would you; use a friendly rise in the invitation."),
    ("m16a1-v1-a1-u08-l05", "It is raining, so we are staying inside because Nam has a cold.", "Why are they staying inside?", "because it is raining", "Stress RAIN-ing and IN-side; pause before because."),
    ("m16a1-v1-a1-u09-l01", "Take the number 6 bus to the station. Get off at River Road.", "Which bus should the listener take?", "the number 6 bus", "Link number six; stress BUS and STA-tion."),
    ("m16a1-v1-a1-u09-l02", "Take the number 6 bus, get off at King Street, then walk past the post office.", "Where should the listener get off?", "King Street", "Use clear sequence stress: TAKE, GET OFF, WALK PAST."),
    ("m16a1-v1-a1-u09-l03", "The bus leaves at eight forty and arrives at nine ten.", "When does the bus arrive?", "at nine ten", "Make leaves /liːvz/ and arrives /əˈraɪvz/ clear."),
    ("m16a1-v1-a1-u09-l04", "Tomorrow, I am going to take the train to visit my grandmother.", "What is the speaker going to do tomorrow?", "take the train to visit the grandmother", "Link going to in normal speech; stress TOMORROW and TRAIN."),
    ("m16a1-v1-a1-u09-l05", "A: Excuse me, when does the number 12 bus leave? B: It leaves at one thirty from the station.", "When does the bus leave?", "at one thirty", "Use a polite rise in the question; stress ONE THIR-ty."),
    ("m16a1-v1-a1-u10-l01", "I feel sick. Could you help me call the clinic, please?", "What does the speaker ask for?", "help to call the clinic", "Link could you; stress HELP and CLINIC."),
    ("m16a1-v1-a1-u10-l02", "Could I make an appointment for Tuesday at ten, please?", "What day does the speaker request?", "Tuesday", "Stress ap-POINT-ment and TUES-day."),
    ("m16a1-v1-a1-u10-l03", "Would you like to have lunch on Saturday? Yes, I'd love to.", "Does the person accept?", "Yes", "Link would you and I'd love; use a warm rising invitation tone."),
    ("m16a1-v1-a1-u10-l04", "Hi Mai, I am late because the bus is slow. Please start without me. Minh", "Why is Minh late?", "because the bus is slow", "Read the message in groups: HI MAI | I AM LATE | SEE YOU."),
    ("m16a1-v1-a1-u10-l05", "I usually study on Friday. Yesterday I studied at home, and tomorrow I am going to visit my friend.", "What is the speaker going to do tomorrow?", "visit a friend", "Contrast YESTERday and toMORrow; stress the time words."),
)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _model_from_legacy(lesson: Mapping[str, Any]) -> str:
    body = lesson["content_sections"][0]["body"]
    marker = "notice this model: "
    if marker not in body:
        raise ValueError(f"legacy lesson has no model sentence: {lesson['lesson_id']}")
    return body.split(marker, 1)[1].split(" Keep the word order", 1)[0].strip()


def _detail_by_lesson() -> dict[str, tuple[str, str, str, str]]:
    return {lesson_id: (transcript, question, answer, pronunciation) for lesson_id, transcript, question, answer, pronunciation in _DETAILS}


def _target_ids(lesson: Mapping[str, Any]) -> list[str]:
    return list(lesson["objective_target_ids"])


def _roleplay(topic: str, model: str) -> dict[str, str | list[str]]:
    return {
        "instruction": (
            f"Roleplay: you are a learner using {topic}; the tutor is a helpful conversation partner. "
            f"Scenario: you need to use this language in a short everyday interaction. Tutor opening: “Hello. Can we practise {topic}?” "
            f"Reply naturally, ask or answer one follow-up question, and finish the exchange politely. Useful model: {model}"
        ),
        "goal": f"Complete a short, understandable exchange about {topic}.",
        "constraints": [
            "Give the tutor one role and the learner one role before the first turn.",
            "Create an information gap: the tutor asks for one missing personal or practical detail.",
            "Use no more than three tutor turns and give one correction only if it blocks meaning.",
            "Finish after the learner has used the target and responded to one follow-up.",
        ],
    }


def _writing(topic: str, model: str) -> dict[str, str | list[str]]:
    return {
        "instruction": (
            f"Write 2–3 short sentences for a real-life situation about {topic}. Include one sentence pattern from this lesson, "
            f"then add one true or invented detail. Do not copy this model exactly: {model} Submit your draft first."
        ),
        "goal": f"Produce a short A1 message about {topic} with a clear meaning.",
        "constraints": [
            "Wait for the learner draft before feedback.",
            "Give at most two brief improvement points about meaning, word order, or target use.",
            "Do not replace the learner draft with a complete rewritten answer.",
        ],
    }


def _exercise(legacy: Mapping[str, Any], model: str, topic: str) -> dict[str, Any]:
    exercise = dict(legacy)
    kind = exercise["type"]
    target_ids = list(exercise["target_ids"])
    if kind == "multiple_choice":
        exercise.update({
            "prompt": f"Choose the sentence that correctly uses the language for {topic}.",
            "options": [model, f"{model} Please use the words in a different order.", f"{topic.title()} is an English sentence."],
            "correct_answer": model,
        })
    elif kind == "fill_blank":
        answer = exercise["acceptable_answers"][0]
        sentence = model.replace(answer, "_____", 1)
        exercise.update({"prompt": f"Complete the natural sentence about {topic}: {sentence}", "acceptable_answers": [answer]})
    elif kind == "matching":
        exercise.update({
            "prompt": f"Match each useful English expression with its practical use in {topic}.",
            "pairs": [
                {"left": model, "right": f"A model sentence for {topic}."},
                {"left": topic.title(), "right": "The everyday situation for this lesson."},
            ],
        })
    elif kind == "ordering":
        words = model.rstrip(".?!").split()
        split_at = max(1, len(words) // 2)
        clauses = [" ".join(words[:split_at]), " ".join(words[split_at:])]
        if len(set(clauses)) != len(clauses) or not clauses[1]:
            clauses = [f"Start: {model}", f"Then add one clear detail about {topic}."]
        exercise.update({
            "prompt": f"Put these two parts in a natural order to make a message about {topic}.",
            "items": list(reversed(clauses)), "correct_order": clauses,
        })
    elif kind in {"reading", "listening"}:
        question = exercise["questions"][0]
        exercise.update({
            "prompt": f"Read the short message and answer the question about {topic}.",
            "stimulus": model,
            "questions": [{"question": question["question"], "acceptable_answers": question["acceptable_answers"]}],
        })
    elif kind in {"speaking", "writing"}:
        exercise.update({
            "prompt": f"Make a short, personal response about {topic}. Use the lesson language and add one detail that is yours.",
            "rubric": {"criteria": [
                f"The response communicates a clear meaning about {topic}.",
                "The response uses the allocated language in an understandable form.",
                "The response adds an appropriate personal or invented detail.",
            ]},
        })
    exercise["target_ids"] = target_ids
    return exercise


def _lesson_card(legacy: Mapping[str, Any], detail: tuple[str, str, str, str]) -> dict[str, Any]:
    transcript, question, answer, pronunciation = detail
    model = _model_from_legacy(legacy)
    topic = legacy["title"].casefold()
    target_ids = _target_ids(legacy)
    roleplay = _roleplay(topic, model)
    writing = _writing(topic, model)
    return {
        "lesson_id": legacy["lesson_id"], "title": legacy["title"], "duration_minutes": 30,
        "objective_target_ids": target_ids,
        "objectives": list(legacy["objectives"]),
        "content_sections": [
            {"id": "form-and-meaning", "section_type": "explanation", "title": "Form and meaning", "target_ids": target_ids,
             "body": f"Use this lesson language to communicate a simple real-life meaning: {legacy['objectives'][0]} Model: “{model}” Notice the important words and the word order. Mẹo tiếng Việt: hãy hiểu ý của cả câu trước, rồi nói theo cụm ngắn; không cần dịch từng từ."},
            {"id": "guided-context", "section_type": "dialogue", "title": "Guided context", "target_ids": target_ids,
             "body": f"Read this short situation. A learner needs to use {topic} clearly and politely. One useful response is: “{model}” Say the model once, then change one safe detail such as a name, place, time, colour, or item when the meaning allows."},
            {"id": "use-it", "section_type": "review", "title": "Use it", "target_ids": target_ids,
             "body": f"Practise for meaning, not only for memory. Imagine one everyday situation where {topic} is useful. First use the model, then make one small change. Check: Is the message clear? Is the target language in the right place? Can another person answer you?"},
        ],
        "exercises": [_exercise(exercise, model, topic) for exercise in legacy["exercises"]],
        "practice": {
            "listening": {"instruction": f"Listen once without reading to a short exchange about {topic}. Answer the question, then ask to see the transcript and listen again.", "goal": f"Understand one clear detail in a short exchange about {topic}.", "target_ids": target_ids, "transcript": transcript, "question": question, "answer": answer, "media_required": False, "constraints": ["Do not reveal the transcript before the learner answers.", "Ask exactly one comprehension question before showing the transcript.", "Use only the supplied project-authored transcript."]},
            "speaking": {"instruction": roleplay["instruction"], "goal": roleplay["goal"], "target_ids": target_ids, "constraints": roleplay["constraints"]},
            "pronunciation": {"instruction": f"Read the concrete sound target aloud: {pronunciation} Then read one lesson sentence slowly and once at normal speed.", "goal": "Produce the identified sound, stress, or rhythm feature clearly in a useful phrase.", "target_ids": target_ids, "target": pronunciation, "without_audio": "NOT_ASSESSED", "constraints": ["Assess pronunciation only when learner audio is available.", "Return NOT_ASSESSED when no audio is supplied.", "Give one observable sound, stress, or rhythm point rather than general pronunciation advice."]},
            "writing": {"instruction": writing["instruction"], "goal": writing["goal"], "target_ids": target_ids, "feedback_boundary": "FEEDBACK_ONLY_NO_REPLACEMENT", "constraints": writing["constraints"]},
        },
    }


def seed_authoring_source(*, predecessor_units: Path, output_path: Path) -> Path:
    """Create the retained v2 authoring source from specifically repaired lesson cards."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite Full A1 authoring source: {output_path}")
    details = _detail_by_lesson()
    if len(details) != 50:
        raise ValueError("Full A1 authoring details must cover exactly fifty lessons")
    cards = []
    for path in sorted(predecessor_units.glob("unit-*.json")):
        unit = load_document(path)
        for legacy in unit["lessons"]:
            detail = details.get(legacy["lesson_id"])
            if detail is None:
                raise ValueError(f"no repaired authoring detail for {legacy['lesson_id']}")
            cards.append(_lesson_card(legacy, detail))
    source = {"source_version": "A1_FULL_PRACTICAL_CONTENT_V2", "content_origin": "PROJECT_AUTHORED", "lessons": cards}
    source["source_sha256"] = sha256_json(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_path, source)
    return output_path


def _validate_source(source: Mapping[str, Any], allocation: Mapping[str, Any]) -> list[dict[str, Any]]:
    if source.get("source_version") != "A1_FULL_PRACTICAL_CONTENT_V2" or source.get("content_origin") != "PROJECT_AUTHORED":
        raise ValueError("unsupported Full A1 practical authoring source")
    expected_hash = sha256_json({key: value for key, value in source.items() if key != "source_sha256"})
    if source.get("source_sha256") != expected_hash:
        raise ValueError("Full A1 authoring source hash mismatch")
    lessons = source.get("lessons")
    if not isinstance(lessons, list):
        raise ValueError("Full A1 authoring source must contain lessons")
    expected_ids = [row["lesson_id"] for row in allocation["lessons"]]
    actual_ids = [lesson.get("lesson_id") for lesson in lessons if isinstance(lesson, Mapping)]
    if actual_ids != expected_ids:
        raise ValueError("Full A1 authoring source must cover the ordered allocation exactly")
    for lesson, row in zip(lessons, allocation["lessons"], strict=True):
        if set(lesson["objective_target_ids"]) != {item["target_id"] for item in row["target_usage"]}:
            raise ValueError(f"authoring target scope drift: {lesson['lesson_id']}")
        text = json.dumps(lesson, ensure_ascii=False).casefold()
        if any(phrase in text for phrase in _LEGACY_PHRASES):
            raise ValueError(f"authoring source retains rejected legacy boilerplate: {lesson['lesson_id']}")
        if len(lesson["content_sections"]) < 3 or lesson["duration_minutes"] < 25:
            raise ValueError(f"authoring source lacks practical lesson structure: {lesson['lesson_id']}")
        listening = lesson["practice"]["listening"]
        visible = " ".join(section["body"] for section in lesson["content_sections"]) + " " + " ".join(exercise["prompt"] for exercise in lesson["exercises"])
        if listening["transcript"].casefold() in visible.casefold():
            raise ValueError(f"authoring listening transcript is visible before attempt: {lesson['lesson_id']}")
        speaking = lesson["practice"]["speaking"]["instruction"].casefold()
        if not all(marker in speaking for marker in ("roleplay:", "scenario:", "tutor opening:")):
            raise ValueError(f"authoring speaking protocol is not executable roleplay: {lesson['lesson_id']}")
        if "concrete sound target" not in lesson["practice"]["pronunciation"]["instruction"].casefold():
            raise ValueError(f"authoring pronunciation target is not concrete: {lesson['lesson_id']}")
    return [dict(lesson) for lesson in lessons]


def compile_authoring_source(*, source_path: Path, allocation_path: Path, output_root: Path) -> Path:
    """Compile a retained lesson source to closed v2 units and a content manifest."""
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite Full A1 content output: {output_root}")
    source = load_document(source_path)
    allocation = load_document(allocation_path)
    lessons = _validate_source(source, allocation)
    temporary = output_root.parent / f".{output_root.name}.tmp"
    if temporary.exists():
        raise FileExistsError(f"refusing to overwrite Full A1 temporary output: {temporary}")
    temporary.mkdir(parents=True)
    try:
        units_dir = temporary / "units"
        units_dir.mkdir()
        entries = []
        for index in range(10):
            rows = allocation["lessons"][index * 5 : (index + 1) * 5]
            unit = {"schema_version": "2.0", "record_type": "a1_full_content_unit", "unit_id": rows[0]["unit_id"], "tier": rows[0]["tier"], "content_origin": "PROJECT_AUTHORED", "lessons": lessons[index * 5 : (index + 1) * 5]}
            validate_instance(unit, "a1-full-content-unit-v2")
            relative = f"units/unit-{index + 1:02d}.json"
            path = temporary / relative
            _write_json(path, unit)
            entries.append({"unit_id": unit["unit_id"], "tier": unit["tier"], "path": relative, "sha256": _sha256_file(path)})
        manifest = {"schema_version": "2.0", "record_type": "a1_full_content_manifest", "allocation_sha256": sha256_json(allocation), "content_origin": "PROJECT_AUTHORED", "units": entries}
        manifest["manifest_sha256"] = sha256_json(manifest)
        validate_instance(manifest, "a1-full-content-manifest-v2")
        _write_json(temporary / "content-manifest.json", manifest)
        temporary.replace(output_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output_root / "content-manifest.json"
