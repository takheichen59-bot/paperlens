"""Conservative, auditable role candidates; never a scientific correctness verdict.

The original materials and numeric candidates remain untouched. Decisions cite
exact sentences and, where needed, the preceding attribution in the same block.
Unknown or mixed ownership is retained for review rather than assigned by unit.
"""
import re

VERSION = "context-roles-v1"
MATERIAL_ROLES = {"study_subject", "background", "comparator", "reagent_or_environment", "uncertain"}
NUMERIC_ROLES = {"own_result", "simulation_parameter", "experimental_condition", "cited_result", "uncertain"}
MATERIAL_LABELS = {"study_subject": "本文研究对象（规则候选）", "background": "背景提及",
    "comparator": "本文对照材料（规则候选）", "reagent_or_environment": "试剂 / 环境", "uncertain": "归属不确定"}
NUMERIC_LABELS = {"own_result": "本文结果（规则候选）", "simulation_parameter": "模拟参数",
    "experimental_condition": "实验条件", "cited_result": "引用 / 背景数值", "uncertain": "归属不确定"}

PRIOR = re.compile(r"\b(?:in (?:recent|previous|prior|earlier) (?:work|studies|research)|"
    r"(?:previous|prior|earlier|other) (?:stud\w*|work|report\w*)|"
    r"(?:[A-Z][a-z]+ et al\.|collaborators)\s*(?:\[.{1,25}?\])?\s*(?:have |has )?(?:report\w*|investigat\w*|found|show\w*)|"
    r"(?:has|have) been (?:reported|demonstrated|found)|previous record|"
    r"best known|well known|canonical example)\b", re.I)
OWN = re.compile(r"\b(?:we (?:have )?(?:stud\w*|investigat\w*|analy[sz]\w*|explor\w*|"
    r"observ\w*|find|found|show\w*|report\w*|synthesi[sz]\w*|compar\w*|simulat\w*|measur\w*|used?)|"
    r"(?:this|our) (?:paper|work|study|results?|simulations?|measurements?)\s+(?:\w+\s+){0,3}"
    r"(?:analy[sz]\w*|investigat\w*|show\w*|demonstrat\w*|reveal\w*|report\w*))\b", re.I)
CITATION = re.compile(r"\[\d[\d\s,–−-]*\]")
PARAMETER = re.compile(r"\b(?:chosen|set to|used|using|cutoff|cut-off|basis|sampling|"
    r"thermaliz\w*|time step|excitation|laser|temperature.dependent|growth conditions|"
    r"anneal\w*|dried|ampul\w*|rod|diameter|wavelength|filter|kept constant)\b", re.I)
COMPUTATIONAL = re.compile(r"\b(?:simulat\w*|molecular dynamics|comput\w*|plane.wave|cutoff|cut-off|"
    r"supercell|Brillouin|density functional|relaxation|thermal noise)\b", re.I)
RESULT = re.compile(r"\b(?:we (?:have )?(?:observ\w*|find|found|show\w*)|"
    r"(?:our|these|the) results? (?:show|reveal|indicate)|"
    r"volume (?:of .{0,60}is .{0,30})?(?:increas\w*|decreas\w*|smaller|larger)|"
    r"(?:is|was) (?:lower|higher) in energy|(?:is|was) found|we observed)\b", re.I)


def normalize(text):
    """Matching only; quotations and stored offsets always use original text."""
    return re.sub(r"\s+", " ", re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text))


def material_role(name, sentence, preceding, section, title):
    text = normalize(sentence)
    own = bool(OWN.search(text))
    prior = bool(PRIOR.search(text) or (PRIOR.search(normalize(preceding)) and not own))
    if prior and not own:
        return "background", "explicit_prior_work_context"
    if prior and own:
        return "uncertain", "mixed_current_and_prior_work"
    escaped = re.escape(name)
    if re.search(r"(?:compar\w* .{0,100}?\b(?:with|to)|versus|against|control(?: material)?(?: of)?)\s+(?:\w+\s+){0,2}" + escaped, text, re.I) or re.search(escaped + r".{0,30}\bas (?:a |the )?(?:control|reference sample)\b", text, re.I):
        return "comparator", "explicit_current_comparison"
    if re.search(r"\b(?:washed|rinsed|dissolved|sealed|atmosphere|solvent)\b.{0,45}" + escaped, text, re.I):
        return "reagent_or_environment", "procedural_reagent_or_environment"
    if section == "introduction" and not own:
        return "background", "background_without_current_action"
    plain_title = re.sub(r"[$_{}\\]", "", normalize(title))
    if re.search(r"(?<!\w)" + escaped + r"(?!\w)", plain_title, re.I):
        return "study_subject", "material_in_paper_title"
    if own and re.search(r"\b(?:stud\w*|investigat\w*|analy[sz]\w*|explor\w*|synthesi[sz]\w*|compar\w*)\b.{0,100}" + escaped, text, re.I):
        return "study_subject", "explicit_current_study_action"
    if section == "methods" and re.search(escaped + r".{0,45}\b(?:samples?|crystals?|nanoparticles?)\b.{0,35}\b(?:grown|prepared|synthesi[sz]ed|measured)\b", text, re.I):
        return "study_subject", "current_sample_preparation"
    if CITATION.search(text) and not own:
        return "background", "background_or_citation_without_current_action"
    return "uncertain", "insufficient_role_context"


