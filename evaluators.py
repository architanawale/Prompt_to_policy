import json

# ------------------------------------------------------------------------------------
# ✅ Helper: Strict JSON Extractor (works for model extra chatter)
# ------------------------------------------------------------------------------------
def extract_json_safely(text: str):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        return json.loads(text[start:end])
    except:
        return None

# ------------------------------------------------------------------------------------
# ✅ Helper: Bracket Integrity (returns % of correctly matched brackets)
# ------------------------------------------------------------------------------------
def bracket_integrity_score(text: str) -> float:
    stack = []
    pairs = {"{": "}", "[": "]", "(": ")"}
    opening = set(pairs.keys())
    closing = set(pairs.values())
    total_brackets = sum(text.count(b) for b in opening.union(closing))
    if total_brackets == 0:
        return 100.0  # no brackets, consider perfect

    for char in text:
        if char in opening:
            stack.append(char)
        elif char in closing:
            if not stack:
                total_brackets += 1  # mismatch
            else:
                last = stack.pop()
                if pairs[last] != char:
                    total_brackets += 1  # mismatch

    unmatched = len(stack)
    correct = max(total_brackets - unmatched, 0)
    return round((correct / total_brackets) * 100, 2)

# ------------------------------------------------------------------------------------
# ✅ Full Model Evaluation Function
# ------------------------------------------------------------------------------------
def evaluate_model_output(model_name, raw_output, response_time):

    evaluation = {
        "Model": model_name,
        "Response Time (s)": round(response_time, 2),
        "JSON Valid": False,
        "Schema Completeness": "Low",
        "Policy Rule Quality": "Poor",
        "Formatting Quality": "Poor",
        "Bracket Integrity Score (%)": 0.0,
        "Failure": False,
    }

    # STEP 1: Try to parse JSON strictly
    parsed_json = extract_json_safely(raw_output)
    evaluation["Bracket Integrity Score (%)"] = bracket_integrity_score(raw_output)

    if parsed_json is None:
        evaluation["Failure"] = True
        return evaluation

    # If parsed successfully
    evaluation["JSON Valid"] = True

    # --------------------------------------------------------------------------------
    # ✅ STEP 2 — Schema Completeness Evaluation
    # --------------------------------------------------------------------------------
    completeness_score = 0

    if "properties" in parsed_json:
        completeness_score += 1

    policy_rule = parsed_json.get("properties", {}).get("policyRule")
    if policy_rule:
        completeness_score += 1

    if isinstance(policy_rule, dict) and "if" in policy_rule:
        completeness_score += 1

    if isinstance(policy_rule, dict):
        effect = policy_rule.get("then", {}).get("effect")
        if effect:
            completeness_score += 1

    # Map score → label
    if completeness_score == 4:
        evaluation["Schema Completeness"] = "High"
    elif completeness_score >= 2:
        evaluation["Schema Completeness"] = "Partial"
    else:
        evaluation["Schema Completeness"] = "Low"

    # --------------------------------------------------------------------------------
    # ✅ STEP 3 — Policy Rule Quality (INTELLIGENT)
    # --------------------------------------------------------------------------------
    try:
        effect = policy_rule.get("then", {}).get("effect")
        conditions = policy_rule.get("if", {})

        valid_effects = {
            "deny",
            "audit",
            "modify",
            "append",
            "deployIfNotExists",
            "disabled",
        }

        if not effect:
            evaluation["Policy Rule Quality"] = "Poor"
        else:
            # Check effect validity
            if effect.lower() not in {e.lower() for e in valid_effects}:
                evaluation["Policy Rule Quality"] = "Average"
            else:
                # Must have meaningful IF conditions
                if isinstance(conditions, dict) and len(conditions) > 0:
                    evaluation["Policy Rule Quality"] = "Excellent"
                else:
                    evaluation["Policy Rule Quality"] = "Good"
    except:
        evaluation["Policy Rule Quality"] = "Poor"

    # --------------------------------------------------------------------------------
    # ✅ STEP 4 — Formatting Quality
    # --------------------------------------------------------------------------------
    raw = raw_output.strip()

    if raw.startswith("{") and raw.endswith("}"):
        evaluation["Formatting Quality"] = "Good"
    elif "{" in raw and "}" in raw:
        evaluation["Formatting Quality"] = "Average"
    else:
        evaluation["Formatting Quality"] = "Poor"

    return evaluation
