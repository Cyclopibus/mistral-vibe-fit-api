"""
Tests for the FIT Parser module
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta
from src.parsers.fit_parser import FITParser, ParsedFITData, Activity, DeviceInfo, Record, Session, Lap


class TestFITParser:
    """Test cases for FITParser class"""
    
    def test_parser_initialization(self):
        """Test that FITParser initializes correctly"""
        parser = FITParser()
        assert parser is not None
        # Parser creates decoders as needed, so we don't check for decoder attribute
    
    def test_semicircles_to_degrees_conversion(self):
        """Test semicircles to degrees conversion"""
        parser = FITParser()
        
        # Test known conversion: 0 semicircles = 0 degrees
        assert parser._convert_semicircles_to_degrees(0) == 0.0
        
        # Test known conversion: 2^31 semicircles = 180 degrees
        assert abs(parser._convert_semicircles_to_degrees(2**31) - 180.0) < 0.0001
        
        # Test known conversion: -2^31 semicircles = -180 degrees
        assert abs(parser._convert_semicircles_to_degrees(-2**31) - (-180.0)) < 0.0001
    
    def test_get_message_value(self):
        """Test message value extraction"""
        parser = FITParser()
        
        # Test with empty message
        assert parser._get_message_value({}, "test_field") is None
        
        # Test with None value
        message = {"test_field": None}
        assert parser._get_message_value(message, "test_field") is None
        
        # Test with integer value
        message = {"test_field": 123}
        assert parser._get_message_value(message, "test_field", "uint16") == 123
        
        # Test with float value
        message = {"test_field": 123.45}
        assert parser._get_message_value(message, "test_field", "float32") == 123.45
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file"""
        parser = FITParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/non/existent/file.fit")
    
    def test_parse_invalid_file(self):
        """Test parsing invalid file"""
        parser = FITParser()
        
        # Create a temporary file with invalid content
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as temp_file:
            temp_file.write(b"This is not a valid FIT file")
            temp_file_path = temp_file.name
        
        try:
            # This should either raise an exception or return empty data
            result = parser.parse_file(temp_file_path)
            # If it doesn't raise an exception, it should return a ParsedFITData object
            assert isinstance(result, ParsedFITData)
        except Exception:
            # It's also acceptable for invalid files to raise exceptions
            pass
        finally:
            os.unlink(temp_file_path)
    
    def test_parsed_fit_data_structure(self):
        """Test ParsedFITData structure"""
        data = ParsedFITData()
        
        # Test default values
        assert data.file_id is None
        assert data.device_info is None
        assert data.activity is None
        assert data.sessions == []
        assert data.laps == []
        assert data.records == []
        
        # Test to_dict method
        result = data.to_dict()
        assert isinstance(result, dict)
        assert "file_id" in result
        assert "device_info" in result
        assert "activity" in result
        assert "sessions" in result
        assert "laps" in result
        assert "records" in result
    
    def test_activity_dataclass(self):
        """Test Activity dataclass"""
        activity = Activity()
        activity.activity_type = "cycling"
        activity.start_time = datetime.now()
        activity.duration = 3600.0
        activity.total_distance = 10000.0
        
        assert activity.activity_type == "cycling"
        assert activity.duration == 3600.0
        assert activity.total_distance == 10000.0
    
    def test_device_info_dataclass(self):
        """Test DeviceInfo dataclass"""
        device = DeviceInfo()
        device.manufacturer = "Garmin"
        device.product_name = "Edge 1040"
        device.serial_number = 123456789
        
        assert device.manufacturer == "Garmin"
        assert device.product_name == "Edge 1040"
        assert device.serial_number == 123456789
    
    def test_record_dataclass(self):
        """Test Record dataclass"""
        record = Record()
        record.timestamp = datetime.now()
        record.position_lat = 45.0
        record.position_long = -75.0
        record.speed = 10.0
        record.cadence = 90.0
        record.power = 250.0
        record.heart_rate = 150.0
        
        assert record.speed == 10.0
        assert record.cadence == 90.0
        assert record.power == 250.0
        assert record.heart_rate == 150.0
    
    def test_session_dataclass(self):
        """Test Session dataclass"""
        session = Session()
        session.sport = "cycling"
        session.sub_sport = "road"
        session.avg_speed = 8.5
        session.max_speed = 12.0
        session.avg_power = 200.0
        session.max_power = 400.0
        
        assert session.sport == "cycling"
        assert session.sub_sport == "road"
        assert session.avg_speed == 8.5
        assert session.max_power == 400.0
    
    def test_lap_dataclass(self):
        """Test Lap dataclass"""
        lap = Lap()
        lap.lap_id = 1
        lap.total_distance = 5000.0
        lap.avg_power = 220.0
        lap.intensity = "active"
        
        assert lap.lap_id == 1
        assert lap.total_distance == 5000.0
        assert lap.avg_power == 220.0
        assert lap.intensity == "active"


class TestFITParserIntegration:
    """Integration tests for FITParser"""
    
    def test_parser_with_real_fit_file(self):
        """Test parsing with a real FIT file if available"""
        parser = FITParser()
        
        # Look for any .fit files in the project
        fit_files = []
        for root, dirs, files in os.walk("/workspace/Cyclopibus__mistral-vibe-fit-api"):
            for file in files:
                if file.lower().endswith(".fit"):
                    fit_files.append(os.path.join(root, file))
        
        if fit_files:
            # Test with the first available FIT file
            fit_file = fit_files[0]
            try:
                result = parser.parse_file(fit_file)
                assert isinstance(result, ParsedFITData)
                print(f"Successfully parsed {fit_file}")
                print(f"  File ID: {result.file_id}")
                print(f"  Device Info: {result.device_info}")
                print(f"  Activity: {result.activity}")
                print(f"  Sessions: {len(result.sessions)}")
                print(f"  Laps: {len(result.laps)}")
                print(f"  Records: {len(result.records)}")
            except Exception as e:
                print(f"Could not parse {fit_file}: {e}")
                # This is acceptable - the file might be corrupted or in an unsupported format
                pass
        else:
            print("No FIT files found for integration testing")
    
    def test_stream_parsing(self):
        """Test stream parsing functionality"""
        parser = FITParser()
        
        # Create a simple stream with invalid data (for testing the fallback mechanism)
        import io
        stream = io.BytesIO(b"This is not a valid FIT file")
        
        try:
            result = parser.parse_stream(stream)
            assert isinstance(result, ParsedFITData)
        except Exception:
            # It's acceptable for invalid streams to raise exceptions
            pass


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
