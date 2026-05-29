"""
Validator Agent — Takes extracted JSON + customer rule set and produces
a field-by-field validation result: match, mismatch, or uncertain.

Mismatches include what was found vs what was expected.
Uncertain fields always surface — never silently approved.
"""

import json
import os
from difflib import SequenceMatcher


def _similarity(a: str, b: str) -> float:
    """Compute string similarity ratio (0.0–1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _validate_field(field_name: str, extracted: dict, rule: dict) -> dict:
    """
    Validate a single field against its rule.

    Returns dict with:
      - status: "match" | "mismatch" | "uncertain"
      - found: extracted value
      - expected: expected value from rule
      - confidence: extraction confidence
      - reason: human-readable explanation
    """
    field_data = extracted.get(field_name, {})
    found_value = field_data.get("value")
    confidence = field_data.get("confidence", 0.0)
    expected = rule.get("expected")
    match_type = rule.get("match_type", "exact")

    result = {
        "field": field_name,
        "found": found_value,
        "expected": expected,
        "confidence": confidence,
        "rule_description": rule.get("description", ""),
    }

    # Low confidence → uncertain, regardless of match
    if confidence < 0.7:
        if found_value is None:
            result["status"] = "uncertain"
            result["reason"] = f"Field not found in document (confidence: {confidence:.2f}). Requires manual review."
        else:
            result["status"] = "uncertain"
            result["reason"] = f"Low extraction confidence ({confidence:.2f}). Value found: '{found_value}'. Requires manual verification."
        return result

    # Field not found
    if found_value is None:
        if match_type == "present":
            result["status"] = "mismatch"
            result["reason"] = "Field is required but was not found in the document."
        else:
            result["status"] = "mismatch"
            result["reason"] = f"Field not found. Expected: '{expected}'."
        return result

    # Match type: "present" — just needs to exist and be non-empty
    if match_type == "present":
        if found_value and str(found_value).strip():
            result["status"] = "match"
            result["reason"] = "Field is present and non-empty."
        else:
            result["status"] = "mismatch"
            result["reason"] = "Field is required but is empty."
        return result

    # Match type: "exact"
    if match_type == "exact":
        if str(found_value).strip().lower() == str(expected).strip().lower():
            result["status"] = "match"
            result["reason"] = "Exact match."
        else:
            sim = _similarity(str(found_value), str(expected))
            if sim > 0.85:
                result["status"] = "uncertain"
                result["reason"] = (
                    f"Close but not exact match (similarity: {sim:.0%}). "
                    f"Found: '{found_value}', Expected: '{expected}'. Needs human review."
                )
            else:
                result["status"] = "mismatch"
                result["reason"] = f"Does not match. Found: '{found_value}', Expected: '{expected}'."
        return result

    # Match type: "fuzzy"
    if match_type == "fuzzy":
        sim = _similarity(str(found_value), str(expected))
        if sim > 0.80:
            result["status"] = "match"
            result["reason"] = f"Fuzzy match (similarity: {sim:.0%})."
        elif sim > 0.50:
            result["status"] = "uncertain"
            result["reason"] = (
                f"Partial match (similarity: {sim:.0%}). "
                f"Found: '{found_value}', Expected: '{expected}'. Needs human review."
            )
        else:
            result["status"] = "mismatch"
            result["reason"] = f"Does not match. Found: '{found_value}', Expected: '{expected}'."
        return result

    # Match type: "contains"
    if match_type == "contains":
        if str(expected).lower() in str(found_value).lower() or str(found_value).lower() in str(expected).lower():
            result["status"] = "match"
            result["reason"] = "Contains expected value."
        else:
            result["status"] = "mismatch"
            result["reason"] = f"Does not contain expected value. Found: '{found_value}', Expected: '{expected}'."
        return result

    # Unknown match type — flag as uncertain
    result["status"] = "uncertain"
    result["reason"] = f"Unknown match type: '{match_type}'. Requires manual review."
    return result


def validate(extracted: dict, rules_path: str) -> dict:
    """
    Validate all extracted fields against customer rules.

    Args:
        extracted: Output from the Extractor Agent.
        rules_path: Path to the customer rules JSON file.

    Returns:
        dict with:
          - customer_name: the customer being validated against
          - fields: list of field validation results
          - summary: counts of match/mismatch/uncertain
          - overall_status: "approved" | "needs_review" | "amendment_required"
    """
    with open(rules_path, "r") as f:
        rules_data = json.load(f)

    rules = rules_data.get("rules", {})
    field_results = []

    for field_name, rule in rules.items():
        result = _validate_field(field_name, extracted, rule)
        field_results.append(result)

    # Compute summary
    matches = sum(1 for r in field_results if r["status"] == "match")
    mismatches = sum(1 for r in field_results if r["status"] == "mismatch")
    uncertain = sum(1 for r in field_results if r["status"] == "uncertain")

    # Determine overall status
    if mismatches > 0:
        overall = "amendment_required"
    elif uncertain > 0:
        overall = "needs_review"
    else:
        overall = "approved"

    return {
        "customer_name": rules_data.get("customer_name", "Unknown"),
        "customer_id": rules_data.get("customer_id", "Unknown"),
        "fields": field_results,
        "summary": {
            "total_fields": len(field_results),
            "matches": matches,
            "mismatches": mismatches,
            "uncertain": uncertain,
        },
        "overall_status": overall,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python validator.py <extracted_json_path> <rules_path>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        extracted = json.load(f)

    result = validate(extracted, sys.argv[2])
    print(json.dumps(result, indent=2))
