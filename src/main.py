import os
import pandas as pd
from scraper import scrape_all
from storage import ensure_dirs, load_master, append_new, save_master, save_daily

RAW_MASTER_LINK = os.environ.get("RAW_MASTER_LINK", "https://raw.githubusercontent.com/<OWNER>/<REPO>/main/data/job_offers_master.csv")
MAX_IN_BODY = int(os.environ.get("MAX_IN_BODY", "50"))

def format_new_list(df):
    if df.empty:
        return "Brak nowych ofert dziś."
    lines = []
    for i, r in df.head(MAX_IN_BODY).iterrows():
        line = f"- {r['job_title']} — {r['company']} — {r['source']} — {r['pub_date']} — {r['job_url']}"
        lines.append(line)
    if len(df) > MAX_IN_BODY:
        lines.append(f"... + {len(df) - MAX_IN_BODY} kolejnych")
    return "\n".join(lines)

def main():
    ensure_dirs()
    master = load_master()
    scraped = scrape_all()
    updated, new_unique = append_new(master, scraped)
    save_master(updated)
    daily_path = save_daily(new_unique)

    # wygeneruj body e-maila do pliku (użyje go action-send-mail)
    with open("email_body.txt", "w", encoding="utf-8") as f:
        # wczytaj szablon
        with open(os.path.join("src","email_body_template.txt"), "r", encoding="utf-8") as t:
            tpl = t.read()
        body = tpl.replace("{{NEW_LIST}}", format_new_list(new_unique)) \
                  .replace("{{MASTER_LINK}}", RAW_MASTER_LINK)
        f.write(body)

    # Zapisz krótkie podsumowanie na STDOUT (przydatne w logach)
    print(f"[INFO] Scraped: {len(scraped)} | New unique: {len(new_unique)} | Master size: {len(updated)}")
    if daily_path:
        print(f"[INFO] New offers file: {daily_path}")
    else:
        print("[INFO] No new offers today.")

if __name__ == "__main__":
    main()
