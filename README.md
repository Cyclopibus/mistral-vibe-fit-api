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

## Project Structure

```
/project
├── /src
│   ├── /parsers
│   │   └── fit_parser.py      # FIT file parsing using fit-python-sdk
│   ├── /services
│   │   ├── storage.py         # Database storage service
│   │   ├── stats.py           # Statistics and comparison engine
│   │   └── visualizer.py       # Plot generation service
│   ├── /api
│   │   └── main.py            # Litestar API endpoints
│   └── /database
│       └── models.py          # SQLAlchemy database models
├── /tests
│   ├── test_fit_parser.py    # Tests for FIT parser
│   ├── test_storage.py       # Tests for storage service
│   ├── test_stats.py         # Tests for stats engine
│   └── test_api.py           # Tests for API endpoints
├── pyproject.toml            # Project configuration for uv
├── requirements.txt          # Legacy requirements (for pip)
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+

### Installation with uv (Recommended)

1. Install `uv` (if not already installed):
   ```bash
   pip install uv
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/Cyclopibus/mistral-vibe-fit-api.git
   cd mistral-vibe-fit-api
   ```

3. Install dependencies with uv:
   ```bash
   uv sync
   ```

4. (Optional) Install dev dependencies:
   ```bash
   uv sync --all-extras
   ```

### Installation with pip (Legacy)

1. Clone the repository:
   ```bash
   git clone https://github.com/Cyclopibus/mistral-vibe-fit-api.git
   cd mistral-vibe-fit-api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install dev dependencies:
   ```bash
   pip install -r requirements.txt pytest pytest-cov python-dotenv
   ```

## Running the API

### With uv

```bash
# Activate the virtual environment
source .venv/bin/activate  # On Unix
.\.venv\Scripts\activate   # On Windows

# Start the API
litestar run src/api/main.py
```

### With pip

```bash
litestar run src/api/main.py
```

Or with uvicorn:

```bash
uvicorn src.api.main:app --reload
```

The API will be available at `http://localhost:8000`. OpenAPI documentation is available at `/schema`.

## API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/upload` | POST | Upload and parse a FIT file | `file` (multipart) |
| `/activities` | GET | List activities with filters | `user_id`, `start_date`, `end_date`, `activity_type`, `limit`, `offset` |
| `/activities/{id}` | GET | Get activity details | `id` (path) |
| `/stats` | GET | Aggregate statistics | `user_id`, `start_date`, `end_date`, `metric`, `activity_type` |
| `/compare` | GET | Compare activities | `activity_ids` (comma-separated) |
| `/export/{id}` | GET | Export activity data | `id` (path), `format` (csv/json) |
| `/plot/{id}` | GET | Generate plot | `id` (path), `metric`, `width`, `height` |
| `/bike-metrics/{id}` | GET | Get bike-specific metrics | `id` (path) |
| `/trends` | GET | Get time series trends | `user_id`, `start_date`, `end_date`, `metric`, `activity_type`, `time_window` |

## Database Schema

```mermaid
graph TD
    User --> Activity
    Device --> Activity
    Activity --> Session
    Activity --> Lap
    Activity --> Record

    User ["User\n    - id\n    - username\n    - email\n    - created_at\n    - updated_at"]

    Device ["Device\n    - id\n    - manufacturer\n    - product_name\n    - serial_number\n    - software_version\n    - hardware_version"]

    Activity ["Activity\n    - id\n    - activity_id\n    - activity_type\n    - start_time\n    - duration\n    - total_distance\n    - total_ascent\n    - total_descent\n    - num_sessions\n    - num_laps"]

    Session ["Session\n    - id\n    - session_id\n    - start_time\n    - total_elapsed_time\n    - total_timer_time\n    - total_distance\n    - avg_speed\n    - max_speed\n    - avg_heart_rate\n    - max_heart_rate\n    - avg_cadence\n    - max_cadence\n    - avg_power\n    - max_power\n    - sport\n    - sub_sport"]

    Lap ["Lap\n    - id\n    - lap_id\n    - start_time\n    - total_elapsed_time\n    - total_timer_time\n    - total_distance\n    - avg_speed\n    - max_speed\n    - avg_heart_rate\n    - max_heart_rate\n    - avg_cadence\n    - max_cadence\n    - avg_power\n    - max_power\n    - intensity"]

    Record ["Record\n    - id\n    - timestamp\n    - position_lat\n    - position_long\n    - distance\n    - speed\n    - cadence\n    - power\n    - heart_rate\n    - altitude\n    - temperature\n    - time_from_course"]
```

