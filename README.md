# `master-splinter` API

A small FastAPI service wrapping the two `master_splinter` analysers over
HTTP, for consumers (like `master-splinter-web`) that want a backend instead
of running the library client-side. It exposes the same two analyses as
[`cli/profile_analyser.py`](../cli/profile_analyser.py) and
[`cli/altitude_analyser.py`](../cli/altitude_analyser.py), documented in the
[root README](../README.md#module-a--dive-profile-analyser) — this document
covers the HTTP surface, not the model itself.

Repo-only, like `cli/` — not part of the distributed `master-splinter` wheel,
so the library keeps its zero-runtime-dependency guarantee.

> Not dive planning software. Never validated against a chamber. No output
> from either endpoint should be dived.

## Contents

- [`master-splinter` API](#master-splinter-api)
  - [Contents](#contents)
  - [Install](#install)
  - [Run](#run)
  - [Endpoint A — Profile Analysis](#endpoint-a--profile-analysis)
    - [Quick start](#quick-start)
    - [Request fields](#request-fields)
    - [Field reference](#field-reference)
    - [Response fields](#response-fields)
  - [Endpoint B — Altitude Analysis](#endpoint-b--altitude-analysis)
    - [Quick start](#quick-start-1)
    - [Request fields](#request-fields-1)
    - [Field reference](#field-reference-1)
    - [Response fields](#response-fields-1)
  - [Errors](#errors)
  - [Tests](#tests)
  - [CORS](#cors)

## Install

```bash
pip install -e ".[api]"
```

## Run

```bash
uvicorn api.main:app --reload
```

Serves on `http://127.0.0.1:8000`. Interactive docs (Swagger UI) at `/docs`,
ReDoc at `/redoc`, raw schema at `/openapi.json`.

## Endpoint A — Profile Analysis

`POST /profile-analysis` wraps `generate_dive_profile` + `analyse_profile`:
executes a planned dive against `ZHL-16C`, clamping to the decompression
ceiling so what comes out is a dive someone could actually perform, and
reports the stops that clamping forced.

### Quick start

```bash
curl -X POST localhost:8000/profile-analysis \
  -H 'content-type: application/json' \
  -d '{
    "boundaries": [
      {"depth": 40, "duration": 3, "phase": "descend", "variation": 1.0},
      {"depth": 40, "duration": 15, "phase": "constant", "variation": 2.0},
      {"depth": 20, "duration": 2, "phase": "ascend", "variation": 0.5},
      {"depth": 20, "duration": 2, "phase": "constant", "variation": 0.5},
      {"depth": 10, "duration": 2, "phase": "ascend", "variation": 0.3},
      {"depth": 10, "duration": 1, "phase": "constant", "variation": 0.2},
      {"depth": 5, "duration": 2, "phase": "ascend", "variation": 0.2},
      {"depth": 5, "duration": 5, "phase": "constant", "variation": 0.1},
      {"depth": 0, "duration": 1, "phase": "ascend", "variation": 0.0}
    ]
  }'
```

```json
{
  "seed": 1,
  "summary": {
    "planned_runtime": 33.0,
    "actual_runtime": 36.0,
    "max_depth": 41.97,
    "total_deco_time": 4.33,
    "stop_count": 2,
    "finding_count": 4
  },
  "stops": [
    {"depth": 6.0, "duration": 1.17, "started_at": 26.83},
    {"depth": 3.0, "duration": 3.17, "started_at": 32.5}
  ],
  "findings": [
    {"kind": "ceiling_violation", "label": "Ceiling", "time": 27.17, "depth": 4.94,
     "detail": "plan calls for 4.9 m but the ceiling is 6.0 m (1.1 m above it)"},
    {"kind": "ceiling_violation", "label": "Ceiling", "time": 33.0, "depth": 0.0,
     "detail": "plan calls for 0.0 m but the ceiling is 3.0 m (3.0 m above it)"},
    {"kind": "surfaced_with_obligation", "label": "Surfaced owing", "time": 33.0, "depth": 0.0,
     "detail": "plan surfaces owing 2.5 min, first stop at 3.0 m"},
    {"kind": "ascent_rate_exceeded", "label": "Ascent rate", "time": 19.0, "depth": 28.01,
     "detail": "ascending at 10.4 m/min, above the 10.0 m/min limit"}
  ],
  "track": ["... one row per simulated tick, see below ..."],
  "final_tissues": [1.425, 1.721, 1.872, "... 16 total ..."]
}
```

> This is the same reference dive `cli/profile_analyser.py --fresh` runs by
> default. The numbers differ slightly from the CLI's own quick start because
> the CLI defaults to `--seed 0` and this endpoint defaults to `seed=1` — see
> [`seed`](#seed) below.

### Request fields

| Field               | Default   | Description                                             |
| ------------------- | --------- | -------------------------------------------------------- |
| `boundaries`         | required  | The planned dive, as a list of segments                  |
| `gas`                | `"air"`   | Breathing gas preset                                     |
| `gradient_factors`   | `"30/85"` | Gradient factors, `LOW/HIGH`                              |
| `ppo2_limit`         | `1.4`     | Working ppO2 limit, capped at `1.6`                       |
| `ascent_rate`        | `10.0`    | Maximum ascent rate (m/min), also the final surfacing rate |
| `surface_pressure`   | `1.01325` | Ambient pressure at the surface (bar)                     |
| `seed`               | `1`       | Seed for the boundaries' random depth jitter              |

### Field reference

<details><summary><code>boundaries</code> — the planned dive</summary></br>

A list of segments, each `{depth, duration, phase, variation}`:

| Key         | Type   | Required | Description                                          |
| ----------- | ------ | -------- | ----------------------------------------------------- |
| `depth`     | float  | yes      | Target depth for this segment (meters), `0`–`120`     |
| `duration`  | float  | yes      | Length of the segment (minutes), must be positive     |
| `phase`     | string | yes      | One of `descend`, `constant`, `ascend`                |
| `variation` | float  | no (`0.0`) | Magnitude of random depth jitter applied per tick    |

This is the request-side equivalent of `--profile`, except there is no file —
the caller builds the profile inline rather than uploading a CSV/JSON dive
log. `generate_dive_profile` turns each segment into simulated ticks: a
`descend`/`ascend` segment ramps linearly from the previous segment's depth to
`depth`, a `constant` segment holds `depth` throughout. `variation` is a
magnitude, not a signed range — the library jitters each tick by
`uniform(-variation, +variation)`.

At least one segment is required, and every segment is validated
independently; the error names the offending segment by its 1-based position:

```json
{"detail": "segment 2: phase must be one of descend, constant, ascend, got 'hover'"}
{"detail": "segment 1: duration must be positive, got 0.0"}
{"detail": "segment 3: variation cannot be negative, got -0.5"}
{"detail": "the profile needs at least one segment"}
```

</details>

<details><summary><code>gas</code> — the breathing mix</summary></br>

One of `air`, `ean32`, `ean40` — the same presets as the CLI's `--gas`. The
model tracks nitrogen only, so a mix is fully described by its nitrogen
fraction; the balance is treated as oxygen.

| Preset  | N2     | O2     | MOD @ `1.4` bar | MOD @ `1.6` bar |
| ------- | ------ | ------ | --------------- | --------------- |
| `air`   | `0.79` | `0.21` | `56.5 m`        | `66.1 m`        |
| `ean32` | `0.68` | `0.32` | `33.6 m`        | `39.9 m`        |
| `ean40` | `0.60` | `0.40` | `24.9 m`        | `29.9 m`        |

There is no `n2_fraction` override on this endpoint (unlike the CLI's
`--n2-fraction`) — pass one of the three presets. An unknown value comes back
as:

```json
{"detail": "unknown gas 'trimix', expected one of air, ean32, ean40"}
```

Presets live in `GAS_MIXES` in `src/master_splinter/configs/limits.py`.

</details>

<details><summary><code>ppo2_limit</code> — how much oxygen exposure to accept</summary></br>

The oxygen partial pressure the plan is judged against, in bar. Exceeding it
produces an `Oxygen (MOD)` finding and moves the reported `MOD` accordingly.
Validation requires `0 < ppo2_limit <= 1.6`:

```json
{"detail": "need 0 < limit <= 1.6, got 2.0"}
```

The cap is the `1.6 bar` contingency limit rather than an arbitrary ceiling —
see the equivalent note under `--ppo2-limit` in the [root
README](../README.md#module-a--dive-profile-analyser).

</details>

<details><summary><code>gradient_factors</code> — how conservative to be</summary></br>

A `"LOW/HIGH"` string of two integer percentages, e.g. `"30/85"`. `LOW`
applies at the first decompression stop and `HIGH` at the surface, with the
allowed supersaturation interpolated linearly between them. `"100/100"`
disables the conservatism entirely and gives pure Bühlmann.

Validation requires `0 < LOW <= HIGH <= 100`:

```json
{"detail": "expected LOW/HIGH such as 30/85, got 'abc'"}
{"detail": "need 0 < low <= high <= 100, got 85/30"}
```

</details>

<details><summary><code>ascent_rate</code> and <code>surface_pressure</code></summary></br>

`ascent_rate` (m/min) sets the rate the final surfacing leg is walked at, and
is also the rate the plan itself is judged against for the `Ascent rate`
finding. `surface_pressure` (bar) is the ambient pressure at the surface —
lower it to model a dive at altitude (`pressure_at_elevation(m)` from
`master_splinter.model.atmosphere` converts an elevation for you before
calling this endpoint). Both are passed straight through to `analyse_profile`
with no extra validation beyond FastAPI's type coercion.

</details>

<details><summary><code>seed</code> — reproducibility</summary></br>

Seeds the random depth jitter each segment's `variation` applies, defaulting
to `1`. The same request with the same `seed` always returns the same `track`
and stops — `random.seed(seed)` runs immediately before generation, matching
`cli/profile_analyser.py --seed` and `master-splinter-web/src/glue.py`.

</details>

### Response fields

| Field           | Description                                                                 |
| --------------- | ---------------------------------------------------------------------------- |
| `seed`          | The seed actually used (echoes the request)                                  |
| `summary`       | `planned_runtime`, `actual_runtime`, `max_depth`, `total_deco_time`, `stop_count`, `finding_count` |
| `stops`         | Decompression stops performed: `depth`, `duration`, `started_at`             |
| `findings`      | Where the plan was unsafe or unexecutable — see the `kind`/`label` table below |
| `track`         | One row per simulated tick — see below                                       |
| `final_tissues` | The 16 tissue nitrogen pressures at the end of the dive (bar). Feed straight into `/altitude-analysis`'s `tissues` |

`findings[].kind` / `findings[].label`:

| `kind`                       | `label`           | Meaning                                         |
| ---------------------------- | ------------------ | ------------------------------------------------ |
| `ceiling_violation`           | Ceiling            | The plan called for shallower than the ceiling allowed |
| `ascent_rate_exceeded`        | Ascent rate        | Ascending faster than `ascent_rate`               |
| `surfaced_with_obligation`    | Surfaced owing     | The plan surfaced with decompression still owed   |
| `mod_exceeded`                | Oxygen (MOD)       | ppO2 exceeded `ppo2_limit` (or the `1.6` contingency limit) |

`track[]` rows are `{t, planned, actual, ambient, tolerated, tissues}` —
elapsed time, planned vs. actual depth, ambient pressure, the whole tissue
set's tolerated ambient pressure at `gf_high`, and all 16 compartment
pressures. It ticks every **10 s** while following the planned `boundaries`,
and every **30 s** during any decompression obligation or the final ascent to
the surface (`generate_dive_profile`'s `interval` and `DECO_STEP`
respectively — neither is configurable through this API).

## Endpoint B — Altitude Analysis

`POST /altitude-analysis` wraps `analyse_altitude_change`: decides whether a
given elevation change is safe on a given tissue state, the same question
`cli/altitude_analyser.py` answers from a state file.

### Quick start

Using the `final_tissues` from the profile analysis above, and checking a
`2,400 m` cabin-altitude flight straight after surfacing:

```bash
curl -X POST localhost:8000/altitude-analysis \
  -H 'content-type: application/json' \
  -d '{
    "tissues": [1.42517, 1.72099, 1.87208, 1.84768, 1.71938, 1.55796,
                1.39259, 1.24381, 1.12083, 1.03753, 0.98013, 0.93364,
                0.8962,  0.86586, 0.84174, 0.82265],
    "elevation_gain": 2400
  }'
```

```json
{
  "elevation_gain": 2400.0,
  "surface_interval": 0.0,
  "start_elevation": 0.0,
  "start_pressure": 1.01325,
  "target_pressure": 0.7563,
  "safe": false,
  "raw": {
    "label": "raw Bühlmann", "gf": 1.0, "safe": false,
    "tolerated_pressure": 0.8934, "limiting_compartment": 5, "limiting_half_time": 27.0,
    "margin": -0.1371, "wait_minutes": 12.0, "max_gain": 1049.6
  },
  "gradient": {
    "label": "GF 85", "gf": 0.85, "safe": false,
    "tolerated_pressure": 0.997, "limiting_compartment": 5, "limiting_half_time": 27.0,
    "margin": -0.2407, "wait_minutes": 23.3, "max_gain": 136.6
  }
}
```

Flying immediately after a `40 m` dive isn't safe under either conservatism
setting — waiting the reported `wait_minutes`, or flying commercial after the
usual 12–18 h, would be.

### Request fields

| Field               | Default   | Description                                                   |
| -------------------- | --------- | -------------------------------------------------------------- |
| `tissues`            | required  | The 16 tissue nitrogen pressures left by the dive (bar), **not pre-aged** |
| `elevation_gain`     | required  | Meters to ascend, relative to the dive site; negative descends |
| `surface_interval`   | `0.0`     | Minutes already spent at the surface before the change          |
| `gf_high`            | `0.85`    | Gradient factor applied at the surface                          |
| `surface_pressure`   | `1.01325` | Ambient pressure at the dive site (bar)                          |

### Field reference

<details><summary><code>tissues</code> — the dive's tissue loading</summary></br>

Exactly 16 floats, as saved at the end of a dive (`final_tissues` from
`/profile-analysis`, or a CLI/web state file's `tissues` array). **Not**
pre-aged — this endpoint applies `surface_interval` itself via `age_tissues`,
so do not off-gas them before sending. A wrong count is rejected before any
analysis runs:

```json
{"detail": [{"type": "too_short", "loc": ["body", "tissues"], "msg": "List should have at least 16 items after validation, not 15", ...}]}
```

</details>

<details><summary><code>elevation_gain</code> — the change to test</summary></br>

Meters to ascend, **relative to the dive site rather than to sea level** — the
site is `surface_pressure`, converted to an elevation internally. So
`elevation_gain=600` from a `1,800 m` lake (`surface_pressure` set
accordingly) ends at the same `2,400 m` that `elevation_gain=2400` from the
coast does.

Negative values are allowed and meaningful: descending raises ambient
pressure and is always safe, so the answer is always `safe: true` with
`wait_minutes: 0.0`.

</details>

<details><summary><code>surface_interval</code> — time already spent at the surface</summary></br>

Minutes at the surface *before* the elevation change, used to off-gas
`tissues` first. Unlike the CLI, there is no wall-clock default here — the
caller always states it explicitly, since an HTTP service has no notion of
"since the last dive" without a timestamp to compare against.

</details>

<details><summary><code>gf_high</code> — how conservative to be</summary></br>

A single gradient factor, `0`–`1`, applied at the surface — equivalent to
only the `HIGH` half of the CLI's `--gf LOW/HIGH`. There is no ascent to
interpolate along here (a diver sitting at the surface isn't mid-ascent), so
`gf_low` plays no part and isn't accepted by this endpoint.

</details>

<details><summary><code>surface_pressure</code> — the dive site</summary></br>

Ambient pressure at the dive site (bar), defaulting to sea level
(`1.01325`). Lower it to model a dive that started at altitude — convert an
elevation to a pressure with `pressure_at_elevation(m)` from
`master_splinter.model.atmosphere` before calling this endpoint.

</details>

### Response fields

| Field              | Description                                                       |
| ------------------ | ------------------------------------------------------------------ |
| `elevation_gain`    | Echoes the request                                                  |
| `surface_interval`  | Echoes the request                                                  |
| `start_elevation`   | `surface_pressure` expressed as an elevation (meters)                |
| `start_pressure`    | Echoes `surface_pressure`                                            |
| `target_pressure`   | Ambient pressure at `start_elevation + elevation_gain` (bar)          |
| `safe`              | `true` only when **both** `raw` and `gradient` are safe               |
| `raw`               | Verdict under raw Bühlmann (`gf=1.0`)                                 |
| `gradient`          | Verdict under `gf_high`                                               |

Each verdict (`raw`, `gradient`) carries:

| Field                  | Description                                                              |
| ----------------------- | -------------------------------------------------------------------------- |
| `label`                 | Human name for the conservatism used                                       |
| `gf`                    | Gradient factor applied                                                    |
| `safe`                  | `true` when `target_pressure` is tolerated right now                       |
| `tolerated_pressure`    | Lowest ambient pressure the tissues currently tolerate (bar)                |
| `limiting_compartment`  | 1-based index of the limiting compartment                                  |
| `limiting_half_time`    | Half-time of that compartment (minutes)                                    |
| `margin`                | `target_pressure - tolerated_pressure` (bar); negative is a breach         |
| `wait_minutes`          | Additional surface time needed, `0.0` if already safe, `null` if no interval makes it safe |
| `max_gain`              | Largest elevation gain tolerable right now (meters); negative means even staying put breaches the limit |

> `wait_minutes: null` is a distinct state from `"wait 90 minutes"` — some
> gains are unreachable however long the diver waits (raw Bühlmann tops out
> around `5,600 m` of tolerated elevation at full surface equilibrium).

## Errors

Bad input — an unknown gas, malformed gradient factors, a segment with a
negative duration, the wrong tissue count, and so on — comes back as `422`.
Domain-level errors (anything `master_splinter.validation` or the analysers
themselves raise as a plain `ValueError`) return `{"detail": "<message>"}`,
the same wording the CLI already uses; malformed request bodies that fail
Pydantic's own type/shape checks (missing required fields, wrong types, a
`tissues` list of the wrong length) return FastAPI's standard validation
error shape instead.

## Tests

```bash
pip install -e ".[api,test]"
pytest tests/api
```

## Deploy

Targets Cloud Run. `api/` is its own build context — unlike local
development, the image installs `master-splinter` from PyPI
([`requirements.txt`](requirements.txt)) rather than the repo's `src/`, so it
builds and deploys with no dependency on anything outside this directory:

```bash
docker build -t master-splinter-api api/
docker run -p 8080:8080 master-splinter-api
```

- [`api/Dockerfile`](Dockerfile) — the image.
- [`api/requirements.txt`](requirements.txt) — pinned to a published
  `master-splinter` release; bump it after cutting one.
- [`api/deploy/service.yaml`](deploy/service.yaml) — the Cloud Run service
  manifest (`gcloud run services replace`). `PROJECT_ID`/`REGION` are
  literal placeholders, rendered at build time.
- [`api/deploy/cloudbuild.yaml`](deploy/cloudbuild.yaml) — builds, pushes to
  Artifact Registry, and deploys the manifest above. Run by hand for now,
  from the repo root:
  `gcloud builds submit --config=api/deploy/cloudbuild.yaml --substitutions=_REGION=us-central1 api/`
- [`.github/workflows/deploy-api.yml`](../.github/workflows/deploy-api.yml)
  — `workflow_dispatch`-only until a GCP project exists to point it at; see
  the workflow's comments for the repository variables it needs
  (`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER`,
  `GCP_DEPLOY_SERVICE_ACCOUNT`).

## CORS

`main.py` currently allows all origins so the website can call it during
development. Restrict `allow_origins` to the deployed site before running
this anywhere public.
