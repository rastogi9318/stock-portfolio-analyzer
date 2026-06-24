import re
import time

import requests
from bs4 import BeautifulSoup

from cache_store import METRIC_COLUMNS, get_cached_metrics, save_metrics


SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
)


def _parse_number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("%", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def _row_numbers(cells) -> list[float]:
    return [
        parsed
        for cell in cells
        if (parsed := _parse_number(cell.get_text())) is not None
    ]


def _empty_metrics() -> dict:
    return {column: None for column in METRIC_COLUMNS}


def _latest_row_value(section, labels: list[str]) -> float | None:
    if section is None:
        return None

    label_tokens = [label.lower() for label in labels]
    for row in section.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        label = cells[0].get_text(" ", strip=True).lower()
        if not any(token in label for token in label_tokens):
            continue

        values = _row_numbers(cells[1:])
        if values:
            return values[-1]
    return None


def _row_change_pct(section, labels: list[str]) -> float | None:
    if section is None:
        return None

    label_tokens = [label.lower() for label in labels]
    for row in section.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        label = cells[0].get_text(" ", strip=True).lower()
        if not any(token in label for token in label_tokens):
            continue

        values = _row_numbers(cells[1:])
        if len(values) >= 2 and values[-2] != 0:
            return (values[-1] - values[-2]) / abs(values[-2]) * 100
    return None


def _metric_from_label(soup: BeautifulSoup, labels: list[str]) -> float | None:
    label_tokens = [label.lower() for label in labels]

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True).lower()
        if any(token in label for token in label_tokens):
            values = _row_numbers(cells[1:])
            if values:
                return values[-1]

    for item in soup.find_all(["li", "div"]):
        text = item.get_text(" ", strip=True)
        normalized = text.lower()
        if not any(token in normalized for token in label_tokens):
            continue

        name = item.find(class_="name")
        number = item.find(class_="number") or item.find(class_="value")
        if name and number:
            name_text = name.get_text(" ", strip=True).lower()
            if any(token in name_text for token in label_tokens):
                return _parse_number(number.get_text(" ", strip=True))

        values = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
        if values:
            return float(values[-1])
    return None


def _extract_numeric_from_element(element) -> float | None:
    if element is None:
        return None
    text = element.get_text(" ", strip=True)
    return _parse_number(text)


def _find_label_value(soup: BeautifulSoup, labels: list[str]) -> float | None:
    label_re = re.compile(r"\b(" + "|".join(re.escape(label) for label in labels) + r")\b", flags=re.I)
    for text_node in soup.find_all(string=label_re):
        parent = text_node.parent
        if parent is None:
            continue

        # Prefer the full parent block if it contains both label and a numeric value
        numeric = _find_numeric_in_block(parent)
        if numeric is not None:
            return numeric

        # Try sibling nodes when label and value are separated
        for sibling in parent.find_next_siblings():
            numeric = _extract_numeric_from_element(sibling)
            if numeric is not None:
                return numeric

        if parent.parent is not None:
            numeric = _find_numeric_in_block(parent.parent)
            if numeric is not None:
                return numeric
    return None


def _find_numeric_in_block(element) -> float | None:
    text = element.get_text(" ", strip=True)
    if not text:
        return None
    values = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not values:
        return None
    return float(values[-1])


def _extract_closing_price(soup: BeautifulSoup) -> float | None:
    # Search for the explicit current/close price label first
    for labels in [
        ["current price"],
        ["close price", "closing price", "close"],
        ["last price", "ltp"],
    ]:
        value = _find_label_value(soup, labels)
        if value is not None and value > 0:
            return value

    # Try structured metadata first
    tag = soup.find(attrs={"itemprop": "price"})
    if tag:
        parsed = _parse_number(tag.get_text(" ", strip=True))
        if parsed is not None and parsed > 0:
            return parsed

    # As a fallback, look for the first strong price-like value in the summary page
    candidates = []
    for node in soup.find_all(text=re.compile(r"\b(?:₹|rs\.?|\d{3,})\b", flags=re.I)):
        parent = node.parent
        if parent is None:
            continue
        numeric = _find_numeric_in_block(parent)
        if numeric is not None and numeric > 0:
            candidates.append(numeric)
    return candidates[0] if candidates else None


