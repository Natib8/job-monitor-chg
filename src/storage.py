import os
import pandas as pd
from datetime import datetime
from normalize import unique_key

MASTER_PATH = "data/job_offers_master.csv"

COLUMNS = ["company","company_website","industry","job_title","pub_date","job_url","source"]

def ensure_dirs():
    os.makedirs("data", exist_ok=True)

def load_master():
    if os.path.exists(MASTER_PATH):
        df = pd.read_csv(MASTER_PATH)
        # sanity: kolumny
        for c in COLUMNS:
            if c not in df.columns:
                df[c] = ""
        return df[COLUMNS]
    return pd.DataFrame(columns=COLUMNS)

def append_new(master_df, new_rows):
    import pandas as pd
    if not new_rows:
        return master_df, pd.DataFrame(columns=COLUMNS)
    new_df = pd.DataFrame(new_rows)[COLUMNS]
    # dedup vs. master
    master_keys = set(master_df.apply(lambda r: unique_key(r), axis=1))
    mask = ~new_df.apply(lambda r: unique_key(r) in master_keys, axis=1)
    new_unique = new_df[mask].copy()
    updated = pd.concat([master_df, new_unique], ignore_index=True)
    # dedup wewnętrzny po URL
    updated = updated.drop_duplicates(subset=["job_url"], keep="first")
    # sortowanie (opcjonalnie po dacie malejąco)
    try:
        updated["pub_date"] = pd.to_datetime(updated["pub_date"], errors="coerce").dt.date.astype(str)
    except Exception:
        pass
    return updated, new_unique

def save_master(df):
    df.to_csv(MASTER_PATH, index=False)

def save_daily(new_df):
    if new_df.empty:
        return None
    day = datetime.utcnow().strftime("%Y%m%d")
    path = f"data/new_offers_{day}.csv"
    new_df.to_csv(path, index=False)
    return path