def numeric_role(sentence, preceding, section, methods_context=""):
    text = normalize(sentence); before = normalize(preceding)
    own = bool(OWN.search(text))
    previous_own = list(OWN.finditer(before)); previous_prior = list(PRIOR.finditer(before))
    if previous_own and (not previous_prior or previous_own[-1].start() > previous_prior[-1].start()):
        before = ""
    prior = bool(PRIOR.search(text) or (PRIOR.search(before) and not own))
    if prior:
        return ("uncertain", "mixed_current_and_prior_work") if own else ("cited_result", "explicit_prior_work_context")
    # A citation can describe an adopted method; it does not alone transfer the
    # ownership of a result. Mixed comparisons stay unresolved.
    if own and CITATION.search(text):
        return "uncertain", "current_statement_with_citation_requires_review"
    if section == "introduction" and CITATION.search(text):
        return "cited_result", "background_citation"
    if (RESULT.search(text) and PARAMETER.search(text)) or re.search(r"\b(?:resulting in|experimental value|compared with|compared to|versus)\b", text, re.I):
        return "uncertain", "mixed_result_condition_or_comparison"
    if RESULT.search(text) and (own or section in {"results", "discussion", "conclusions", "inferred_results"}):
        return "own_result", "current_result_statement"
    if PARAMETER.search(text) and section == "methods":
        if re.search(r"\b(?:laser|growth|anneal\w*|dried|ampul\w*|rod|diameter|filter|wavelength)\b", text, re.I):
            return "experimental_condition", "experimental_procedure"
        if COMPUTATIONAL.search(text) or COMPUTATIONAL.search(normalize(methods_context)):
            return "simulation_parameter", "computational_procedure"
        return "experimental_condition", "method_condition"
    if section in {"results", "discussion", "conclusions"} and not CITATION.search(text):
        return "own_result", "result_section_without_external_attribution"
    return "uncertain", "insufficient_or_mixed_numeric_context"


