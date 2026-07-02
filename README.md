# Garmin FIT File API

A Python API using **Litestar** to parse, store, and analyze Garmin FIT files exclusively with the official [`fit-python-sdk`](https://github.com/garmin/fit-python-sdk).

## Features

- **FIT File Parsing**: Parse Garmin FIT files using the official `fit-python-sdk`
- **Data Storage**: Store parsed data in SQLite (default) or PostgreSQL
- **Bike Focus**: Prioritize bike-related fields (power, cadence, speed, GPS)
- **Data Exploration**: Query activities, sessions, laps, and time-series records
- **Comparison**: Compare multiple activities side by side
- **Statistics**: Aggregate metrics with min/max/mean/median/std calculations
- **Visualization**: Generate plots with darker green (#006400) color scheme
- **Export**: Export data as CSV or JSON
- **RESTful API**: Comprehensive endpoints for all functionality

## Setup

### Prerequisites

- Python 3.11+
- uv package manager

### Installation

```bash
# Install uv
pip install uv

# Clone the repository
git clone https://github.com/Cyclopibus/mistral-vibe-fit-api.git
cd mistral-vibe-fit-api

# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

## Running the API

```bash
# Run the API
uv run litestar --app src.api.main:app run

# Run with auto-reload for development
uv run litestar --app src.api.main:app run --reload
```

The API will be available at `http://localhost:8000`. OpenAPI documentation is available at `/schema`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check endpoint |
| `/upload` | POST | Upload and parse a FIT file |
| `/activities` | GET | List activities with filters |
| `/activities/{id}` | GET | Get activity details |
| `/stats` | GET | Aggregate statistics |
| `/compare` | GET | Compare activities |
| `/export/{id}` | GET | Export activity data |
| `/plot/{id}` | GET | Generate plot |
| `/bike-metrics/{id}` | GET | Get bike-specific metrics |
| `/trends` | GET | Get time series trends |

## Project Structure

```
project/
├── src/
│   ├── parsers/
│   │   └── fit_parser.py      # FIT file parsing
│   ├── services/
│   │   ├── storage.py         # Database storage
│   │   ├── stats.py           # Statistics engine
│   │   └── visualizer.py       # Plot generation
│   ├── api/
│   │   └── main.py            # Litestar endpoints
│   └── database/
│       └── models.py          # SQLAlchemy models
├── tests/
│   ├── test_fit_parser.py
│   ├── test_storage.py
│   ├── test_stats.py
│   └── test_api.py
├── pyproject.toml            # Project configuration
└── README.md
```

## Usage Examples

### Upload a FIT file

```bash
curl -X POST -F "file=@activity.fit" http://localhost:8000/upload
```

### List activities

```bash
curl http://localhost:8000/activities
```

### Get statistics

```bash
curl "http://localhost:8000/stats?metric=power"
```

## Project Management

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Add a dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name
```

## Success Criteria

- ✅ FIT files are parsed **only using `fit-python-sdk`**
- ✅ All bike-related metrics are stored and queryable
- ✅ Time-based comparisons and aggregations work
- ✅ Plots are generated with **darker green** (`#006400`)
- ✅ Comprehensive test coverage
- ✅ Modern package management with uv

## License

MIT License
