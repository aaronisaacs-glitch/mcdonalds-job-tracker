"""
count_jobs.py

PURPOSE:
Fetches the McDonald's job listings feed (JSON) from the internal
jims.thirtythree.co.uk endpoint, counts how many jobs are currently live,
and appends one row (timestamp + counts) to a CSV file.

This script is designed to be run automatically, once per hour, by the
GitHub Actions workflow (job-count.yml) sitting alongside it in this repo.
Each run adds ONE new row to job_counts.csv, which is how the CSV becomes
a growing time series rather than just a snapshot.
"""

# --- Imports -----------------------------------------------------------
# requests: lets Python make an HTTP request (like visiting a URL) and
# get the response back as data we can work with, instead of a browser.
import requests

# csv: Python's built-in tool for reading/writing .csv files row by row,
# handling commas/quoting correctly so we don't have to do it by hand.
import csv

# os: used here just to check "does this file already exist on disk?"
# before deciding whether to write a header row.
import os

# datetime/timezone: used to generate a timestamp for each row, so we
# know exactly when each count was taken. timezone.utc keeps it
# consistent regardless of where the script physically runs.
from datetime import datetime, timezone


# --- Configuration -------------------------------------------------------
# The URL of the live job feed. This is the same URL you'd paste into a
# browser to see the raw JSON list of jobs.
FEED_URL = "https://jims.thirtythree.co.uk/clients/21/sites/41/algolia"

# The name of the CSV file this script writes to. Because no folder path
# is given, it will be created/updated in the same directory the script
# runs from (the root of the repo, when run via GitHub Actions).
OUTPUT_CSV = "job_counts.csv"


def main():
    # --- Step 1: Fetch the data -----------------------------------------
    # Sends a GET request to the feed URL, just like a browser loading a
    # page. timeout=30 means: if there's no response within 30 seconds,
    # give up and raise an error rather than hanging forever.
    resp = requests.get(FEED_URL, timeout=30)

    # If the server responded with an error status (e.g. 404 or 500),
    # this line stops the script immediately with a clear error message,
    # rather than silently continuing with broken/empty data.
    resp.raise_for_status()

    # Converts the raw response text (JSON) into a Python list of
    # dictionaries -- one dictionary per job listing. After this line,
    # "jobs" behaves like a list of job objects we can loop through.
    jobs = resp.json()

    # --- Step 2: Count total live jobs -----------------------------------
    # Loops through every job in the list. job.get("jd_url") looks up the
    # "jd_url" field safely (returns None if it's missing, rather than
    # crashing). The "if job.get('jd_url')" part only counts jobs that
    # actually HAVE a jd_url -- treating that as our definition of "a real,
    # published job listing."
    total_jobs = sum(1 for job in jobs if job.get("jd_url"))

    # --- Step 3: Optional breakdown by contract type ----------------------
    # Builds a running tally of how many jobs fall into each contract_type
    # category (e.g. "Full Time", "Part Time"). Starts as an empty
    # dictionary and grows as we loop through every job.
    by_contract_type = {}
    for job in jobs:
        # job.get("contract_type", "Unknown") looks up the contract_type
        # field, and falls back to the string "Unknown" if that field
        # doesn't exist on this particular job -- avoids crashing on
        # incomplete data.
        ct = job.get("contract_type", "Unknown")

        # This increases the count for that contract type by 1 each time
        # we see it. by_contract_type.get(ct, 0) means "look up the
        # current count for this type, or start at 0 if we haven't seen
        # it before."
        by_contract_type[ct] = by_contract_type.get(ct, 0) + 1

    # --- Step 4: Build the timestamp for this run --------------------------
    # Captures the exact current date/time in UTC, in a standard
    # ISO 8601 format (e.g. 2026-07-09T14:00:03.123456+00:00). This is
    # what lets you later plot job counts against time.
    timestamp = datetime.now(timezone.utc).isoformat()

    # --- Step 5: Write the result into the CSV file -------------------------
    # Checks whether job_counts.csv already exists BEFORE we open it,
    # because we only want to write the header row (column names) the
    # very first time the file is created -- not on every single run.
    file_exists = os.path.isfile(OUTPUT_CSV)

    # Opens the CSV file in "append" mode ("a"), meaning new data is
    # added to the end of the file without erasing what's already there.
    # newline="" avoids extra blank lines being inserted on some systems.
    with open(OUTPUT_CSV, "a", newline="") as f:
        # Wraps the file so we can write rows as simple Python lists,
        # and csv.writer takes care of formatting/commas correctly.
        writer = csv.writer(f)

        # Only runs the very first time this script is ever executed
        # against a fresh repo (when the CSV doesn't exist yet) -- writes
        # the column headers as the first row of the file.
        if not file_exists:
            writer.writerow(["timestamp_utc", "total_jobs", "full_time", "part_time"])

        # Writes the actual data row for this run: when it ran, the total
        # job count, and the full-time/part-time breakdown. .get(..., 0)
        # defaults to 0 if that contract type had zero matches this run.
        writer.writerow([
            timestamp,
            total_jobs,
            by_contract_type.get("Full Time", 0),
            by_contract_type.get("Part Time", 0),
        ])

    # --- Step 6: Print a confirmation line ---------------------------------
    # This text shows up in the GitHub Actions run log, so you can open
    # any past run and see at a glance what it counted, without needing
    # to open the CSV itself.
    print(f"{timestamp}: {total_jobs} jobs logged.")


# --- Entry point ---------------------------------------------------------
# This is a standard Python pattern: it means "only run main() if this
# file is being executed directly (e.g. `python count_jobs.py`)", rather
# than if it were imported by some other script. For our purposes here,
# it just means: run the function above when this file is run.
if __name__ == "__main__":
    main()
