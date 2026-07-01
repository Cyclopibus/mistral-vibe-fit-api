"""
Tests for the Litestar API
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta
from litestar.testing import TestClient
from src.api.main import app
from src.services.storage import DataStorage
from src.parsers.fit_parser import ParsedFITData, Activity, DeviceInfo, Record, Session, Lap


@pytest.fixture
def test_client():
    """Create a test client for the API"""
    # Clear any existing data first
    storage = DataStorage()
    storage.clear_all_data()
    storage.close()
    
    with TestClient(app) as client:
        yield client


class TestAPIEndpoints:
    """Test cases for API endpoints"""
    
    def test_upload_endpoint(self, test_client):
        """Test the /upload endpoint"""
        # Test with invalid file
        response = test_client.post(
            "/upload",
            files={"file": ("test.fit", b"This is not a valid FIT file")}
        )
        
        # Should return 400 for invalid file
        assert response.status_code == 400
        assert "Error" in response.json()["detail"]
    
    def test_activities_list_endpoint(self, test_client):
        """Test the /activities endpoint"""
        # First, we need to store some activities through the storage directly
        storage = DataStorage()
        
        try:
            # Store a test activity
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now()
            activity.duration = 3600.0
            activity.total_distance = 10000.0
            parsed_data.activity = activity
            
            # Add some records
            records = []
            for i in range(5):
                record = Record()
                record.timestamp = datetime.now() + timedelta(minutes=i)
                record.power = 200.0 + i * 10
                record.speed = 10.0 + i * 0.5
                records.append(record)
            parsed_data.records = records
            
            activity_id = storage.store_activity(parsed_data, username="test_user")
            
            # Now test the API endpoint
            response = test_client.get("/activities")
            assert response.status_code == 200
            
            data = response.json()
            assert "activities" in data
            assert "total_count" in data
            assert len(data["activities"]) >= 1
            
            # Check that our activity is in the list
            activity_ids = [act["id"] for act in data["activities"]]
            assert activity_id in activity_ids
            
        finally:
            storage.close()
    
    def test_activities_detail_endpoint(self, test_client):
        """Test the /activities/{id} endpoint"""
        storage = DataStorage()
        
        try:
            # Store a test activity
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now()
            activity.duration = 3600.0
            activity.total_distance = 10000.0
            parsed_data.activity = activity
            
            # Add some records
            records = []
            for i in range(3):
                record = Record()
                record.timestamp = datetime.now() + timedelta(minutes=i)
                record.power = 200.0 + i * 10
                record.speed = 10.0 + i * 0.5
                records.append(record)
            parsed_data.records = records
            
            activity_id = storage.store_activity(parsed_data, username="test_user")
            
            # Test the API endpoint
            response = test_client.get(f"/activities/{activity_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert "activity" in data
            assert "sessions" in data
            assert "laps" in data
            assert "records" in data
            assert data["activity"]["activity_type"] == "cycling"
            assert len(data["records"]) == 3
            
            # Test with non-existent activity
            response = test_client.get("/activities/99999")
            assert response.status_code == 404
            
        finally:
            storage.close()
    
    def test_stats_endpoint(self, test_client):
        """Test the /stats endpoint"""
        storage = DataStorage()
        
        try:
            # Store a test activity with power data
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now()
            activity.duration = 3600.0
            parsed_data.activity = activity
            
            # Add records with power data
            records = []
            for i in range(10):
                record = Record()
                record.timestamp = datetime.now() + timedelta(minutes=i)
                record.power = 200.0 + i * 10
                records.append(record)
            parsed_data.records = records
            
            storage.store_activity(parsed_data, username="test_user")
            
            # Test the API endpoint
            response = test_client.get("/stats?metric=power&activity_type=cycling")
            assert response.status_code == 200
            
            data = response.json()
            assert "metric" in data
            assert "statistics" in data
            assert data["metric"] == "power"
            assert "count" in data["statistics"]
            assert "min" in data["statistics"]
            assert "max" in data["statistics"]
            assert "mean" in data["statistics"]
            
        finally:
            storage.close()
    
    def test_compare_endpoint(self, test_client):
        """Test the /compare endpoint"""
        storage = DataStorage()
        
        try:
            # Store multiple test activities
            activity_ids = []
            for i in range(3):
                parsed_data = ParsedFITData()
                activity = Activity()
                activity.activity_type = "cycling"
                activity.start_time = datetime.now() - timedelta(days=i)
                activity.duration = 3600.0 * (i + 1)
                parsed_data.activity = activity
                
                # Add records
                records = []
                for j in range(5):
                    record = Record()
                    record.timestamp = datetime.now() - timedelta(days=i, minutes=j)
                    record.power = 200.0 + i * 50
                    records.append(record)
                parsed_data.records = records
                
                activity_id = storage.store_activity(parsed_data, username="test_user")
                activity_ids.append(activity_id)
            
            # Test the API endpoint
            ids_str = ",".join(str(id) for id in activity_ids)
            response = test_client.get(f"/compare?activity_ids={ids_str}")
            assert response.status_code == 200
            
            data = response.json()
            assert "comparison" in data
            assert len(data["comparison"]) == 4  # 3 activities + summary
            
            # Test with insufficient IDs
            response = test_client.get("/compare?activity_ids=1")
            assert response.status_code == 400
            
        finally:
            storage.close()
    
    def test_export_endpoint(self, test_client):
        """Test the /export/{id} endpoint"""
        storage = DataStorage()
        
        try:
            # Store a test activity
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now()
            parsed_data.activity = activity
            
            # Add records
            records = []
            for i in range(5):
                record = Record()
                record.timestamp = datetime.now() + timedelta(minutes=i)
                record.power = 200.0 + i * 10
                record.speed = 10.0 + i * 0.5
                records.append(record)
            parsed_data.records = records
            
            activity_id = storage.store_activity(parsed_data, username="test_user")
            
            # Test CSV export
            response = test_client.get(f"/export/{activity_id}?format=csv")
            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]
            assert "activity_" in response.headers["content-disposition"]
            assert ".csv" in response.headers["content-disposition"]
            
            # Test JSON export
            response = test_client.get(f"/export/{activity_id}?format=json")
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]
            assert "activity_" in response.headers["content-disposition"]
            assert ".json" in response.headers["content-disposition"]
            
            # Test with non-existent activity
            response = test_client.get("/export/99999")
            assert response.status_code == 404
            
        finally:
            storage.close()
    
    def test_bike_metrics_endpoint(self, test_client):
        """Test the /bike-metrics/{id} endpoint"""
        storage = DataStorage()
        
        try:
            # Store a test activity with bike metrics
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
                record.power = 200.0 + i * 20
                record.cadence = 80.0 + i * 2
                record.speed = 10.0 + i * 0.5
                record.heart_rate = 140.0 + i * 2
                records.append(record)
            parsed_data.records = records
            
            activity_id = storage.store_activity(parsed_data, username="test_user")
            
            # Test the API endpoint
            response = test_client.get(f"/bike-metrics/{activity_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert "activity_id" in data
            assert "activity_type" in data
            assert data["activity_type"] == "cycling"
            assert "power" in data
            assert "cadence" in data
            assert "speed" in data
            assert "heart_rate" in data
            
            # Test with non-existent activity
            response = test_client.get("/bike-metrics/99999")
            assert response.status_code == 404
            
        finally:
            storage.close()
    
    def test_trends_endpoint(self, test_client):
        """Test the /trends endpoint"""
        storage = DataStorage()
        
        try:
            # Store activities on different days
            base_date = datetime(2023, 6, 15)
            for i in range(3):
                parsed_data = ParsedFITData()
                activity = Activity()
                activity.activity_type = "cycling"
                activity.start_time = base_date + timedelta(days=i)
                activity.duration = 3600.0
                parsed_data.activity = activity
                
                # Add records with power data
                records = []
                for j in range(5):
                    record = Record()
                    record.timestamp = base_date + timedelta(days=i, minutes=j)
                    record.power = 200.0 + i * 20
                    records.append(record)
                parsed_data.records = records
                
                storage.store_activity(parsed_data, username="test_user")
            
            # Test the API endpoint
            response = test_client.get(
                "/trends?metric=power&activity_type=cycling&start_date=2023-06-15&end_date=2023-06-18&time_window=daily"
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "metric" in data
            assert "time_window" in data
            assert "data" in data
            assert data["metric"] == "power"
            assert data["time_window"] == "daily"
            
        finally:
            storage.close()
    
    def test_plot_endpoint(self, test_client):
        """Test the /plot/{id} endpoint"""
        storage = DataStorage()
        
        try:
            # Store a test activity
            parsed_data = ParsedFITData()
            activity = Activity()
            activity.activity_type = "cycling"
            activity.start_time = datetime.now()
            parsed_data.activity = activity
            
            # Add records
            records = []
            for i in range(10):
                record = Record()
                record.timestamp = datetime.now() + timedelta(minutes=i)
                record.power = 200.0 + i * 10
                records.append(record)
            parsed_data.records = records
            
            activity_id = storage.store_activity(parsed_data, username="test_user")
            
            # Test the API endpoint
            response = test_client.get(f"/plot/{activity_id}?metric=power")
            assert response.status_code == 200
            assert "image/png" in response.headers["content-type"]
            assert "activity_" in response.headers["content-disposition"]
            assert ".png" in response.headers["content-disposition"]
            
            # Test with non-existent activity
            response = test_client.get("/plot/99999")
            assert response.status_code == 404
            
        finally:
            storage.close()


class TestAPIIntegration:
    """Integration tests for the API"""
    
    def test_full_api_workflow(self):
        """Test complete API workflow"""
        storage = DataStorage()
        
        try:
            # Clear any existing data
            storage.clear_all_data()
            
            with TestClient(app) as client:
                # Step 1: Store some activities directly (since file upload is complex to test)
                activity_ids = []
                for i in range(3):
                    parsed_data = ParsedFITData()
                    activity = Activity()
                    activity.activity_type = "cycling"
                    activity.start_time = datetime(2023, 6, 15 + i, 10, 0, 0)
                    activity.duration = 3600.0 * (i + 1)
                    activity.total_distance = 10000.0 * (i + 1)
                    parsed_data.activity = activity
                    
                    # Add sessions
                    session = Session()
                    session.session_id = 1
                    session.sport = "cycling"
                    session.avg_power = 200.0 + i * 50
                    parsed_data.sessions = [session]
                    
                    # Add laps
                    lap = Lap()
                    lap.lap_id = 1
                    lap.intensity = "active"
                    lap.avg_power = 220.0 + i * 50
                    parsed_data.laps = [lap]
                    
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
                
                # Step 2: Test listing activities
                response = client.get("/activities")
                assert response.status_code == 200
                data = response.json()
                assert len(data["activities"]) >= 3
                
                # Step 3: Test getting individual activity
                for activity_id in activity_ids:
                    response = client.get(f"/activities/{activity_id}")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["activity"]["activity_type"] == "cycling"
                
                # Step 4: Test statistics
                response = client.get("/stats?metric=power&activity_type=cycling")
                assert response.status_code == 200
                data = response.json()
                assert data["metric"] == "power"
                assert data["statistics"]["count"] == 60  # 3 activities * 20 records
                
                # Step 5: Test comparison
                ids_str = ",".join(str(id) for id in activity_ids)
                response = client.get(f"/compare?activity_ids={ids_str}")
                assert response.status_code == 200
                data = response.json()
                assert len(data["comparison"]) == 4  # 3 activities + summary
                
                # Step 6: Test bike metrics
                for activity_id in activity_ids:
                    response = client.get(f"/bike-metrics/{activity_id}")
                    assert response.status_code == 200
                    data = response.json()
                    assert "power" in data
                    assert "cadence" in data
                
                # Step 7: Test trends
                response = client.get(
                    "/trends?metric=power&activity_type=cycling&start_date=2023-06-15&end_date=2023-06-18&time_window=daily"
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["data"]) == 3  # 3 days
                
                # Step 8: Test export
                for activity_id in activity_ids:
                    response = client.get(f"/export/{activity_id}?format=csv")
                    assert response.status_code == 200
                    assert "text/csv" in response.headers["content-type"]
                    
                    response = client.get(f"/export/{activity_id}?format=json")
                    assert response.status_code == 200
                    assert "application/json" in response.headers["content-type"]
                
                # Step 9: Test plots
                for activity_id in activity_ids:
                    response = client.get(f"/plot/{activity_id}?metric=power")
                    assert response.status_code == 200
                    assert "image/png" in response.headers["content-type"]
                
                print("Full API workflow test passed!")
                
        finally:
            storage.close()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
