def score_stock_explained(metrics: dict) -> tuple[int, str, str]:
    rules = [
        _rule("QoQ profit improved", metrics.get("qoq_profit_change_pct"), _positive),
        _rule("FII holding increased", metrics.get("fii_change_pct"), _positive),
        _rule("DII holding increased", metrics.get("dii_change_pct"), _positive),
        _rule("ROCE improved", metrics.get("roce_change"), _positive),
        _rule("ROE improved", metrics.get("roe_change"), _positive),
        _rule("Sales grew", metrics.get("sales_growth_pct"), _positive),
        _rule(
            "Promoter holding >= 40%",
            metrics.get("promoter_holding_pct"),
            lambda value: _at_least(value, 40),
        ),
        _rule(
            "Pledged shares <= 5%",
            metrics.get("pledged_shares_pct"),
            lambda value: _at_most(value, 5),
        ),
        _rule(
            "Debt/equity <= 1.5",
            metrics.get("debt_to_equity"),
            lambda value: _at_most(value, 1.5),
        ),
        _rule(
            "PE <= industry PE",
            (metrics.get("pe_ratio"), metrics.get("industry_pe")),
            _pe_reasonable_pair,
        ),
    ]
    valid = [rule for rule in rules if rule["passed"] is not None]
    if len(valid) < 4:
        return 0, "N/A", "Not enough usable metrics for a reliable recommendation."

    passed = [rule["label"] for rule in valid if rule["passed"]]
    failed = [rule["label"] for rule in valid if not rule["passed"]]
    scaled = round(len(passed) / len(valid) * 5)

    if scaled >= 4:
        recommendation = "BUY"
    elif scaled >= 2:
        recommendation = "HOLD"
    else:
        recommendation = "SELL"

    explanation_parts = []
    if passed:
        explanation_parts.append("Positive: " + "; ".join(passed[:4]))
    if failed:
        explanation_parts.append("Watch: " + "; ".join(failed[:4]))
    explanation_parts.append(f"{len(passed)}/{len(valid)} signals passed.")
    return scaled, recommendation, " | ".join(explanation_parts)


def score_stock(metrics: dict) -> tuple[int, str]:
    score, recommendation, _ = score_stock_explained(metrics)
    return score, recommendation


def _rule(label: str, value, evaluator) -> dict:
    return {"label": label, "passed": evaluator(value)}


def _positive(value: float | None) -> bool | None:
    if value is None:
        return None
    return value > 0


def _at_least(value: float | None, threshold: float) -> bool | None:
    if value is None:
        return None
    return value >= threshold


def _at_most(value: float | None, threshold: float) -> bool | None:
    if value is None:
        return None
    return value <= threshold


def _pe_reasonable(pe_ratio: float | None, industry_pe: float | None) -> bool | None:
    if pe_ratio is None or industry_pe is None or industry_pe <= 0:
        return None
    return pe_ratio <= industry_pe


def _pe_reasonable_pair(values: tuple[float | None, float | None]) -> bool | None:
    pe_ratio, industry_pe = values
    return _pe_reasonable(pe_ratio, industry_pe)
