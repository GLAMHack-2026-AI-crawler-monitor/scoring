# scoring

Scores every IP address in a web access log (CSV) for bot-like behaviour.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 score_bot_ips.py synthetic_stress_log_sample.csv --out ip_scores_sample.csv
```

This reads `synthetic_stress_log_sample.csv` (a 1,000-line sample log) and writes
`ip_scores_sample.csv`, one row per IP with a bot score (0-5), a label, and the
reasons behind it. See `BOT_SCORING_NOTES.md` for the full developer notes: input
format, how the scoring works, converting other log formats, and the dashboard.