## Example API Calls

### Upload a FIT file

```bash
curl -X POST -F "file=@activity.fit" http://localhost:8000/upload
```

### List activities

```bash
curl http://localhost:8000/activities
```

### Get activity details

```bash
curl http://localhost:8000/activities/1
```

### Get statistics

```bash
curl "http://localhost:8000/stats?metric=power&activity_type=cycling"
```

### Compare activities

```bash
curl "http://localhost:8000/compare?activity_ids=1,2,3"
```

### Export as CSV

```bash
curl http://localhost:8000/export/1?format=csv -o activity.csv
```

### Get bike metrics

```bash
curl http://localhost:8000/bike-metrics/1
```

### Get trends

```bash
curl "http://localhost:8000/trends?metric=power&time_window=daily"
```

## Python Usage

```python
from src.parsers.fit_parser import FITParser
from src.services.storage import DataStorage
from src.services.stats import StatsEngine
from src.services.visualizer import Visualizer

# Parse a FIT file
parser = FITParser()
parsed_data = parser.parse_file("activity.fit")

# Store the data
storage = DataStorage()
activity_id = storage.store_activity(parsed_data, username="test_user")

# Get statistics
stats = StatsEngine(storage)
power_stats = stats.aggregate_metrics(metric="power")

# Compare activities
comparison = stats.compare_activities([1, 2, 3])

# Get bike metrics
bike_metrics = stats.get_bike_specific_metrics(activity_id)

# Generate plots
visualizer = Visualizer()
plot_data = visualizer.generate_plot(storage.get_activity(activity_id), "power")
```

## Project Management with uv

### Common uv Commands

```bash
# Install the project
uv sync

# Install with all extras (dev dependencies)
uv sync --all-extras

# Run the API
uv run litestar run src/api/main.py

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=term

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update all dependencies
uv lock --upgrade

# Show dependency graph
uv tree
```

## Testing

Run all tests:

```bash
# With uv
uv run pytest tests/ -v

# With pip
pytest tests/ -v
```

Run specific test modules:

```bash
pytest tests/test_fit_parser.py -v
pytest tests/test_storage.py -v
pytest tests/test_stats.py -v
pytest tests/test_api.py -v
```

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection URL (default: `sqlite:///fit_api.db`)
- `DEBUG`: Enable debug mode (default: `True`)

### Database Support

- **SQLite**: Default, file-based database
- **PostgreSQL**: Set `DATABASE_URL` to PostgreSQL connection string

## Bike-Specific Features

The API prioritizes bike-related metrics:

- **Power**: Watts, average, max, min, standard deviation
- **Cadence**: RPM, average, max, min, standard deviation
- **Speed**: m/s and km/h, average, max, min
- **Heart Rate**: BPM, average, max, min, standard deviation
- **GPS**: Latitude, longitude, distance
- **Altitude**: Meters, ascent, descent

## Visualization

All plots use the darker green color (`#006400`) as specified in the requirements. Available plot types:

- Single metric plots
- Multi-metric comparison plots
- Summary plots with multiple subplots
- Time series trend plots

## Success Criteria

- ✅ FIT files are parsed **only using `fit-python-sdk`**
- ✅ All bike-related metrics are stored and queryable
- ✅ Time-based comparisons and aggregations work
- ✅ Plots are generated with **darker green** (`#006400`)
- ✅ Comprehensive test coverage for parsing, storage, and stats
- ✅ Git history shows regular, meaningful commits

## Why uv?

We use `uv` as our Python package manager because it provides:

- **Blazing Fast**: Much faster dependency resolution and installation
- **Modern**: Built with Rust, designed for Python 3.11+
- **Simple**: Single command interface for all operations
- **Reliable**: Deterministic builds and reproducible environments
- **Feature-rich**: Built-in virtual environment management, dependency locking, and more

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request
