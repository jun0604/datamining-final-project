def split_text_items(text):
    if not text:
        return []
    for sep in ["/", "，", "\n", "|", ";"]:
        text = str(text).replace(sep, ",")
    return [item.strip() for item in str(text).split(",") if item.strip()]


def unique_list(items):
    return list(dict.fromkeys([x for x in items if x]))


def merge_recommendations(items, trace=None):
    merged = {}
    if trace:
        trace.step("영양소 기준 병합 시작", {
            "입력후보수": len(items or []),
            "입력후보영양소": [item.get("nutrient") for item in items or []],
        })

    for item in items:
        nutrient = item.get("nutrient")
        if not nutrient:
            continue
        if nutrient not in merged:
            merged[nutrient] = {
                "nutrient": nutrient,
                "score": 0,
                "reasons": [],
                "triggers": [],
                "sources": [],
                "nutrient_cautions": [],
                "features": [],
                "managements": [],
                "evidences": [],
                "raw_evidences": [],
                "matched_health_status": [],
                "supplements": [],
                "filter_status": "추천가능",
                "trace_rows": [],
                "score_details": [],
            }
        m = merged[nutrient]
        m["score"] += item.get("score", 0)
        m["reasons"].append(item.get("reason"))
        # trigger는 "입덧, 한 번에 많은 양을 섭취함"처럼 합쳐져 들어올 수 있어 분해 후 중복 제거한다.
        for trig in split_text_items(item.get("trigger")):
            m["triggers"].append(trig)
        m["sources"].append(item.get("source"))
        m["nutrient_cautions"].append(item.get("nutrient_caution"))
        m["features"].append(item.get("feature"))
        m["managements"].append(item.get("management"))
        m["evidences"].append(item.get("evidence"))
        m["raw_evidences"].append(item.get("raw_evidence"))
        m["matched_health_status"].extend(item.get("matched_health_status", []) or [])
        m["trace_rows"].append(item.get("row_index"))
        m["score_details"].append({
            "row_index": item.get("row_index"),
            "trigger": item.get("trigger"),
            "score": item.get("score", 0),
            "score_breakdown": item.get("score_breakdown", []),
            "evidence": item.get("evidence", ""),
            "source_pdf": item.get("source_pdf", ""),
            "source_page": item.get("source_page", ""),
        })

    out = []
    for row in merged.values():
        for key in ["reasons", "triggers", "sources", "nutrient_cautions", "features", "managements", "evidences", "raw_evidences", "matched_health_status", "trace_rows"]:
            row[key] = unique_list(row[key])
        out.append(row)

    out = sorted(out, key=lambda x: x["score"], reverse=True)
    if trace:
        trace.step("영양소 기준 병합 완료", {
            "병합후보수": len(out),
            "병합결과": [
                {
                    "영양소": row.get("nutrient"),
                    "총점": row.get("score"),
                    "트리거": row.get("triggers"),
                    "근거행": row.get("trace_rows"),
                    "근거문장": row.get("evidences"),
                    "주의사항": row.get("nutrient_cautions"),
                }
                for row in out
            ],
        })
    return out


FIXED_PUBLIC_SOURCES = [
    "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리)",
    "국가건강정보포털(질병관리청)_식이영양(임산부)",
    "공공데이터포털(MFDS)_의약품개요정보(e약은요)",
    "공공데이터포털(MFDS)_의약품 제품 허가정보",
    "공공데이터포털(MFDS)_건강기능식품 품목제조 신고사항 현황",
]

FIXED_PUBLIC_SOURCES_TEXT = "\n".join(FIXED_PUBLIC_SOURCES)
FIXED_PUBLIC_SOURCES_HTML = "".join([f"<li>{source}</li>" for source in FIXED_PUBLIC_SOURCES])


def get_fixed_public_sources():
    return FIXED_PUBLIC_SOURCES.copy()


def get_fixed_public_sources_text():
    return FIXED_PUBLIC_SOURCES_TEXT


def get_fixed_public_sources_html():
    return FIXED_PUBLIC_SOURCES_HTML


def force_fixed_references(result):

    if not isinstance(result, dict):
        return result

    fixed = get_fixed_public_sources()
    fixed_text = get_fixed_public_sources_text()
    fixed_html = get_fixed_public_sources_html()

    result["references"] = fixed
    result["references_text"] = fixed_text
    result["reference_sources"] = fixed
    result["fixed_references"] = fixed
    result["fixed_reference_sources"] = fixed
    result["fixed_references_text"] = fixed_text
    result["references_html"] = fixed_html
    result["fixed_references_html"] = fixed_html

    for key in ["recommendations", "excluded_recommendations"]:
        for item in result.get(key, []) or []:
            if isinstance(item, dict):
                item["sources"] = fixed.copy()
                item.pop("source", None)
                item["reference_sources"] = fixed.copy()
                item["references"] = fixed.copy()

    for item in result.get("cautions", []) or []:
        if isinstance(item, dict):
            item["sources"] = fixed.copy()
            item.pop("source", None)
            item["reference_sources"] = fixed.copy()
            item["references"] = fixed.copy()

    return result