def scrape_metrics(symbol: str) -> dict:
    return scrape_metrics_details(symbol)["metrics"]


def scrape_metrics_details(symbol: str, use_cache: bool = True) -> dict:
    if use_cache:
        cached = get_cached_metrics(symbol)
        if cached is not None:
            return cached

    metrics = _empty_metrics()

    try:
        resp = SESSION.get(f"https://www.screener.in/company/{symbol}/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        time.sleep(1)

        quarters_table = soup.find("section", {"id": "quarters"})
        if quarters_table:
            for row in quarters_table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if cells and "net profit" in cells[0].get_text(strip=True).lower():
                    values = _row_numbers(cells[1:])
                    if len(values) >= 2:
                        prev, latest = values[-2], values[-1]
                        if prev != 0:
                            metrics["qoq_profit_change_pct"] = (
                                (latest - prev) / abs(prev) * 100
                            )

        shareholding = soup.find("section", {"id": "shareholding"})
        if shareholding:
            metrics["promoter_holding_pct"] = _latest_row_value(
                shareholding, ["promoters", "promoter"]
            )
            metrics["pledged_shares_pct"] = _latest_row_value(
                shareholding, ["pledged"]
            )

            for row in shareholding.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue

                label = cells[0].get_text(strip=True).lower()
                values = _row_numbers(cells[1:])
                if len(values) < 2:
                    continue

                change = values[-1] - values[-2]
                if "fii" in label or "foreign" in label:
                    metrics["fii_change_pct"] = change
                elif "dii" in label or "domestic" in label:
                    metrics["dii_change_pct"] = change

        profit_loss = soup.find("section", {"id": "profit-loss"})
        metrics["sales_growth_pct"] = _row_change_pct(
            profit_loss, ["sales", "revenue"]
        )

        ratios = soup.find("section", {"id": "ratios"})
        if ratios:
            for row in ratios.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue

                label = cells[0].get_text(strip=True).lower()
                vals = _row_numbers(cells[1:])
                if len(vals) < 2:
                    continue

                change = vals[-1] - vals[-2]
                if "roce" in label:
                    metrics["roce_change"] = change
                elif "roe" in label:
                    metrics["roe_change"] = change

        # Also extract absolute ROCE / ROE values when present elsewhere on the page
        metrics["roce"] = _metric_from_label(soup, ["roce", "return on capital employed"]) 
        metrics["roe"] = _metric_from_label(soup, ["roe", "return on equity"]) 

        metrics["debt_to_equity"] = _metric_from_label(
            soup, ["debt to equity", "debt/equity", "debt equity"]
        )
        metrics["pe_ratio"] = _metric_from_label(
            soup, ["stock p/e", "price to earning", "p/e"]
        )
        metrics["industry_pe"] = _metric_from_label(
            soup, ["industry p/e", "industry pe"]
        )

        # Try to extract the latest market close/last traded price
        metrics["closing_price"] = _extract_closing_price(soup)

        missing_count = sum(metrics.get(column) is None for column in METRIC_COLUMNS)
        if missing_count == len(METRIC_COLUMNS):
            status = "parse_failed"
            error_message = "Screener page loaded, but no target metrics were found"
        elif missing_count:
            status = "partial"
            error_message = f"{missing_count} metric(s) unavailable"
        else:
            status = "ok"
            error_message = None

        save_metrics(symbol, metrics, status, error_message)
        return {
            "metrics": metrics,
            "status": status,
            "error_message": error_message,
            "from_cache": False,
        }
    except Exception as exc:
        error_message = str(exc)
        save_metrics(symbol, metrics, "error", error_message)
        return {
            "metrics": metrics,
            "status": "error",
            "error_message": error_message,
            "from_cache": False,
        }
