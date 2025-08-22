import datetime

def init_srs_record(question_id):
    return {
        "id": question_id,
        "interval": 1,
        "ease_factor": 2.5,
        "next_review": datetime.date.today() + datetime.timedelta(days=1),
        "repetitions": 0
    }

def update_srs_record(record, correct):
    if not correct:
        record["interval"] = 1
        record["ease_factor"] = max(1.3, record["ease_factor"] - 0.2)
        record["repetitions"] = 0
    else:
        record["repetitions"] += 1
        record["ease_factor"] += 0.1
        record["interval"] = int(record["interval"] * record["ease_factor"])
    
    record["next_review"] = datetime.date.today() + datetime.timedelta(days=record["interval"])
    return record
