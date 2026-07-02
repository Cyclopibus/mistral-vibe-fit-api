"""
Tests for the Storage Service
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta
from src.services.storage import DataStorage
from src.parsers.fit_parser import ParsedFITData, Activity, DeviceInfo, Record, Session, Lap


@pytest.fixture
def storage():
    """Create a temporary storage instance for testing with isolated database"""
    # Use a unique in-memory database for each test
    storage = DataStorage("sqlite:///:memory:")
    yield storage
    storage.close()


class TestDataStorage:
    """Test cases for DataStorage class"""
    
    def test_storage_initialization(self, storage):
        """Test that DataStorage initializes correctly"""
        assert storage is not None
        assert hasattr(storage, 'engine')
        assert hasattr(storage, 'Session')
    
    def test_store_and_retrieve_activity(self, storage):
        """Test storing and retrieving an activity"""
        # Create sample parsed data
        parsed_data = ParsedFITData()
        
        # Create activity
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        activity.duration = 3600.0
        activity.total_distance = 10000.0
        parsed_data.activity = activity
        
        # Create device info
        device_info = DeviceInfo()
        device_info.manufacturer = "Garmin"
        device_info.product_name = "Edge 1040"
        device_info.serial_number = 123456789
        parsed_data.device_info = device_info
        
        # Add some records
        record1 = Record()
        record1.timestamp = datetime.now()
        record1.speed = 10.0
        record1.power = 250.0
        record1.heart_rate = 150.0
        
        record2 = Record()
        record2.timestamp = datetime.now() + timedelta(seconds=1)
        record2.speed = 12.0
        record2.power = 300.0
        record2.heart_rate = 160.0
        
        parsed_data.records = [record1, record2]
        
        # Store the activity
        activity_id = storage.store_activity(parsed_data, username="test_user")
        assert activity_id is not None
        assert isinstance(activity_id, int)
        
        # Retrieve the activity
        retrieved = storage.get_activity(activity_id)
        assert retrieved is not None
        assert retrieved["activity"]["activity_type"] == "cycling"
        assert retrieved["activity"]["total_distance"] == 10000.0
        assert len(retrieved["records"]) == 2
        assert retrieved["records"][0]["speed"] == 10.0
        assert retrieved["records"][1]["power"] == 300.0
    
    def test_query_activities(self, storage):
        """Test querying activities with filters"""
        # Clear any existing data first
        storage.clear_all_data()
        
        # Store multiple activities
        for i in range(5):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling" if i % 2 == 0 else "running"
            activity.start_time = datetime.now() - timedelta(days=i)
            activity.duration = 3600.0 * (i + 1)
            parsed_data.activity = activity
            
            storage.store_activity(parsed_data, username="test_user")
        
        # Query all activities
        activities = storage.query_activities()
        assert len(activities) == 5
        
        # Query by activity type
        cycling_activities = storage.query_activities(activity_type="cycling")
        assert len(cycling_activities) == 3
        
        running_activities = storage.query_activities(activity_type="running")
        assert len(running_activities) == 2
    
    def test_query_activities_with_date_filter(self, storage):
        """Test querying activities with date filters"""
        # Clear any existing data first
        storage.clear_all_data()
        
        # Store activities with different dates
        base_date = datetime.now().date()
        
        for i in range(5):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime(base_date.year, base_date.month, base_date.day - i, 10, 0, 0)
            parsed_data.activity = activity
            
            storage.store_activity(parsed_data, username="test_user")
        
        # Query with date range
        start_date = (base_date - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
        
        activities = storage.query_activities(start_date=start_date, end_date=end_date)
        assert len(activities) == 3  # Days -3, -2, -1
    
    def test_delete_activity(self, storage):
        """Test deleting an activity"""
        # Store an activity
        parsed_data = ParsedFITData()
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        parsed_data.activity = activity
        
        activity_id = storage.store_activity(parsed_data, username="test_user")
        
        # Verify it exists
        retrieved = storage.get_activity(activity_id)
        assert retrieved is not None
        
        # Delete it
        result = storage.delete_activity(activity_id)
        assert result is True
        
        # Verify it's gone
        retrieved = storage.get_activity(activity_id)
        assert retrieved is None
    
    def test_get_activity_count(self, storage):
        """Test getting activity count"""
        # Clear any existing data first
        storage.clear_all_data()
        
        # Store some activities
        for i in range(3):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now() - timedelta(days=i)
            parsed_data.activity = activity
            
            storage.store_activity(parsed_data, username="test_user")
        
        count = storage.get_activity_count()
        assert count == 3
    
    def test_device_management(self, storage):
        """Test device management"""
        # Store activity with device info
        parsed_data = ParsedFITData()
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        parsed_data.activity = activity
        
        device_info = DeviceInfo()
        device_info.manufacturer = "Garmin"
        device_info.product_name = "Edge 1040"
        device_info.serial_number = 123456789
        parsed_data.device_info = device_info
        
        activity_id = storage.store_activity(parsed_data, username="test_user")
        
        # Get the activity to find the device ID
        activity_data = storage.get_activity(activity_id)
        device_id = activity_data["activity"]["device_id"]
        
        # Get device info
        device_info = storage.get_device_info(device_id)
        assert device_info is not None
        assert device_info["manufacturer"] == "Garmin"
        assert device_info["product_name"] == "Edge 1040"
        assert device_info["serial_number"] == 123456789
    
    def test_user_management(self, storage):
        """Test user management"""
        # Store activity with user
        parsed_data = ParsedFITData()
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        parsed_data.activity = activity
        
        activity_id = storage.store_activity(parsed_data, username="test_user", email="test@example.com")
        
        # Get the activity to find the user ID
        activity_data = storage.get_activity(activity_id)
        user_id = activity_data["activity"]["user_id"]
        
        # Get user info
        user_info = storage.get_user_info(user_id)
        assert user_info is not None
        assert user_info["username"] == "test_user"
        assert user_info["email"] == "test@example.com"
    
    def test_pagination(self, storage):
        """Test pagination in activity queries"""
        # Clear any existing data first
        storage.clear_all_data()
        
        # Store many activities
        for i in range(10):
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now() - timedelta(days=i)
            parsed_data.activity = activity
            
            storage.store_activity(parsed_data, username="test_user")
        
        # Query with limit and offset
        page1 = storage.query_activities(limit=3, offset=0)
        assert len(page1) == 3
        
        page2 = storage.query_activities(limit=3, offset=3)
        assert len(page2) == 3
        
        # Verify different activities
        assert page1[0]["id"] != page2[0]["id"]


class TestDataStorageIntegration:
    """Integration tests for DataStorage"""
    
    def test_full_workflow(self):
        """Test complete workflow from parsing to storage and retrieval"""
        storage = DataStorage("sqlite:///:memory:")
        
        try:
            # Clear any existing data
            storage.clear_all_data()
            
            # Create sample parsed data (simulating what would come from FIT parser)
            parsed_data = ParsedFITData()
            
            # Activity
            activity = Activity()
            activity.activity_id = 12345
            activity.activity_type = "cycling"
            activity.start_time = datetime(2023, 6, 15, 10, 0, 0)
            activity.duration = 7200.0  # 2 hours
            activity.total_distance = 50000.0  # 50 km
            activity.total_ascent = 500.0
            activity.total_descent = 300.0
            activity.num_sessions = 1
            activity.num_laps = 2
            parsed_data.activity = activity
            
            # Device info
            device_info = DeviceInfo()
            device_info.manufacturer = "Garmin"
            device_info.product_name = "Edge 1040"
            device_info.serial_number = 123456789
            device_info.software_version = 1.0
            parsed_data.device_info = device_info
            
            # Sessions
            session = Session()
            session.session_id = 1
            session.start_time = datetime(2023, 6, 15, 10, 0, 0)
            session.total_elapsed_time = 7200.0
            session.total_timer_time = 7200.0
            session.total_distance = 50000.0
            session.avg_speed = 6.944  # 50km / 2h
            session.max_speed = 15.0
            session.avg_heart_rate = 140.0
            session.max_heart_rate = 180.0
            session.avg_cadence = 85.0
            session.max_cadence = 110.0
            session.avg_power = 200.0
            session.max_power = 400.0
            session.sport = "cycling"
            session.sub_sport = "road"
            parsed_data.sessions = [session]
            
            # Laps
            lap1 = Lap()
            lap1.lap_id = 1
            lap1.start_time = datetime(2023, 6, 15, 10, 0, 0)
            lap1.total_distance = 25000.0
            lap1.avg_power = 220.0
            lap1.intensity = "active"
            
            lap2 = Lap()
            lap2.lap_id = 2
            lap2.start_time = datetime(2023, 6, 15, 11, 0, 0)
            lap2.total_distance = 25000.0
            lap2.avg_power = 180.0
            lap2.intensity = "active"
            
            parsed_data.laps = [lap1, lap2]
            
            # Records (time-series data)
            records = []
            for i in range(10):
                record = Record()
                record.timestamp = datetime(2023, 6, 15, 10, 0, 0) + timedelta(minutes=i*6)
                record.position_lat = 45.0 + i * 0.01
                record.position_long = -75.0 + i * 0.01
                record.distance = 5000.0 * i
                record.speed = 7.0 + i * 0.1
                record.cadence = 80.0 + i * 1.0
                record.power = 150.0 + i * 20.0
                record.heart_rate = 130.0 + i * 2.0
                record.altitude = 100.0 + i * 10.0
                records.append(record)
            
            parsed_data.records = records
            
            # Store the activity
            activity_id = storage.store_activity(parsed_data, username="cyclist1")
            
            # Retrieve and verify
            retrieved = storage.get_activity(activity_id)
            
            assert retrieved["activity"]["activity_type"] == "cycling"
            assert retrieved["activity"]["total_distance"] == 50000.0
            assert retrieved["activity"]["duration"] == 7200.0
            assert len(retrieved["sessions"]) == 1
            assert len(retrieved["laps"]) == 2
            assert len(retrieved["records"]) == 10
            
            # Check session data
            session_data = retrieved["sessions"][0]
            assert session_data["avg_speed"] == 6.944
            assert session_data["sport"] == "cycling"
            
            # Check lap data
            lap_data = retrieved["laps"][0]
            assert lap_data["total_distance"] == 25000.0
            assert lap_data["intensity"] == "active"
            
            # Check record data
            record_data = retrieved["records"][0]
            assert record_data["speed"] == 7.0
            assert record_data["power"] == 150.0
            
            print("Full workflow test passed!")
            
        finally:
            storage.close()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