def build_attribution(record, body, quote, sentence_ranges):
    """Add an independent interpretation layer, not a review or legacy edit."""
    first_methods = next((i for i, b in enumerate(body) if b.kind.value == "methods"), None)
    methods_context = " ".join(b.text for b in body if b.kind.value == "methods")
    mentions = {name: [] for name in record["materials"]}
    numeric = []
    for index, block in enumerate(body):
        section = block.kind.value
        # Only use position to recognize unlabelled introduction when a real
        # methods boundary exists. Unknown late sections are left unknown.
        if section == "unknown" and first_methods is not None and index < first_methods and block.page_number > 1:
            section = "introduction"
        for start, end in sentence_ranges(block.text):
            sentence = block.text[start:end]; preceding = block.text[:start]
            # An explicit current-work statement resets an earlier prior-work
            # attribution for following sentences in this same PDF block.
            reset = list(OWN.finditer(normalize(preceding)))
            prior = list(PRIOR.finditer(normalize(preceding)))
            if reset and (not prior or reset[-1].start() > prior[-1].start()):
                preceding = ""
            for name in record["materials"]:
                if not re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", sentence, re.I):
                    continue
                role, reason = material_role(name, sentence, preceding, section, record["meta"].get("title", ""))
                evidence = quote(block, "material_roles", start, end)
                context = []
                if preceding.strip() and reason in {"explicit_prior_work_context", "mixed_current_and_prior_work"}:
                    context = [quote(block, "attribution_context", 0, start)["evidence_id"]]
                mentions[name].append({"role": role, "reason": reason, "evidence_ids": [evidence["evidence_id"]], "context_evidence_ids": context})
    # Numeric candidates already have exact source sentences; locate their
    # position in the extraction view to obtain preceding attribution.
    by_id = {s["evidence_id"]: s for s in record["source_snippets"]}
    for i, candidate in enumerate(record["experimental_data"]):
        evidence = by_id[candidate["evidence_ids"][0]]
        located = next(((j, b) for j, b in enumerate(body) if b.block_id == evidence["block_id"] and b.raw_start <= evidence["start_offset"] < evidence["end_offset"] <= b.raw_end), None)
        if located is None:
            raise ValueError("Numeric candidate outside extraction view")
        index, block = located; start = evidence["start_offset"] - block.raw_start
        preceding = block.text[:start]; section = block.kind.value
        if section == "unknown" and first_methods is not None:
            section = "introduction" if index < first_methods else "inferred_results"
        role, reason = numeric_role(candidate["text"], preceding, section, methods_context)
        context = []
        if preceding.strip() and reason in {"explicit_prior_work_context", "mixed_current_and_prior_work"}:
            context = [quote(block, "attribution_context", 0, start)["evidence_id"]]
        numeric.append({"candidate_index": i, "role": role, "reason": reason,
            "evidence_ids": list(candidate["evidence_ids"]), "context_evidence_ids": context})
    materials = []
    for name, items in mentions.items():
        roles = {m["role"] for m in items}
        # Same substance can be the current subject AND occur in cited work.
        # Preserve all mention decisions. Multiple current roles stay mixed.
        current = roles & {"study_subject", "comparator", "reagent_or_environment"}
        role = next(iter(current)) if len(current) == 1 else ("background" if roles == {"background"} else "uncertain")
        materials.append({"name": name, "role": role, "mentions": items,
            "evidence_ids": list(dict.fromkeys(e for m in items for e in m["evidence_ids"]))})
    return {"version": VERSION, "mode": "rule_candidates_not_scientific_validation", "review_status": "unreviewed",
        "materials": materials, "numeric": numeric,
        "limitations": ["Material roles cover existing chemical candidates only; missing species are not inferred.",
            "Role and ownership rules are incomplete; exact quotations do not establish scientific correctness.",
            "Unknown section boundaries and mixed comparisons require manual review."]}


def validate_attribution(record):
    layer = record.get("attribution")
    if layer is None:  # Historical research-1 records remain explicitly unclassified.
        return
    if layer.get("version") != VERSION or layer.get("review_status") != "unreviewed":
        raise ValueError("Unsupported attribution layer")
    by_id = {s["evidence_id"]: s for s in record["source_snippets"]}
    if [m["name"] for m in layer["materials"]] != record["materials"]:
        raise ValueError("Attribution material candidate mismatch")
    for material in layer["materials"]:
        if material["role"] not in MATERIAL_ROLES or not material["mentions"]:
            raise ValueError("Invalid material role")
        expected = list(dict.fromkeys(e for m in material["mentions"] for e in m["evidence_ids"]))
        if material["evidence_ids"] != expected:
            raise ValueError("Material evidence aggregation mismatch")
        for mention in material["mentions"]:
            if mention["role"] not in MATERIAL_ROLES or not mention["evidence_ids"]:
                raise ValueError("Invalid material mention")
            for eid in mention["evidence_ids"]:
                evidence = by_id.get(eid)
                if not evidence or evidence["field"] != "material_roles" or not re.search(r"(?<!\w)" + re.escape(material["name"]) + r"(?!\w)", evidence["text"], re.I):
                    raise ValueError("Material mention evidence mismatch")
            _validate_context(mention, by_id)
    if len(layer["numeric"]) != len(record["experimental_data"]):
        raise ValueError("Numeric attribution coverage mismatch")
    for i, numeric in enumerate(layer["numeric"]):
        if numeric["candidate_index"] != i or numeric["role"] not in NUMERIC_ROLES or numeric["evidence_ids"] != record["experimental_data"][i]["evidence_ids"]:
            raise ValueError("Numeric attribution evidence mismatch")
        _validate_context(numeric, by_id)


def _validate_context(decision, by_id):
    for eid in decision.get("context_evidence_ids", []):
        if eid not in by_id or by_id[eid]["field"] != "attribution_context":
            raise ValueError("Attribution context evidence mismatch")
