#!/usr/bin/env python3
"""Write data/README.md (the card), data/LICENSE and data/provenance.yaml of the prefectures placed so far.

    uv run python scripts/11_card.py

Every count in the card is read from docs/profile_<pref>.json (08_profile.py) and from data/parquet/tables.json.
"""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NAMES = {40: "茨城県", 41: "栃木県", 42: "群馬県", 43: "埼玉県", 44: "東京都", 45: "千葉県", 46: "神奈川県"}
ROMA = {40: "Ibaraki", 41: "Tochigi", 42: "Gunma", 43: "Saitama", 44: "Tokyo", 45: "Chiba", 46: "Kanagawa"}


def main() -> int:
    tables = json.loads((DATA / "parquet" / "tables.json").read_text())
    prefs = sorted(int(k.split("=")[1]) for k in tables["daily"])
    prof = {p: json.loads((ROOT / "docs" / f"profile_{p}.json").read_text()) for p in prefs}
    st = duckdb.sql(
        f"select station_id, station_name, pref, kind from read_parquet('{DATA}/parquet/stations.parquet') order by 1"
    ).fetchall()
    name = {r[0]: r[1] for r in st}
    nd = sum(tables["daily"].values())
    nh = sum(tables["hourly"].values())
    rows, issues = [], []
    for p in prefs:
        d, s = prof[p], [r for r in st if r[2] == p]
        ns = len(s)
        nsyn = sum(r[3] == "synop" for r in s)
        rows.append(f"| {p} | {NAMES[p]} | {ns} ({nsyn} + {ns - nsyn}) | {d['rows']['daily']:,} | {d['rows']['hourly']:,} |")
        per, h = d["per_station_daily"], d["hourly"]
        ended = [f"{name[i]} ({i}, {v['last']})" for i, v in per.items() if v["last"] < "2026-09-30"]
        late = [f"{name[i]} ({i}, {v['first']})" for i, v in per.items() if v["first"] > "1980-01-01"]
        gaps = sorted(((v["missing_days_in_span"], i) for i, v in per.items() if v["missing_days_in_span"] >= 100), reverse=True)
        homog = [
            f"{name[i]} ({i}): " + ", ".join(f"{x['number']} from {x['from']}" for x in v["homog"][1:])
            for i, v in per.items()
            if len(v["homog"]) > 1
        ]
        sd = h["sum_differs_by_station"]
        z = d["synop_zero_days"]
        lines = [
            f"### {NAMES[p]} ({p})",
            "",
            f"- Stations that ended: {', '.join(ended) if ended else 'none'}. Stations whose first value is after 1980: {', '.join(late) if late else 'none'}.",
            f"- Missing days between the first and the last value, stations with 100 or more: "
            f"{', '.join(f'{name[i]} ({i}) {n:,}' for n, i in gaps) if gaps else 'none'}.",
            f"- Homogeneity number changes: {'; '.join(homog) if homog else 'none'}.",
            f"- A 0 of a weather station: no rain (`nophen` 1) {z['nophen_1_no_rain']:,} days, rain that came to 0.0 mm (`nophen` 0) {z['nophen_0_with_0_mm']:,} days.",
            f"- Hourly: {h['null_values']:,} null values; {h['days_24_hours_daily_null']:,} station-days have 24 hourly values while the daily total is null; "
            f"{h['days_with_1_to_23_hours']} days have 1 to 23 hourly values. Of {h['compared_days']:,} days with 24 hourly values and a daily value, the hours add up to the daily total on "
            f"{h['compared_days'] - h['sum_differs']:,}; "
            + (
                "the other " + str(h["sum_differs"]) + " are at "
                + ", ".join(f"{name[i]} ({i}): {v[0]} days, by {v[1]} to {v[2]} mm" for i, v in sd.items())
                if sd
                else "none differ"
            )
            + f". The daily greatest 1 hour amount is larger than the greatest hourly amount of the day on {h['max1h_daily_larger']:,} days and smaller on {h['max1h_daily_smaller']}.",
            "",
        ]
        if d["shared_names"]:
            lines.insert(-1, f"- Names used by two stations: {d['shared_names']}.")
        issues += lines
    pref_list = ", ".join(f"{NAMES[p]} ({p})" for p in prefs)
    card = f"""---
license: cc-by-4.0
license_name: cc-by-4.0
license_link: https://creativecommons.org/licenses/by/4.0/legalcode
language:
- ja
tags:
- japan
- kanto
- rainfall
- precipitation
- weather
- flood
size_categories:
- 10M<n<100M
pretty_name: Rainfall of the JMA stations in the Kanto region, daily and hourly (1974 to September 2026)
configs:
- config_name: daily
  data_files: parquet/daily/*.parquet
- config_name: hourly
  data_files: parquet/hourly/*.parquet
- config_name: stations
  data_files: parquet/stations.parquet
---

# jma-rain-kanto

Rainfall of the stations of the Japan Meteorological Agency (JMA) in the Kanto region, 1974-01-01 to 2026-09-30, with the JMA's
flags, as Parquet, one file per prefecture. This version has {len(prefs)} prefectures: {pref_list}; {nd:,} station-days of daily
values and {nh:,} station-hours of hourly values, {len(st)} stations. 東京都 (44) is to be added; Tokyo is
already published as [jma-rain-tokyo](https://huggingface.co/datasets/yuiseki/jma-rain-tokyo) (1974 to 2025).

Chiba is also published alone as [jma-rain-chiba](https://huggingface.co/datasets/yuiseki/jma-rain-chiba), with the reason given there
(the 2026 heavy rain); the Chiba files here hold the same values. Kanagawa is only published here. The columns are those of
jma-rain-tokyo and jma-rain-chiba, plus `pref` (the JMA's prefecture number).

The dataset is meant to grow by prefecture: each fetch keeps its files as served under `raw/<date of the fetch>/pref=<NN>/`, and the
Parquet of a prefecture is rebuilt from its latest fetch. October 2026 is not in this version: a test request that ended in October
2026, a month that had not ended, got an error page from the JMA's form, and the same request ended in September was served.

## Source

- The JMA's 過去の気象データ・ダウンロード (download of past weather data), <https://www.data.jma.go.jp/risk/obsdl/index.php>. The
  page sends a form to `/risk/obsdl/show/table` and gets a CSV (Shift_JIS); `scripts/02_fetch_daily.sh` and `scripts/04_fetch_hourly.sh`
  send the same form. This is not a published API and can change. The requests were made one at a time, 5 seconds apart.
- Stations: the station list of the page for each prefecture (`/risk/obsdl/top/station`, `pd=<NN>`), kept as
  `raw/<date>/pref=<NN>/stations_<NN>.json`. All stations in the list, including those that have ended.
- Daily values (`aggrgPeriod=1`): one request per station for 1974-01-01 to 2026-09-30, elements 降水量の合計 (`["101",""]`),
  1時間降水量の最大 (`["105","1"]`) and 10分間降水量の最大 (`["105","10"]`). The CSVs are kept unchanged in `raw/<date>/pref=<NN>/daily/`.
- Hourly values (`aggrgPeriod=9`, element 降水量 `["101",""]`): one request per station and year, for the years in which the station has
  daily values (`hourly_plan_<NN>.tsv`; a request of ten years was refused with HTTP 500 in the Tokyo fetch); 2026 is January to September.
  The CSVs are kept unchanged in `raw/<date>/pref=<NN>/hourly/<station>/<year>.csv`.
- Fetch dates: Chiba 2026-10-30 (1974 to 2025) and 2026-10-31 (daily to 2026-09 and hourly 2026), in the folder `raw/2026-10-30/`;
  Ibaraki, Tochigi, Gunma, Saitama and Kanagawa 2026-10-31, in `raw/2026-10-31/`. The time of each CSV is in its first line and in
  `parquet/daily_files/` and `parquet/hourly_files/`. Every raw file has its sha256 in `raw/<date>/pref=<NN>/MANIFEST.json`.

## Files

| File | What a row is |
|---|---|
| `parquet/daily/pref=<NN>.parquet` | A station and a day (JST) |
| `parquet/hourly/pref=<NN>.parquet` | A station and an hour (JST) |
| `parquet/stations.parquet` (and `stations/pref=<NN>.parquet`) | A station |
| `parquet/daily_files/`, `parquet/hourly_files/` | A CSV of the fetch: station, file, the time the JMA put in it, rows |

| Pref | Name | Stations (weather + AMeDAS) | Daily rows | Hourly rows |
|---|---|---|---|---|
{chr(10).join(rows)}

## Columns of the daily table

`station_id` (`s` + 5 digits for a weather station 気象台, `a` + 4 digits for an AMeDAS station), `date` (JST), then for each of `precip`
(daily total), `max1h` (greatest 1 hour amount) and `max10m` (greatest 10 minute amount):

| Column | Meaning (from the JMA's help for the CSV) |
|---|---|
| `<element>_mm` | The value in mm. Null where the CSV is blank |
| `<element>_nophen` | 現象なし情報: 1 no rain, 0 rain. Only weather stations have it; null for AMeDAS |
| `<element>_quality` | 品質情報: 8 normal, 5 quasi-normal (some data missing, within the allowance), 4 insufficient data, 2 doubtful, 1 missing, 0 not observed |
| `<element>_homog` | 均質番号: a change of the number marks a change of the observing environment; values with different numbers are not directly comparable. The JMA numbers them from 1 within each request |

and `pref`. Every station has a row for every day of the request, also before it started and after it ended; those rows have no
value. `stations` has `station_id`, `station_name`, `pref`, `kind` (`synop` or `amedas`), `lat` and `lon` (decimal degrees, converted from
the degrees and minutes to 0.1 minute of the list), `elevation_m`, `ended` (the date the list gives for the end of observation) and
`kansoku` (the list's code of the elements a station observes; `100000` is rain only).

## Columns of the hourly table

`station_id`, `time_end` (the end of the hour, JST, as the JMA writes it: `2026-08-13 20:00` is the hour from 19:00 to 20:00, and
`2026-08-14 00:00` is the last hour of 2026-08-13), then `precip_mm`, `precip_nophen` and `precip_quality` as above,
`precip_homog_in_file` (the homogeneity number of the CSV of that station and year; as the JMA numbers from 1 in each request, it can be
compared only within a year, use the daily `precip_homog` across years) and `pref`. The day of an hour is the date of `time_end - 1 hour`.
The hourly table has the hours of the years requested for each station only; 2026 has 6,552 hours (273 days, January to September).

## What was changed

- The CSVs were read with their own header rows (weather stations have four columns per element, AMeDAS three, without 現象なし情報),
  values made numbers and blanks null. Nothing was dropped, filled or corrected. `scripts/05_build.py` counts that every CSV row is in
  the Parquet and that (station, date) and (station, time_end) are unique. In the hourly table only the homogeneity column was renamed.
- The Parquet was checked against the CSVs with a second reader (DuckDB's CSV reader, `scripts/06_verify.py`) for every prefecture: rows,
  non-null values and sums agree for every station, daily and hourly, with no duplicate keys, and every station and year of the
  hourly table has 8,760 hours (8,784 in a leap year; 6,552 in 2026).

## Known issues (measured 2026-10-31)

General: the AMeDAS stations start in 1976 or later (the weather stations in 1974); the 10 minute maximum of the AMeDAS stations
starts in 2008 or 2009 (the weather stations: 1974). The station list gives the present positions only; past positions are not in the
data. The daily greatest 1 hour amount is measured over any 60 minutes, not only from the hour (this reading is not confirmed by the
JMA's text). Several mountain stations of Tochigi and Gunma have thousands of missing days; for 八溝山 (a0330, Tochigi), measured on 2026-10-31, the missing days fall in November to April (930 of 930 days in January, 734 of 900 in November, 870 of 900 in April, 7 of 961 in July), that is, the record has a winter gap; the data do not state a reason, and the other stations were not checked. The JMA can correct past values: a later fetch of the same request is not guaranteed to return the same CSV (Chiba 1974 to
2025 did not change between 2026-10-30 and 2026-10-31).

{chr(10).join(issues)}
## Licence

The JMA's terms for the content of its web site (気象庁ホームページについて, コンテンツの利用について,
<https://www.jma.go.jp/jma/kishou/info/coment.html>) follow the 公共データ利用規約 (第1.0版) (Public Data License 1.0), which is
compatible with CC BY 4.0. This dataset is offered under CC BY 4.0, with the credit to the JMA and the statement that it was processed:

> 出典：気象庁ホームページ「過去の気象データ・ダウンロード」（https://www.data.jma.go.jp/risk/obsdl/index.php）を加工して作成

It is not an official product of the JMA. The terms pages as read are kept in `raw/<date>/evidence/`.
"""
    (DATA / "README.md").write_text(card)
    (DATA / "LICENSE").write_text(
        """CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode)

The values are the past weather data of the Japan Meteorological Agency, from its 過去の気象データ・ダウンロード
(https://www.data.jma.go.jp/risk/obsdl/index.php), used under the JMA's terms for its web site content
(https://www.jma.go.jp/jma/kishou/info/coment.html), which follow the 公共データ利用規約 (第1.0版),
processed as described in README.md. It is not an official product of the JMA.
Credit: 出典：気象庁ホームページ「過去の気象データ・ダウンロード」（https://www.data.jma.go.jp/risk/obsdl/index.php）を加工して作成
"""
    )
    (DATA / "provenance.yaml").write_text(
        "source: 気象庁 過去の気象データ・ダウンロード\n"
        "url: https://www.data.jma.go.jp/risk/obsdl/index.php\n"
        "license: CC BY 4.0 (気象庁ホームページのコンテンツ利用規約、公共データ利用規約 第1.0版に準拠)\n"
        "period: 1974-01-01 to 2026-09-30\n"
        f"prefectures: {prefs}\n"
        "fetches:\n"
        "  pref=45 (Chiba): raw/2026-10-30/pref=45, 2026-10-30 and 2026-10-31\n"
        "  pref=40, 41, 42, 43, 46 (Ibaraki, Tochigi, Gunma, Saitama, Kanagawa): raw/2026-10-31/pref=<NN>, 2026-10-31\n"
        f"rows:\n  daily: {nd}\n  hourly: {nh}\n  stations: {len(st)}\n"
    )
    print(len(card), "characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
