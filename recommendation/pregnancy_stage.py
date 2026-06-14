def get_pregnancy_stage(week):
    week = int(week)
    if 1 <= week <= 13:
        return {"week": week, "week_start": 1, "week_end": 13, "stage_name": "초기", "precautions": []}
    if 14 <= week <= 27:
        return {"week": week, "week_start": 14, "week_end": 27, "stage_name": "중기", "precautions": []}
    if 28 <= week <= 42:
        return {"week": week, "week_start": 28, "week_end": 42, "stage_name": "후기", "precautions": []}
    return {"week": week, "week_start": None, "week_end": None, "stage_name": "단계 정보 없음", "precautions": []}
