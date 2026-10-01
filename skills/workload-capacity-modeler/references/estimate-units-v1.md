# Estimate Unit Contract v1.0

Every `EST-*` record must be verifiable by machine. `scripts/units.py` evaluates the formula with units and compares the result with the declared value.

```json
{
  "id": "EST-001",
  "formula": "peak_rate * payload",
  "inputs": {
    "peak_rate": {"value": 100, "unit": "req/s", "source": "ASM-001"},
    "payload": {"value": 1, "unit": "KB/req"}
  },
  "value": 0.8,
  "unit": "Mbit/s",
  "horizon": "peak five-minute window",
  "scenario": "peak",
  "related_ids": ["ASM-001", "NFR-001"]
}
```

## Rules

- `inputs` maps identifier names to `{value, unit}`; an optional `source` must be an existing stable ID. Every input must appear in the formula.
- `formula` uses input names, numeric literals, `+ - * /`, integer `**`, `min`, `max`, and dimensionless `ceil`/`floor`. Nothing else is evaluated.
- Numeric literals are dimensionless. Units convert automatically, so `/ 60` or `* 8` are scaling factors, not unit conversions. `events_per_minute / 60` declared as `events/s` fails; declare the input as `events/min` and the formula as `events_per_minute`.
- Addition, subtraction, `min`, and `max` require matching dimensions. The result dimension must equal the declared unit, and the converted value must be within 1% of `value`.

## Units

| Kind | Accepted spellings |
|---|---|
| time | `ns`, `us`, `ms`, `s`, `sec`, `min`, `h`, `hr`, `day`, `d`, `week`, `month` (30 d), `year` (365 d), plural forms |
| data | `B`, `KB`, `MB`, `GB`, `TB`, `PB` (decimal), `KiB`, `MiB`, `GiB`, `TiB` (binary), `bit`, `Kbit`, `Mbit`, `Gbit`, `byte(s)`, `bit(s)` |
| rates | `rps`, `qps`, `tps`, `bps`, `Kbps`, `Mbps`, `Gbps` |
| counts | `event`, `request`/`req`, `query`, `message`/`msg`, `user`, `record`, `op`, `order`, `transfer`, `transaction`/`txn`, `url`, `item`, `connection`, `session`, `device`, `object`, `write`, `read`, `node`, `server`, `instance`, `core`, `page`, `file`, `key`, `batch`, `job`, `task`, `entry`, `account`, `row`, `document`, `partition`, `shard`, `notification`, `payment`, `redirect`, `upload`, `download`, `packet` and plurals. Different count nouns are different dimensions. |
| dimensionless | `1`, `x`, `ratio`, `factor`, `replica`, `copy`, `%`, `percent` |
| currency | `USD`, `EUR`, `GBP`, `TRY` |

Compose units with `/`, `*`, `·`, spaces, `per`, and integer exponents (`req/user/day`, `GB/day`, `s^-1`). Ambiguous spellings such as `b`, `kb`, `Mb`, or `m` are rejected.
