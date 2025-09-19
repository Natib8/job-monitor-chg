import hashlib

def unique_key(row):
    url = (row.get("job_url") or "").strip().lower()
    if url:
        return f"url::{url}"
    s = f"{(row.get('company') or '').strip().lower()}|{(row.get('job_title') or '').strip().lower()}|{(row.get('pub_date') or '').strip()}"
    return "hash::" + hashlib.sha1(s.encode("utf-8")).hexdigest()
