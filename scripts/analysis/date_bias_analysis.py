from pathlib import Path
import argparse
import sqlite3
import pandas as pd
import numpy as np
import re
import wave, contextlib
from datetime import timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

FILENAME_REGEX = re.compile(
    r'(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})_(?P<hh>\d{2})(?P<mi>\d{2})\.wav$',
    re.IGNORECASE
)

DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def detect_year(yy: int) -> int:
    return 2000 + yy  # bias to modern field recordings

def wav_duration_seconds(path: Path) -> float | None:
    try:
        with contextlib.closing(wave.open(str(path), 'rb')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return None
            return frames / float(rate)
    except Exception:
        return None

def parse_wav_start(p: Path):
    m = FILENAME_REGEX.search(p.name)
    if not m:
        return None
    yy, mm, dd, hh, mi = map(int, m.groups())
    yyyy = detect_year(yy)
    try:
        return pd.Timestamp(year=yyyy, month=mm, day=dd, hour=hh, minute=mi)
    except Exception:
        return None

def load_fs_intervals(root: Path, tzname: str | None) -> pd.DataFrame:
    rows = []
    for p in root.rglob("*.wav"):
        dt_start = parse_wav_start(p)
        note = "filename"
        if dt_start is None:
            dt_start = pd.Timestamp(p.stat().st_mtime, unit='s', tz="UTC")
            note = "mtime(UTC)"
        if tzname and ZoneInfo:
            tz = ZoneInfo(tzname)
            if dt_start.tzinfo is None:
                dt_start = dt_start.tz_localize(tz)
            else:
                dt_start = dt_start.tz_convert(tz)
        dur_s = wav_duration_seconds(p)
        if dur_s is None:
            # if unreadable, treat as zero-length (skip)
            continue
        dt_end = dt_start + pd.to_timedelta(dur_s, unit='s')
        rows.append({
            "source": "file",
            "id_or_path": str(p),
            "start": dt_start,
            "end": dt_end,
            "infer_note": note,
            "duration_seconds": dur_s
        })
    return pd.DataFrame(rows)

def load_db_intervals(sqlite_path: Path, table: str, from_col: str, to_col: str, tzname: str | None) -> pd.DataFrame:
    conn = sqlite3.connect(str(sqlite_path))
    try:
        q = f"SELECT {from_col} as start, {to_col} as end, rowid as row_id FROM {table}"
        df = pd.read_sql_query(q, conn, parse_dates=['start','end'])
    finally:
        conn.close()

    if df.empty:
        return df.assign(source="db", id_or_path=np.nan, infer_note="db", duration_seconds=np.nan)

    # Coerce to timezone consistently (series-wide)
    if tzname and ZoneInfo:
        tz = ZoneInfo(tzname)
        s = pd.to_datetime(df['start'], errors='coerce')
        e = pd.to_datetime(df['end'],   errors='coerce')
        if s.dt.tz is None:
            s = s.dt.tz_localize(tz)
        else:
            s = s.dt.tz_convert(tz)
        if e.dt.tz is None:
            e = e.dt.tz_localize(tz)
        else:
            e = e.dt.tz_convert(tz)
        df['start'], df['end'] = s, e

    df = df.rename(columns={"row_id":"db_row_id"})
    df['source'] = "db"
    df['id_or_path'] = df['db_row_id'].astype(str)
    df['infer_note'] = "db"
    df['duration_seconds'] = (df['end'] - df['start']).dt.total_seconds()
    return df

def tidy_intervals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out = out[~out['start'].isna() & ~out['end'].isna()].copy()
    out = out[out['end'] > out['start']].copy()
    return out

def clamp_window(df: pd.DataFrame, since: str | None, until: str | None, tzname: str | None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if since:
        s = pd.to_datetime(since)
        if tzname and ZoneInfo:
            s = s.tz_localize(ZoneInfo(tzname))
        out['start'] = out['start'].where(out['start'] >= s, s)
    if until:
        u = pd.to_datetime(until)
        if tzname and ZoneInfo:
            u = u.tz_localize(ZoneInfo(tzname))
        out['end'] = out['end'].where(out['end'] <= u, u)
    out = out[out['end'] > out['start']]
    return out

# ---------- TZ utilities to avoid naive/aware comparisons ----------

def coerce_series_to_tz(series: pd.Series, tzname: str) -> pd.Series:
    """Make the entire datetime series tz-aware in the given tz (localize if naive, convert if aware)."""
    if ZoneInfo is None:
        return pd.to_datetime(series, errors='coerce')
    tz = ZoneInfo(tzname)
    s = pd.to_datetime(series, errors='coerce')
    if s.dt.tz is None:
        return s.dt.tz_localize(tz)
    else:
        return s.dt.tz_convert(tz)

def month_start(dt: pd.Timestamp) -> pd.Timestamp:
    """First of month at 00:00 in the SAME tz as dt."""
    return pd.Timestamp(dt.year, dt.month, 1, tz=dt.tz)

def next_month(dt: pd.Timestamp) -> pd.Timestamp:
    """Next month start, preserving tz."""
    y, m = dt.year, dt.month
    if m == 12:
        return pd.Timestamp(y + 1, 1, 1, tz=dt.tz)
    else:
        return pd.Timestamp(y, m + 1, 1, tz=dt.tz)

# ---------- Coverage helpers (interval → buckets with overlapped seconds) ----------

def iter_hour_boundaries(start: pd.Timestamp, end: pd.Timestamp):
    """Yield (bin_start, bin_end) for each hour bin overlapped."""
    cur = start.floor('H')  # preserves tz for tz-aware timestamps
    while cur < end:
        nxt = cur + pd.Timedelta(hours=1)
        yield cur, min(nxt, end)
        cur = nxt

def iter_day_boundaries(start: pd.Timestamp, end: pd.Timestamp):
    cur = start.normalize()  # preserves tz
    while cur < end:
        nxt = cur + pd.Timedelta(days=1)
        yield cur, min(nxt, end)
        cur = nxt

def coverage_buckets(intervals: pd.DataFrame):
    """Return three DataFrames with total overlapped seconds and interval counts per bucket."""
    # Hours of day (0..23)
    hour_sec = {h: 0.0 for h in range(24)}
    hour_cnt = {h: 0   for h in range(24)}
    # Weekday
    dow_sec  = {d: 0.0 for d in DOW_ORDER}
    dow_cnt  = {d: 0   for d in DOW_ORDER}
    # Month
    month_sec = {}
    month_cnt = {}

    for _, r in intervals.iterrows():
        s = r['start']; e = r['end']

        # Hours of day
        seen_hours = set()
        for hb_s, hb_e in iter_hour_boundaries(s, e):
            h = int(hb_s.hour)
            overlap = (hb_e - hb_s).total_seconds()
            hour_sec[h] += overlap
            seen_hours.add(h)
        for h in seen_hours:
            hour_cnt[h] += 1

        # Day-of-week
        seen_dow = set()
        for db_s, db_e in iter_day_boundaries(s, e):
            overlap = (db_e - db_s).total_seconds()
            dname = db_s.day_name()
            if dname not in dow_sec:
                dow_sec[dname] = 0.0
                dow_cnt[dname] = 0
            dow_sec[dname] += overlap
            seen_dow.add(dname)
        for d in seen_dow:
            dow_cnt[d] += 1

        # Month (tz-aware month boundaries)
        seen_months = set()
        cur = month_start(s)
        if cur > s:
            # move back to previous month start if somehow ahead
            prev = s - pd.Timedelta(days=1)
            cur = month_start(prev)
        while cur < e:
            nxt = next_month(cur)
            ms = cur
            me = min(nxt, e)
            overlap = (me - max(ms, s)).total_seconds()
            mkey = ms  # first day of the month at 00:00 in local tz
            month_sec[mkey] = month_sec.get(mkey, 0.0) + overlap
            seen_months.add(mkey)
            cur = nxt
        for m in seen_months:
            month_cnt[m] = month_cnt.get(m, 0) + 1

    # Build frames
    by_hour = pd.DataFrame({
        "hour": list(range(24)),
        "covered_seconds": [hour_sec[h] for h in range(24)],
        "intervals_overlapped": [hour_cnt[h] for h in range(24)],
    })
    by_hour["covered_hours"] = by_hour["covered_seconds"] / 3600.0

    by_dow = pd.DataFrame({
        "dow": DOW_ORDER,
        "covered_seconds": [dow_sec[d] for d in DOW_ORDER],
        "intervals_overlapped": [dow_cnt[d] for d in DOW_ORDER],
    })
    by_dow["covered_hours"] = by_dow["covered_seconds"] / 3600.0

    if month_sec:
        months_sorted = sorted(month_sec.keys())
        by_month = pd.DataFrame({
            "month": months_sorted,
            "covered_seconds": [month_sec[m] for m in months_sorted],
            "intervals_overlapped": [month_cnt.get(m, 0) for m in months_sorted],
        })
        by_month["covered_hours"] = by_month["covered_seconds"] / 3600.0
    else:
        by_month = pd.DataFrame(columns=["month","covered_seconds","intervals_overlapped","covered_hours"])

    return {"by_month": by_month, "by_dow": by_dow, "by_hour": by_hour}

def contiguous_ranges(nums: list[int]) -> list[tuple[int,int]]:
    if not nums:
        return []
    nums = sorted(nums)
    out = []
    a = b = nums[0]
    for x in nums[1:]:
        if x == b + 1:
            b = x
        else:
            out.append((a, b))
            a = b = x
    out.append((a, b))
    return out

def analyze(buckets: dict, min_month_hours: float, min_dow_hours: float, min_hour_hours: float) -> list[str]:
    notes = []
    # Month
    bm = buckets["by_month"]
    if not bm.empty:
        zero_m = bm[bm["covered_seconds"] <= 0]
        low_m  = bm[bm["covered_hours"] < min_month_hours]
        if not zero_m.empty:
            notes.append("Months with ZERO coverage: " + ", ".join(m.strftime("%Y-%m") for m in zero_m["month"]))
        if not low_m.empty:
            notes.append("Months below threshold ({:.2f}h): ".format(min_month_hours) +
                         ", ".join(f"{m.strftime('%Y-%m')}={h:.2f}h" for m,h in zip(low_m["month"], low_m["covered_hours"])))

    # Weekday
    bd = buckets["by_dow"]
    zero_d = bd[bd["covered_seconds"] <= 0]["dow"].tolist()
    low_d  = bd[bd["covered_hours"] < min_dow_hours]
    if zero_d:
        notes.append("Weekdays with ZERO coverage: " + ", ".join(zero_d))
    if not low_d.empty:
        notes.append("Weekdays below threshold ({:.2f}h): ".format(min_dow_hours) +
                     ", ".join(f"{d}={h:.2f}h" for d,h in zip(low_d["dow"], low_d["covered_hours"])))

    # Hour-of-day
    bh = buckets["by_hour"]
    zero_h = bh[bh["covered_seconds"] <= 0]["hour"].astype(int).tolist()
    low_h  = bh[bh["covered_hours"] < min_hour_hours]["hour"].astype(int).tolist()
    if zero_h:
        spans = contiguous_ranges(zero_h)
        pretty = ", ".join(f"{a}-{b}" if a!=b else f"{a}" for a,b in spans)
        notes.append(f"Hours with ZERO coverage: {pretty}")
    if low_h:
        spans = contiguous_ranges(low_h)
        pretty = ", ".join(f"{a}-{b}" if a!=b else f"{a}" for a,b in spans)
        notes.append(f"Hours below threshold ({min_hour_hours:.2f}h): {pretty}")

    return notes

def main():
    p = argparse.ArgumentParser(description="Interval-based coverage over months, weekdays, and hours (DB + WAVs).")
    # hard-coded defaults (Windows-friendly root)
    p.add_argument("--sqlite", type=Path, default=Path("./db/chorusAvery.db"))
    p.add_argument("--table", default="SourceFiles")
    p.add_argument("--from-col", default="From_Date")
    p.add_argument("--to-col", default="To_Date")
    p.add_argument("--root", type=Path, default=Path(r"E:\\"))  # use r"E:\\" as a safe default on Windows
    p.add_argument("--tz", default="America/Chicago")
    p.add_argument("--since", default="2024-01-01")
    p.add_argument("--until", default="2025-12-31")
    p.add_argument("--min-month-hours", type=float, default=1.0)
    p.add_argument("--min-dow-hours", type=float, default=0.5)
    p.add_argument("--min-hour-hours", type=float, default=0.25)
    p.add_argument("--export-prefix", type=Path, default=Path("chorus_avery_interval_coverage"))
    args = p.parse_args()   # no flags required anymore

    frames = []
    if args.sqlite:
        frames.append(load_db_intervals(args.sqlite, args.table, args.from_col, args.to_col, args.tz))
    if args.root:
        frames.append(load_fs_intervals(args.root, args.tz))
    if not frames:
        print("Nothing to analyze. Provide --sqlite and/or --root.")
        return

    intervals = tidy_intervals(pd.concat(frames, ignore_index=True))

    # Ensure BOTH columns are tz-aware in the target timezone before any comparisons/bucketing
    if ZoneInfo is not None:
        intervals['start'] = coerce_series_to_tz(intervals['start'], args.tz)
        intervals['end']   = coerce_series_to_tz(intervals['end'],   args.tz)
    else:
        intervals['start'] = pd.to_datetime(intervals['start'], errors='coerce')
        intervals['end']   = pd.to_datetime(intervals['end'],   errors='coerce')

    # Clamp analysis window (also tz-aware)
    intervals = clamp_window(intervals, args.since, args.until, args.tz)
    if intervals.empty:
        print("No intervals after clamping.")
        return

    buckets = coverage_buckets(intervals)
    notes = analyze(buckets, args.min_month_hours, args.min_dow_hours, args.min_hour_hours)

    # Export CSVs
    prefix = args.export_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    by_month_path = Path(str(prefix) + "_by_month.csv")
    by_dow_path   = Path(str(prefix) + "_by_dow.csv")
    by_hour_path  = Path(str(prefix) + "_by_hour.csv")
    buckets["by_month"].to_csv(by_month_path, index=False)
    buckets["by_dow"].to_csv(by_dow_path, index=False)
    buckets["by_hour"].to_csv(by_hour_path, index=False)

    # Console summary
    print("\n==== Chorus Avery Interval Coverage ====")
    print(f"Intervals analyzed: {len(intervals)}  (window: {intervals['start'].min()} .. {intervals['end'].max()})")
    print("\nBy month (covered hours, top & tail):")
    bm = buckets["by_month"].copy()
    if not bm.empty:
        bm["covered_hours"] = bm["covered_seconds"]/3600.0
        print(pd.concat([bm.head(3), bm.tail(3)]).to_string(index=False))
    print("\nBy weekday:")
    bd = buckets["by_dow"].copy()
    bd["covered_hours"] = bd["covered_seconds"]/3600.0
    print(bd.to_string(index=False))
    print("\nBy hour:")
    bh = buckets["by_hour"].copy()
    bh["covered_hours"] = bh["covered_seconds"]/3600.0
    print(bh.to_string(index=False))

    print("\n--- Notable ---")
    if notes:
        for n in notes:
            print("* " + n)
    else:
        print("No notable distribution gaps found.")

    print("\nCSV exports:")
    print(f"- By month: {by_month_path}")
    print(f"- By weekday: {by_dow_path}")
    print(f"- By hour: {by_hour_path}")

if __name__ == "__main__":
    main()
