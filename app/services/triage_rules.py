"""Transparent, explicit triage-support rules (PRELIMINARY DEMONSTRATION LOGIC).

This is keyword matching with simple negation handling. It is NOT clinically
validated and must be reviewed by qualified clinicians before any real use.
Design principles:
  * Conservative: uncertainty never lowers urgency.
  * Negated symptoms ("no chest pain") are not treated as present.
  * Ambiguous negation ("no fever and chest pain") is still flagged, with a note.
  * Mild/slight wording never downgrades an emergency warning sign.
  * No diagnoses, medication, dosages or treatment plans are produced.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

EMERGENCY = "emergency"
URGENT = "urgent"
ROUTINE = "routine"
UNDETERMINED = "undetermined"

URGENCY_RANK: Dict[str, int] = {UNDETERMINED: 0, ROUTINE: 1, URGENT: 2, EMERGENCY: 3}

# (id, label, level, regex patterns). Patterns are matched on lowercase text.
RULES: List[Tuple[str, str, str, List[str]]] = [
    # --- Potentially life-threatening warning signs ---
    ("chest_pain", "chest pain or pressure", EMERGENCY,
     [r"chest (pain|pressure|tightness|discomfort)", r"pain in (my |the )?chest",
      r"tight(ness)? in (my |the )?chest", "सीने में दर्द", "सीने में जकड़न"]),
    ("breathing_difficulty", "difficulty breathing", EMERGENCY,
     [r"(difficulty|trouble|hard to|struggling to|can'?t|cannot|unable to) breath(e|ing)",
      r"shortness of breath", r"short of breath", r"breathless(ness)?", r"gasping",
      "सांस लेने में तकलीफ", "सांस फूल"]),
    ("stroke_signs", "possible stroke warning signs", EMERGENCY,
     [r"face (is )?droop(ing|y)?", r"slurred speech", r"slurring", r"sudden (weakness|numbness)",
      r"weakness (on|in) one side", r"can'?t (move|lift) (my |the )?(arm|leg)",
      r"sudden (confusion|trouble speaking|loss of vision)"]),
    ("unconscious", "loss of consciousness", EMERGENCY,
     [r"unconscious", r"unresponsive", r"passed out", r"fainted", r"blacked out",
      r"not responding", r"collapsed", "बेहोश"]),
    ("seizure", "seizure", EMERGENCY, [r"seizure", r"convulsion", r"fitting", "दौरा"]),
    ("severe_bleeding", "severe or uncontrolled bleeding", EMERGENCY,
     [r"severe bleeding", r"heavy bleeding", r"bleeding (heavily|a lot|won'?t stop|will not stop)",
      r"uncontrolled bleeding", r"vomit(ing|ed)? blood", r"coughing (up )?blood",
      r"blood in (my |the )?vomit"]),
    ("anaphylaxis", "possible severe allergic reaction", EMERGENCY,
     [r"throat (is )?(swelling|closing|tight)", r"swollen (tongue|throat|lips)",
      r"tongue (is )?swelling", r"anaphyla\w+"]),
    ("self_harm", "thoughts of self-harm or suicide", EMERGENCY,
     [r"suicid\w+", r"kill (myself|himself|herself)", r"want to die", r"end my life",
      r"self[- ]harm", r"hurt myself"]),
    ("overdose", "possible poisoning or overdose", EMERGENCY,
     [r"overdos\w+", r"poison(ed|ing)?", r"swallowed (a lot of|too many)"]),
    # --- Needs prompt (same-day) assessment ---
    ("high_fever", "high fever", URGENT,
     [r"high fever", r"fever (of|above|over) 10[2-9]", r"fever (of|above|over) 39",
      r"fever (for|since) (more than |over )?(3|three|4|four|5|five|\d{2}) days",
      r"fever (that )?(won'?t|will not) (go|come) down"]),
    ("severe_abdominal_pain", "severe abdominal pain", URGENT,
     [r"severe (abdominal|stomach|belly) pain", r"(abdominal|stomach|belly) pain (is )?severe",
      r"unbearable (stomach|abdominal|belly) pain"]),
    ("severe_headache", "severe or sudden headache", URGENT,
     [r"severe headache", r"worst headache", r"sudden headache", r"thunderclap"]),
    ("persistent_vomiting", "persistent vomiting or dehydration", URGENT,
     [r"persistent vomiting", r"vomiting (for|since) (more than |over )?(2|two|3|three|\d{2}) days",
      r"can'?t keep (anything|fluids|water) down", r"dehydrat\w+", r"not (passing|passed) urine"]),
    ("blood_in_stool_urine", "blood in stool or urine", URGENT,
     [r"blood in (my |the )?(stool|urine|poop)", r"black (tarry )?stool", r"bloody (stool|urine)"]),
    ("pregnancy_concern", "symptom during pregnancy", URGENT,
     [r"pregnan\w+ (and|with|having) (bleeding|pain|cramp\w*)",
      r"(bleeding|pain) (while|during|in) pregnan\w+"]),
    # --- Common symptoms recorded without raising urgency ---
    ("fever", "fever", ROUTINE, [r"fever", r"temperature", r"feverish", "बुखार"]),
    ("cough", "cough", ROUTINE, [r"cough(ing)?", "खांसी"]),
    ("sore_throat", "sore throat", ROUTINE, [r"sore throat", r"throat pain"]),
    ("headache", "headache", ROUTINE, [r"headache", r"head ache", "सिर दर्द"]),
    ("nausea_vomiting", "nausea or vomiting", ROUTINE, [r"nausea", r"nauseous", r"vomit(ing|ed)?", "उल्टी"]),
    ("diarrhea", "diarrhea", ROUTINE, [r"diarrh?oea", r"loose (stool|motion)s?", "दस्त"]),
    ("abdominal_pain", "abdominal pain", ROUTINE, [r"(abdominal|stomach|belly) (pain|ache)", r"stomach ache"]),
    ("body_ache", "body ache or fatigue", ROUTINE, [r"body ache", r"body pain", r"fatigue", r"tired(ness)?", r"weakness"]),
    ("runny_nose", "runny or blocked nose", ROUTINE, [r"runny nose", r"blocked nose", r"stuffy nose", r"sneez\w+"]),
    ("rash", "skin rash or itching", ROUTINE, [r"rash", r"itching", r"itchy"]),
    ("dizziness", "dizziness", ROUTINE, [r"dizz(y|iness)", r"lightheaded", r"light-headed"]),
]

# Where a symptom has both an urgent and a routine variant, the routine variant
# is suppressed from "reported symptoms" when the urgent one matched.
SUPERSEDES: Dict[str, str] = {
    "high_fever": "fever",
    "severe_abdominal_pain": "abdominal_pain",
    "severe_headache": "headache",
    "persistent_vomiting": "nausea_vomiting",
}

NEGATION_CUES = (
    "no", "not", "without", "denies", "denied", "never", "none", "neither", "nor",
    "free of", "absence of", "negative for", "ruled out",
)
_NEG_WORD_RE = re.compile(r"\b(no|not|without|denies|denied|never|none|neither|nor)\b|free of|absence of|negative for|ruled out|n't\b")
_COORDINATORS = {"and", "or", "nor", "but", "with"}
_CLAUSE_SPLIT_RE = re.compile(r"[.;!?,\n]+|\bbut\b|\bhowever\b|\balthough\b|\bthough\b|\bexcept\b")
_HINDI_NEG = ("नहीं", "नही", "बिना")
NEG_WINDOW_WORDS = 5

EMERGENCY_ADVICE = (
    "Possible emergency warning sign reported. Seek emergency medical help immediately "
    "(call your local emergency number, e.g. {num} in India) and do not wait for this tool."
)


@dataclass
class Finding:
    rule_id: str
    label: str
    level: str
    evidence: str
    negated: bool = False
    ambiguous_negation: bool = False


@dataclass
class RulesResult:
    urgency: str
    explanation: str
    reported_symptoms: List[str] = field(default_factory=list)
    negated_symptoms: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    emergency_advice: Optional[str] = None


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _clauses(text: str) -> List[str]:
    return [c.strip() for c in _CLAUSE_SPLIT_RE.split(text) if c and c.strip()]


def _negation_state(clause: str, start: int, end: int) -> Tuple[bool, bool]:
    """Return (negated, ambiguous) for a match at clause[start:end]."""
    before = clause[:start]
    # Latin-script negation within a short window before the match.
    words = re.findall(r"[\w']+", before)
    window_text = " ".join(words[-NEG_WINDOW_WORDS:])
    cue = None
    for m in _NEG_WORD_RE.finditer(window_text):
        cue = m
    if cue is not None:
        tail = window_text[cue.end():].split()
        if any(w in _COORDINATORS for w in tail):
            # e.g. "no fever and chest pain": scope is unclear -> stay conservative.
            return False, True
        return True, False
    # Hindi negation anywhere in the clause is ambiguous (word order differs).
    if any(h in clause for h in _HINDI_NEG) and re.search(r"[\u0900-\u097F]", clause[start:end]):
        return False, True
    return False, False


def _find_all(text: str) -> List[Finding]:
    findings: List[Finding] = []
    for clause in _clauses(text):
        for rule_id, label, level, patterns in RULES:
            for pat in patterns:
                for m in re.finditer(pat, clause):
                    negated, ambiguous = _negation_state(clause, m.start(), m.end())
                    findings.append(Finding(rule_id, label, level, m.group(0), negated, ambiguous))
    return findings


def assess(text: str, emergency_number: str = "112") -> RulesResult:
    """Run the rules over free text and return an explained urgency."""
    clean = normalize(text)
    if not clean or len(re.sub(r"[\W_]+", "", clean)) < 3:
        return RulesResult(
            urgency=UNDETERMINED,
            explanation="No usable symptom description was provided, so urgency cannot be assessed.",
            uncertainties=["Symptom description is empty or unreadable."],
        )

    all_findings = _find_all(clean)
    present = [f for f in all_findings if not f.negated]
    negated_only: Dict[str, Finding] = {}
    present_ids = {f.rule_id for f in present}
    for f in all_findings:
        if f.negated and f.rule_id not in present_ids:
            negated_only.setdefault(f.rule_id, f)

    # Conflict: same symptom both negated and affirmed -> affirmed wins (conservative).
    uncertainties: List[str] = []
    for f in all_findings:
        if f.negated and f.rule_id in present_ids:
            note = f"Conflicting statements about '{f.label}'; treated as present to be safe."
            if note not in uncertainties:
                uncertainties.append(note)
    for f in present:
        if f.ambiguous_negation:
            note = (f"Unclear whether '{f.label}' is present or denied; treated as possibly present to be safe.")
            if note not in uncertainties:
                uncertainties.append(note)

    # Build de-duplicated, ordered symptom lists.
    seen: Dict[str, Finding] = {}
    for f in present:
        seen.setdefault(f.rule_id, f)
    for hi, lo in SUPERSEDES.items():
        if hi in seen:
            seen.pop(lo, None)
    reported = [f.label for f in seen.values()]
    negated_labels = [f.label for f in negated_only.values()]
    top = max((URGENCY_RANK[f.level] for f in seen.values()), default=0)
    level = {v: k for k, v in URGENCY_RANK.items()}[top]

    if not seen:
        explanation = ("No symptom covered by the demonstration rules was found as present. "
                       "This does not mean nothing is wrong; urgency cannot be determined.")
        if negated_labels:
            explanation += " Symptoms reported as absent: " + ", ".join(negated_labels) + "."
        uncertainties.append("Symptoms were not recognised by the limited rule set; a clinician should review.")
        return RulesResult(UNDETERMINED, explanation, [], negated_labels, all_findings, uncertainties)

    triggers = [f.label for f in seen.values() if f.level == level]
    advice = None
    if level == EMERGENCY:
        advice = EMERGENCY_ADVICE.format(num=emergency_number)
        explanation = ("Classified as EMERGENCY because a potentially life-threatening warning sign was reported: "
                       + ", ".join(triggers) + ". Seek emergency medical help immediately.")
    elif level == URGENT:
        explanation = ("Classified as URGENT because the report includes: " + ", ".join(triggers)
                       + ". Prompt assessment by a healthcare professional is advised. If symptoms worsen, "
                         "seek emergency help immediately.")
    else:
        explanation = ("Classified as ROUTINE because only common symptoms covered by the demonstration rules were "
                       "reported: " + ", ".join(triggers) + ". This is not a diagnosis; seek care sooner if symptoms "
                       "worsen or new warning signs appear.")
    if negated_labels:
        explanation += " Symptoms reported as absent: " + ", ".join(negated_labels) + "."
    return RulesResult(level, explanation, reported, negated_labels, all_findings, uncertainties, advice)


def missing_information(text: str) -> List[str]:
    """Generic follow-up gaps; never invents facts about the person."""
    t = normalize(text)
    gaps = []
    if not re.search(r"\b(\d+|one|two|three|four|five|few|several)\s*(day|days|hour|hours|week|weeks|month|months|minute|minutes)\b|since|yesterday|today|for a while", t):
        gaps.append("Duration or onset of symptoms was not stated.")
    if not re.search(r"\b(mild|moderate|severe|worst|unbearable|slight|\d/10|\d out of 10)\b", t):
        gaps.append("Severity of symptoms was not stated.")
    if not re.search(r"\b(\d{1,3}\s*(years?|yrs?|y/?o|months?)\b|age|infant|child|baby|elderly)", t):
        gaps.append("Age of the person was not stated.")
    gaps.append("Medical history, medications and allergies were not assessed.")
    return gaps
