# jma-rain-kanto

Scripts that fetch, build and verify the rainfall of the stations of the Japan Meteorological Agency in the Kanto region
(daily and hourly, 1974 to September 2026; Ibaraki, Saitama, Chiba and Kanagawa so far) from the JMA's 過去の気象データ・ダウンロード,
and publish it, one Parquet file per prefecture.

The data and its card are on Hugging Face: <https://huggingface.co/datasets/yuiseki/jma-rain-kanto>
(published at revision `e7064e30dabf6fd3bd5fa8d5e01d8b63f69a3a5b`; `docs/revision.json`). Chiba is also published alone, with the
reason for its 2026 data: <https://huggingface.co/datasets/yuiseki/jma-rain-chiba> (its scripts: <https://github.com/yuiseki/jma-rain-chiba>).

- `scripts/01_stations.sh`: the station list of a prefecture (the JMA's prefecture number: 40 Ibaraki, 41 Tochigi, 42 Gunma,
  43 Saitama, 45 Chiba, 46 Kanagawa).
- `scripts/02_fetch_daily.sh`, `03_plan_hourly.py`, `04_fetch_hourly.sh`: fetch, one request at a time, 5 seconds apart.
- `scripts/05_build.py`, `06_verify.py`, `07_place.py`, `08_profile.py`, `09_manifest.py`: build the Parquet, check it against the CSVs
  with a second reader, place it, profile it, and checksum the raw files.
- `scripts/11_card.py`, `src/publish.py`, `scripts/10_verify_hub.py`: the card, the publication, and the read-back from the Hub.

The code is offered as is; the data is CC BY 4.0 with the credit to the JMA (see the card).
