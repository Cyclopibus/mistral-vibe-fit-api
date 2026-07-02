"""
Tests for the Stats Engine
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta
from src.services.stats import StatsEngine
from src.services.storage import DataStorage
from src.parsers.fit_parser import ParsedFITData, Activity, DeviceInfo, Record, Session, Lap


@pytest.fixture
def stats_engine():
    """Create a stats engine with isolated database for testing"""
    storage = DataStorage("sqlite:///:memory:")
    stats = StatsEngine(storage)
    # Clear any existing data
    storage.clear_all_data()
    yield stats
    storage.close()


class TestStatsEngine:
    """Test cases for StatsEngine class"""
    
    def test_stats_engine_initialization(self, stats_engine):
        """Test that StatsEngine initializes correctly"""
        assert stats_engine is not None
        assert hasattr(stats_engine, 'storage')
    
    def test_aggregate_metrics_no_data(self, stats_engine):
        """Test aggregation with no data"""
        # Clear any existing data first
        stats_engine.storage.clear_all_data()
        
        result = stats_engine.aggregate_metrics(metric="power")
        assert "error" in result
        assert "No activities found" in result["error"]
    
    def test_aggregate_metrics_with_data(self, stats_engine):
        """Test aggregation with sample data"""
        storage = stats_engine.storage
        
        # Store activities with power data
        for i in range(3):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now() - timedelta(days=i)
            activity.duration = 3600.0
            activity.total_distance = 10000.0
            parsed_data.activity = activity
            
            # Add records with power data
            records = []
            for j in range(10):
                record = Record()
                record.timestamp = datetime.now() - timedelta(days=i, minutes=j)
                record.power = 200.0 + i * 50 + j * 10  # Varying power values
                record.speed = 10.0 + i + j * 0.1
                records.append(record)
            parsed_data.records = records
            
            storage.store_activity(parsed_data, username="test_user")
        
        # Test power aggregation
        result = stats_engine.aggregate_metrics(metric="power", activity_type="cycling")
        assert "error" not in result
        assert result["metric"] == "power"
        assert result["count"] == 30  # 3 activities * 10 records each
        assert result["min"] >= 200.0
        assert result["max"] > 200.0
        assert result["mean"] > 200.0
        
        # Test speed aggregation
        result = stats_engine.aggregate_metrics(metric="speed", activity_type="cycling")
        assert "error" not in result
        assert result["metric"] == "speed"
        assert result["count"] == 30
    
    def test_compare_activities(self, stats_engine):
        """Test activity comparison"""
        storage = stats_engine.storage
        
        # Store multiple activities
        activity_ids = []
        for i in range(3):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now() - timedelta(days=i)
            activity.duration = 3600.0 * (i + 1)  # Different durations
            activity.total_distance = 10000.0 * (i + 1)  # Different distances
            parsed_data.activity = activity
            
            # Add records
            records = []
            for j in range(5):
                record = Record()
                record.timestamp = datetime.now() - timedelta(days=i, minutes=j)
                record.power = 200.0 + i * 50
                record.speed = 10.0 + i * 2
                records.append(record)
            parsed_data.records = records
            
            activity_id = storage.store_activity(parsed_data, username="test_user")
            activity_ids.append(activity_id)
        
        # Compare activities
        result = stats_engine.compare_activities(activity_ids)
        assert "error" not in result
        assert len(result) == 4  # 3 activities + summary
        assert f"activity_{activity_ids[0]}" in result
        assert f"activity_{activity_ids[1]}" in result
        assert f"activity_{activity_ids[2]}" in result
        assert "summary" in result
        
        # Check summary
        summary = result["summary"]
        assert "duration_seconds_min" in summary
        assert "duration_seconds_max" in summary
        assert "total_distance_meters_min" in summary
        assert "total_distance_meters_max" in summary
    
    def test_compare_activities_insufficient_ids(self, stats_engine):
        """Test comparison with insufficient activity IDs"""
        result = stats_engine.compare_activities([1])  # Only one activity
        assert "error" in result
        assert "At least 2 activity IDs required" in result["error"]
        
        result = stats_engine.compare_activities([])  # No activities
        assert "error" in result
    
    def test_get_time_series_trends(self, stats_engine):
        """Test time series trend analysis"""
        storage = stats_engine.storage
        
        # Store activities on different days with explicit dates
        base_date = datetime(2023, 6, 15)  # Use a fixed base date
        for i in range(5):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = base_date + timedelta(days=i)  # Days 15, 16, 17, 18, 19
            activity.duration = 3600.0
            parsed_data.activity = activity
            
            # Add records with power data - increasing with i
            records = []
            for j in range(3):
                record = Record()
                record.timestamp = base_date + timedelta(days=i, hours=10 + j)
                record.power = 200.0 + i * 20  # Power increases with each day (i)
                records.append(record)
            parsed_data.records = records
            
            storage.store_activity(parsed_data, username="test_user")
        
        # Test daily trends
        result = stats_engine.get_time_series_trends(
            metric="power",
            activity_type="cycling",
            time_window="daily",
            start_date="2023-06-15",
            end_date="2023-06-19"
        )
        assert "error" not in result
        assert result["metric"] == "power"
        assert result["time_window"] == "daily"
        assert "data" in result
        assert len(result["data"]) == 5  # 5 days
        
        # Check that power values increase over time
        daily_data = result["data"]
        # Sort by date and check trend
        sorted_days = sorted(daily_data.keys())
        power_values = [daily_data[day]["mean"] for day in sorted_days]
        # Power should increase from day 15 to day 19
        assert power_values[0] < power_values[-1]  # First day should have lower power than last day
    
    def test_get_activity_summary(self, stats_engine):
        """Test activity summary generation"""
        storage = stats_engine.storage
        
        # Store an activity with comprehensive data
        parsed_data = ParsedFITData()
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        activity.duration = 7200.0  # 2 hours
        activity.total_distance = 50000.0  # 50 km
        activity.total_ascent = 500.0
        activity.total_descent = 300.0
        parsed_data.activity = activity
        
        # Add sessions
        session = Session()
        session.session_id = 1
        session.sport = "cycling"
        session.sub_sport = "road"
        session.avg_speed = 6.944
        session.max_speed = 15.0
        session.avg_power = 200.0
        session.max_power = 400.0
        parsed_data.sessions = [session]
        
        # Add laps
        lap = Lap()
        lap.lap_id = 1
        lap.intensity = "active"
        lap.total_distance = 25000.0
        lap.avg_power = 220.0
        parsed_data.laps = [lap]
        
        # Add records
        records = []
        for i in range(10):
            record = Record()
            record.timestamp = datetime.now() + timedelta(minutes=i*6)
            record.speed = 7.0 + i * 0.1
            record.power = 150.0 + i * 20.0
            record.heart_rate = 130.0 + i * 2.0
            record.cadence = 80.0 + i * 1.0
            record.altitude = 100.0 + i * 10.0
            records.append(record)
        parsed_data.records = records
        
        activity_id = storage.store_activity(parsed_data, username="test_user")
        
        # Get summary
        result = stats_engine.get_activity_summary(activity_id)
        assert "error" not in result
        assert result["activity_id"] == activity_id
        assert result["activity_type"] == "cycling"
        assert result["total_distance_meters"] == 50000.0
        assert result["duration_seconds"] == 7200.0
        
        # Check calculated metrics
        assert "avg_speed_kph" in result
        assert result["avg_speed_kph"] > 0
        
        # Check record statistics
        assert "speed_min" in result
        assert "speed_max" in result
        assert "speed_mean" in result
        assert "power_min" in result
        assert "power_max" in result
        
        # Check session and lap data
        assert "sessions" in result
        assert len(result["sessions"]) == 1
        assert "laps" in result
        assert len(result["laps"]) == 1
    
    def test_get_bike_specific_metrics(self, stats_engine):
        """Test bike-specific metrics extraction"""
        storage = stats_engine.storage
        
        # Store an activity with bike data
        parsed_data = ParsedFITData()
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        activity.duration = 3600.0
        parsed_data.activity = activity
        
        # Add records with bike metrics
        records = []
        for i in range(10):
            record = Record()
            record.timestamp = datetime.now() + timedelta(minutes=i)
            record.power = 200.0 + i * 20.0
            record.cadence = 80.0 + i * 2.0
            record.speed = 10.0 + i * 0.5
            record.heart_rate = 140.0 + i * 2.0
            record.position_lat = 45.0 + i * 0.01
            record.position_long = -75.0 + i * 0.01
            record.altitude = 100.0 + i * 10.0
            records.append(record)
        parsed_data.records = records
        
        activity_id = storage.store_activity(parsed_data, username="test_user")
        
        # Get bike metrics
        result = stats_engine.get_bike_specific_metrics(activity_id)
        assert "error" not in result
        assert result["activity_id"] == activity_id
        assert result["activity_type"] == "cycling"
        
        # Check power metrics
        assert "power" in result
        assert "avg_watts" in result["power"]
        assert "max_watts" in result["power"]
        assert result["power"]["avg_watts"] > 200.0
        
        # Check cadence metrics
        assert "cadence" in result
        assert "avg_rpm" in result["cadence"]
        assert result["cadence"]["avg_rpm"] > 80.0
        
        # Check speed metrics
        assert "speed" in result
        assert "avg_kph" in result["speed"]
        assert result["speed"]["avg_kph"] > 0
        
        # Check heart rate metrics
        assert "heart_rate" in result
        assert "avg_bpm" in result["heart_rate"]
        assert result["heart_rate"]["avg_bpm"] > 140.0
        
        # Check GPS metrics
        assert "gps" in result
        assert result["gps"]["has_gps"] is True
        
        # Check altitude metrics
        assert "altitude" in result
        assert "ascent_meters" in result["altitude"]


class TestStatsEngineIntegration:
    """Integration tests for StatsEngine"""
    
    def test_full_stats_workflow(self):
        """Test complete stats workflow"""
        storage = DataStorage("sqlite:///:memory:")
        stats = StatsEngine(storage)
        
        try:
            # Clear any existing data
            storage.clear_all_data()
            
            # Store multiple activities with different metrics
            activity_ids = []
            for i in range(3):
                parsed_data = ParsedFITData()
                activity = Activity()
                activity.activity_type = "cycling"
                activity.start_time = datetime(2023, 6, 15 + i, 10, 0, 0)
                activity.duration = 3600.0 * (i + 1)
                activity.total_distance = 10000.0 * (i + 1)
                parsed_data.activity = activity
                
                # Add records
                records = []
                for j in range(20):
                    record = Record()
                    record.timestamp = datetime(2023, 6, 15 + i, 10, 0, 0) + timedelta(minutes=j)
                    record.power = 150.0 + i * 50 + j * 5
                    record.speed = 8.0 + i * 2 + j * 0.1
                    record.heart_rate = 130.0 + i * 10 + j * 1
                    record.cadence = 70.0 + i * 10 + j * 0.5
                    records.append(record)
                parsed_data.records = records
                
                activity_id = storage.store_activity(parsed_data, username="cyclist1")
                activity_ids.append(activity_id)
            
            # Test aggregation
            power_stats = stats.aggregate_metrics(
                user_id=None,
                start_date="2023-06-15",
                end_date="2023-06-18",
                metric="power",
                activity_type="cycling"
            )
            assert "error" not in power_stats
            assert power_stats["count"] == 60  # 3 activities * 20 records each
            assert power_stats["min"] >= 150.0
            assert power_stats["max"] > 150.0
            
            # Test comparison
            comparison = stats.compare_activities(activity_ids)
            assert "error" not in comparison
            assert len(comparison) == 4  # 3 activities + summary
            
            # Test time series trends
            trends = stats.get_time_series_trends(
                user_id=None,
                start_date="2023-06-15",
                end_date="2023-06-18",
                metric="power",
                activity_type="cycling",
                time_window="daily"
            )
            assert "error" not in trends
            assert len(trends["data"]) == 3  # 3 days
            
            # Test individual activity summary
            for activity_id in activity_ids:
                summary = stats.get_activity_summary(activity_id)
                assert "error" not in summary
                assert summary["activity_id"] == activity_id
                assert summary["activity_type"] == "cycling"
                
                # Test bike-specific metrics
                bike_metrics = stats.get_bike_specific_metrics(activity_id)
                assert "error" not in bike_metrics
                assert bike_metrics["activity_id"] == activity_id
                assert "power" in bike_metrics
                assert "cadence" in bike_metrics
            
            print("Full stats workflow test passed!")
            
        finally:
            storage.close()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
