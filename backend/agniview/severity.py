def severity(frp: float | None, dnbr: float | None, confidence: float) -> tuple[float, str]:
    # ponytail: heuristic score, replace with regional calibration when labeled outcomes exist.
    frp_score = min(max(frp or 0, 0) / 100, 1) * 55
    burn_score = min(max(dnbr or 0, 0) / 0.66, 1) * 35
    score = round((frp_score + burn_score) * (0.7 + 0.3 * min(max(confidence, 0), 1)), 1)
    label = "high" if score >= 70 else "medium" if score >= 35 else "low"
    return score, label
