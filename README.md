# ProcessMiner AI

ProcessMiner AI is a deterministic, rule-based process-mining CLI. It reads CSV event logs, discovers observed activities and transitions, measures stage durations, waits, and queued cases, then ranks bottlenecks and automation targets using published rules. The bundled examples are fictional, synthetic data.

## Quickstart

Requires Python 3.10 or newer. The project has no runtime dependency on machine-learning or GPU packages.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .

processminer fixtures --out data
processminer mine data/order_fulfilment.csv --out graph.json
processminer bottlenecks graph.json
processminer targets graph.json
processminer report graph.json --format md --out report.md
processminer report graph.json --format html --out report.html
```

The same commands work as `python -m processminer ...` when running from the repository. Use `data/clean_control.csv` to see a control log with no bottleneck findings. Fixture generation uses fixed timestamps and a fixed sequence, so it writes byte-identical files every time. No random generator is used.

## HONESTY BOUNDARY

This project demonstrates deterministic process mining on declared CSV inputs. The bundled fixture logs are synthetic and fictional. The tool uses fixed rules, not a learned model or live data source. Its outputs make no claim about any real company's process and do not monitor real employees. Synthetic fixture output is evidence about the fixture only.

The CLI help, graph JSON, findings, and reports carry this boundary. Do not present the fixture results as customer, company, or employee data.

## Architecture

```text
Synthetic CSV fixtures or a declared CSV log
                 |
                 v
     CSV validation and UTC parsing
                 |
                 v
  Per-case ordering and graph discovery
       |                    |
       v                    v
 stage durations,       transition counts
 waits, queue lengths          |
       |                       |
       +-----------+-----------+
                   v
     bottleneck thresholds and evidence
                   |
                   v
      fixed automation scoring formula
                   |
                   v
          JSON, Markdown, or HTML
```

`processminer.fixtures` writes two synthetic logs. `processminer.miner` validates rows and derives graph metrics. `processminer.analysis` applies documented thresholds and formula weights. `processminer.report` renders stable Markdown or HTML. The CLI composes these functions and reports rejected rows by row number and named validation error.

## Log format reference

CSV headers are case sensitive and must include these columns:

| Column | Meaning |
|---|---|
| `case_id` | Identifier that groups events belonging to one process instance |
| `activity` | Activity or stage name |
| `start` | Event service start timestamp in ISO 8601 format with a timezone |
| `end` | Event service end timestamp in ISO 8601 format with a timezone, not before `start` |
| `actor` | Actor label used for the fixed manual versus automated share rule |

Example:

```csv
case_id,activity,start,end,actor
SYN-ORDER-001,order_intake,2026-01-05T09:00:00Z,2026-01-05T09:02:00Z,agent-1
SYN-ORDER-001,payment_validation,2026-01-05T09:02:00Z,2026-01-05T09:08:00Z,agent-1
```

Rows with empty required values, extra fields, invalid timestamps, missing timezones, or an end before the start are rejected with row-specific named errors. Other valid rows still contribute to the graph. Timestamps are normalized to UTC. Within each case, events are ordered by start, end, activity, then source row number. An edge frequency counts how many cases contain that observed adjacent activity transition.

Activity median duration is calculated from `end - start`. Wait is the nonnegative gap between the current event start and the previous event end in its case; the first event in a case has zero wait. An arrival for a stage is the preceding event end, or the first event's start. Queue length at an arrival counts same-activity events that have arrived by that time and whose service start is later than that time. Mean and maximum queue lengths are computed across each activity's arrivals. These queue values are inferred from the supplied timestamps, not from an external queue system.

## Bottleneck thresholds

A stage is flagged if its median wait is at least 10 minutes or its mean measured queue length is at least 2 cases. The impact score is:

```text
max(median_wait_minutes / 10, mean_queue_length / 2)
```

Findings sort by descending impact score and then activity name. Each finding includes the measured wait and queue lengths, the metric fields that crossed a threshold, and a pointer such as `graph.activities.pick_items`.

## Automation scoring formula

Each activity receives the following score from 0 to 1:

```text
score = 0.35 * repetition
      + 0.25 * manual_actor_share
      + 0.20 * duration_factor
      + 0.20 * rule_suitability
```

| Input | Definition |
|---|---|
| `repetition` | Activity event count divided by the largest activity event count in this graph |
| `manual_actor_share` | Fraction of activity events whose actor is not `system`, `bot`, `automation`, `automated`, `service`, or `api` (case insensitive) |
| `duration_factor` | Activity median duration divided by the largest median duration in this graph; zero if all medians are zero |
| `rule_suitability` | 1 when the activity name contains one of the fixed terms below, otherwise 0 |

Fixed suitability terms: `payment_validation`, `shipping_label_creation`, `invoice_data_entry`, `address_validation`, and `email_notification`. This is a small, inspectable rule list, not a model prediction. CLI output and reports show every component used for each score. Ties sort by activity name.

## Determinism and compute

For an unchanged CSV, graph JSON and reports are byte-identical. The analyzer does not use randomness, training, or GPU computation. It records no current timestamp or source path in outputs. CPU-only Python standard-library code performs all analysis.

## Tests

Run the full suite with:

```powershell
python -m pytest
```

Tests cover fixture determinism, ordered edges, hand-computed stage medians, queue-derived bottlenecks, zero-flag control data, target ranking and score inputs, named row errors, stable reports, end-to-end commands, and CLI smoke checks.
