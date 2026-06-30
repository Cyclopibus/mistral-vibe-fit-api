"""
FIT Parser Module using the official garmin-fit-sdk

This module provides functionality to parse Garmin FIT files and extract
bike-specific metrics using the official fit-python-sdk.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import tempfile
import io

from garmin_fit_sdk import Decoder, Stream
from garmin_fit_sdk import profile


@dataclass
class DeviceInfo:
    """Device information extracted from FIT file"""
    manufacturer: Optional[str] = None
    product_name: Optional[str] = None
    device_index: Optional[int] = None
    serial_number: Optional[int] = None
    software_version: Optional[float] = None
    hardware_version: Optional[int] = None


@dataclass
class Activity:
    """Activity information extracted from FIT file"""
    activity_id: Optional[int] = None
    activity_type: Optional[str] = None
    start_time: Optional[datetime] = None
    duration: Optional[float] = None  # in seconds
    total_distance: Optional[float] = None  # in meters
    total_ascent: Optional[float] = None  # in meters
    total_descent: Optional[float] = None  # in meters
    num_sessions: Optional[int] = None
    num_laps: Optional[int] = None


@dataclass
class Record:
    """Single record/point from FIT file"""
    timestamp: Optional[datetime] = None
    position_lat: Optional[float] = None  # in semicircles
    position_long: Optional[float] = None  # in semicircles
    distance: Optional[float] = None  # in meters
    speed: Optional[float] = None  # in m/s
    cadence: Optional[float] = None  # in RPM
    power: Optional[float] = None  # in watts
    heart_rate: Optional[float] = None  # in BPM
    altitude: Optional[float] = None  # in meters
    temperature: Optional[float] = None  # in Celsius
    time_from_course: Optional[float] = None  # in seconds


@dataclass
class Session:
    """Session information from FIT file"""
    session_id: Optional[int] = None
    start_time: Optional[datetime] = None
    total_elapsed_time: Optional[float] = None  # in seconds
    total_timer_time: Optional[float] = None  # in seconds
    total_distance: Optional[float] = None  # in meters
    total_ascent: Optional[float] = None  # in meters
    total_descent: Optional[float] = None  # in meters
    avg_speed: Optional[float] = None  # in m/s
    max_speed: Optional[float] = None  # in m/s
    avg_heart_rate: Optional[float] = None  # in BPM
    max_heart_rate: Optional[float] = None  # in BPM
    avg_cadence: Optional[float] = None  # in RPM
    max_cadence: Optional[float] = None  # in RPM
    avg_power: Optional[float] = None  # in watts
    max_power: Optional[float] = None  # in watts
    sport: Optional[str] = None
    sub_sport: Optional[str] = None


@dataclass
class Lap:
    """Lap information from FIT file"""
    lap_id: Optional[int] = None
    start_time: Optional[datetime] = None
    total_elapsed_time: Optional[float] = None  # in seconds
    total_timer_time: Optional[float] = None  # in seconds
    total_distance: Optional[float] = None  # in meters
    total_ascent: Optional[float] = None  # in meters
    total_descent: Optional[float] = None  # in meters
    avg_speed: Optional[float] = None  # in m/s
    max_speed: Optional[float] = None  # in m/s
    avg_heart_rate: Optional[float] = None  # in BPM
    max_heart_rate: Optional[float] = None  # in BPM
    avg_cadence: Optional[float] = None  # in RPM
    max_cadence: Optional[float] = None  # in RPM
    avg_power: Optional[float] = None  # in watts
    max_power: Optional[float] = None  # in watts
    intensity: Optional[str] = None


@dataclass
class ParsedFITData:
    """Complete parsed FIT file data"""
    file_id: Optional[Dict[str, Any]] = None
    device_info: Optional[DeviceInfo] = None
    activity: Optional[Activity] = None
    sessions: List[Session] = field(default_factory=list)
    laps: List[Lap] = field(default_factory=list)
    records: List[Record] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parsed data to dictionary format"""
        return {
            "file_id": self.file_id,
            "device_info": self.device_info.__dict__ if self.device_info else None,
            "activity": self.activity.__dict__ if self.activity else None,
            "sessions": [session.__dict__ for session in self.sessions],
            "laps": [lap.__dict__ for lap in self.laps],
            "records": [record.__dict__ for record in self.records],
        }


class FITParser:
    """
    FIT File Parser using garmin-fit-sdk
    
    This class provides methods to parse FIT files and extract bike-specific metrics.
    """
    
    def __init__(self):
        """Initialize the FIT parser"""
        pass  # We'll create decoders as needed
        
    def _convert_semicircles_to_degrees(self, semicircles: float) -> float:
        """Convert semicircles to degrees"""
        return semicircles * (180.0 / 2**31)
    
    def _get_message_value(self, message, field_name: str, profile_type: str = None):
        """Get value from FIT message with proper type conversion"""
        try:
            if field_name in message:
                value = message[field_name]
                if value is not None:
                    # Handle different profile types
                    if profile_type == "date_time":
                        return datetime(1989, 12, 31) + timedelta(seconds=value)
                    elif profile_type == "sint32" or profile_type == "uint32":
                        return int(value)
                    elif profile_type == "sint16" or profile_type == "uint16":
                        return int(value)
                    elif profile_type == "sint8" or profile_type == "uint8":
                        return int(value)
                    elif profile_type == "float32":
                        return float(value)
                    elif profile_type == "float64":
                        return float(value)
                    elif profile_type == "string":
                        return str(value)
                    else:
                        return value
                return None
            return None
        except Exception:
            return None
    
    def _parse_file_id_message(self, message: Dict) -> Dict[str, Any]:
        """Parse file_id message"""
        file_id = {}
        file_id["type"] = self._get_message_value(message, "type", "uint8")
        file_id["manufacturer"] = self._get_message_value(message, "manufacturer", "uint16")
        file_id["product"] = self._get_message_value(message, "product", "uint16")
        file_id["serial_number"] = self._get_message_value(message, "serial_number", "uint32")
        file_id["time_created"] = self._get_message_value(message, "time_created", "date_time")
        file_id["number"] = self._get_message_value(message, "number", "uint16")
        return file_id
    
    def _parse_device_info_message(self, message: Dict) -> DeviceInfo:
        """Parse device_info message"""
        device_info = DeviceInfo()
        
        # Get manufacturer name
        manufacturer_id = self._get_message_value(message, "manufacturer", "uint16")
        if manufacturer_id is not None:
            try:
                manufacturer = profile.get_manufacturer_name(manufacturer_id)
                device_info.manufacturer = manufacturer
            except:
                device_info.manufacturer = f"Unknown ({manufacturer_id})"
        
        # Get product name
        product_id = self._get_message_value(message, "product", "uint16")
        if product_id is not None and manufacturer_id is not None:
            try:
                product_name = profile.get_product_name(manufacturer_id, product_id)
                device_info.product_name = product_name
            except:
                device_info.product_name = f"Unknown ({product_id})"
        
        device_info.device_index = self._get_message_value(message, "device_index", "uint8")
        device_info.serial_number = self._get_message_value(message, "serial_number", "uint32")
        device_info.software_version = self._get_message_value(message, "software_version", "float32")
        device_info.hardware_version = self._get_message_value(message, "hardware_version", "uint8")
        
        return device_info
    
    def _parse_activity_message(self, message: Dict) -> Activity:
        """Parse activity message"""
        activity = Activity()
        
        activity.activity_id = self._get_message_value(message, "activity_id", "uint32")
        
        # Get activity type
        activity_type_id = self._get_message_value(message, "type", "uint8")
        if activity_type_id is not None:
            try:
                activity_type = profile.get_activity_type_name(activity_type_id)
                activity.activity_type = activity_type
            except:
                activity.activity_type = f"Unknown ({activity_type_id})"
        
        activity.start_time = self._get_message_value(message, "timestamp", "date_time")
        activity.duration = self._get_message_value(message, "total_timer_time", "float32")
        activity.total_distance = self._get_message_value(message, "total_distance", "float32")
        activity.total_ascent = self._get_message_value(message, "total_ascent", "float32")
        activity.total_descent = self._get_message_value(message, "total_descent", "float32")
        activity.num_sessions = self._get_message_value(message, "num_sessions", "uint16")
        activity.num_laps = self._get_message_value(message, "num_laps", "uint16")
        
        return activity
    
    def _parse_session_message(self, message: Dict) -> Session:
        """Parse session message"""
        session = Session()
        
        session.session_id = self._get_message_value(message, "session_id", "uint16")
        session.start_time = self._get_message_value(message, "start_time", "date_time")
        session.total_elapsed_time = self._get_message_value(message, "total_elapsed_time", "float32")
        session.total_timer_time = self._get_message_value(message, "total_timer_time", "float32")
        session.total_distance = self._get_message_value(message, "total_distance", "float32")
        session.total_ascent = self._get_message_value(message, "total_ascent", "float32")
        session.total_descent = self._get_message_value(message, "total_descent", "float32")
        session.avg_speed = self._get_message_value(message, "avg_speed", "float32")
        session.max_speed = self._get_message_value(message, "max_speed", "float32")
        session.avg_heart_rate = self._get_message_value(message, "avg_heart_rate", "uint8")
        session.max_heart_rate = self._get_message_value(message, "max_heart_rate", "uint8")
        session.avg_cadence = self._get_message_value(message, "avg_cadence", "uint8")
        session.max_cadence = self._get_message_value(message, "max_cadence", "uint8")
        session.avg_power = self._get_message_value(message, "avg_power", "uint16")
        session.max_power = self._get_message_value(message, "max_power", "uint16")
        
        # Get sport and sub-sport
        sport_id = self._get_message_value(message, "sport", "uint8")
        if sport_id is not None:
            try:
                session.sport = profile.get_sport_name(sport_id)
            except:
                session.sport = f"Unknown ({sport_id})"
        
        sub_sport_id = self._get_message_value(message, "sub_sport", "uint8")
        if sub_sport_id is not None:
            try:
                session.sub_sport = profile.get_sub_sport_name(sub_sport_id)
            except:
                session.sub_sport = f"Unknown ({sub_sport_id})"
        
        return session
    
    def _parse_lap_message(self, message: Dict) -> Lap:
        """Parse lap message"""
        lap = Lap()
        
        lap.lap_id = self._get_message_value(message, "lap_id", "uint16")
        lap.start_time = self._get_message_value(message, "start_time", "date_time")
        lap.total_elapsed_time = self._get_message_value(message, "total_elapsed_time", "float32")
        lap.total_timer_time = self._get_message_value(message, "total_timer_time", "float32")
        lap.total_distance = self._get_message_value(message, "total_distance", "float32")
        lap.total_ascent = self._get_message_value(message, "total_ascent", "float32")
        lap.total_descent = self._get_message_value(message, "total_descent", "float32")
        lap.avg_speed = self._get_message_value(message, "avg_speed", "float32")
        lap.max_speed = self._get_message_value(message, "max_speed", "float32")
        lap.avg_heart_rate = self._get_message_value(message, "avg_heart_rate", "uint8")
        lap.max_heart_rate = self._get_message_value(message, "max_heart_rate", "uint8")
        lap.avg_cadence = self._get_message_value(message, "avg_cadence", "uint8")
        lap.max_cadence = self._get_message_value(message, "max_cadence", "uint8")
        lap.avg_power = self._get_message_value(message, "avg_power", "uint16")
        lap.max_power = self._get_message_value(message, "max_power", "uint16")
        
        # Get intensity
        intensity_id = self._get_message_value(message, "intensity", "uint8")
        if intensity_id is not None:
            try:
                lap.intensity = profile.get_intensity_name(intensity_id)
            except:
                lap.intensity = f"Unknown ({intensity_id})"
        
        return lap
    
    def _parse_record_message(self, message: Dict) -> Record:
        """Parse record message - contains time-series data"""
        record = Record()
        
        record.timestamp = self._get_message_value(message, "timestamp", "date_time")
        
        # Position data (in semicircles, needs conversion)
        position_lat = self._get_message_value(message, "position_lat", "sint32")
        position_long = self._get_message_value(message, "position_long", "sint32")
        
        if position_lat is not None:
            record.position_lat = self._convert_semicircles_to_degrees(position_lat)
        if position_long is not None:
            record.position_long = self._convert_semicircles_to_degrees(position_long)
        
        record.distance = self._get_message_value(message, "distance", "float32")
        record.speed = self._get_message_value(message, "speed", "float32")
        record.cadence = self._get_message_value(message, "cadence", "uint8")
        record.power = self._get_message_value(message, "power", "uint16")
        record.heart_rate = self._get_message_value(message, "heart_rate", "uint8")
        record.altitude = self._get_message_value(message, "altitude", "float32")
        record.temperature = self._get_message_value(message, "temperature", "float32")
        record.time_from_course = self._get_message_value(message, "time_from_course", "float32")
        
        return record
    
    def _process_messages(self, messages) -> ParsedFITData:
        """Process decoded messages into structured data"""
        parsed_data = ParsedFITData()
        
        for message in messages:
            # Get message name and fields
            message_name = getattr(message, 'name', None)
            if not message_name:
                continue
                
            # Convert message to dictionary
            message_dict = {}
            for field in message.fields:
                field_name = field.name
                field_value = field.value
                message_dict[field_name] = field_value
            
            # Parse different message types
            if message_name == "file_id":
                parsed_data.file_id = self._parse_file_id_message(message_dict)
            elif message_name == "device_info":
                parsed_data.device_info = self._parse_device_info_message(message_dict)
            elif message_name == "activity":
                parsed_data.activity = self._parse_activity_message(message_dict)
            elif message_name == "session":
                session = self._parse_session_message(message_dict)
                parsed_data.sessions.append(session)
            elif message_name == "lap":
                lap = self._parse_lap_message(message_dict)
                parsed_data.laps.append(lap)
            elif message_name == "record":
                record = self._parse_record_message(message_dict)
                parsed_data.records.append(record)
        
        return parsed_data
    
    def parse_file(self, file_path: str) -> ParsedFITData:
        """
        Parse a FIT file and extract all relevant data
        
        Args:
            file_path: Path to the FIT file
            
        Returns:
            ParsedFITData object containing all extracted data
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"FIT file not found: {file_path}")
        
        try:
            # Create a stream from the file
            stream = Stream.from_file(file_path)
            
            # Create decoder with the stream
            decoder = Decoder(stream)
            
            # Check if it's a valid FIT file
            if not decoder.is_fit():
                raise ValueError(f"File is not a valid FIT file: {file_path}")
            
            # Read all messages
            messages = decoder.read()
            
            # Process messages
            return self._process_messages(messages)
            
        except Exception as e:
            raise ValueError(f"Error parsing FIT file: {str(e)}")
        finally:
            # Clean up stream
            if 'stream' in locals():
                stream.close()
    
    def parse_stream(self, stream) -> ParsedFITData:
        """
        Parse a FIT file from a stream (e.g., uploaded file)
        
        Args:
            stream: File-like object containing FIT data
            
        Returns:
            ParsedFITData object containing all extracted data
        """
        try:
            # Check if stream has read method
            if hasattr(stream, 'read'):
                # Read the data
                data = stream.read()
                
                # Create a stream from bytes
                fit_stream = Stream.from_byte_array(data)
                
                # Create decoder
                decoder = Decoder(fit_stream)
                
                # Check if it's a valid FIT file
                if not decoder.is_fit():
                    raise ValueError("Stream does not contain valid FIT data")
                
                # Read all messages
                messages = decoder.read()
                
                # Process messages
                return self._process_messages(messages)
            else:
                raise ValueError("Stream object must have a read() method")
                
        except Exception as e:
            raise ValueError(f"Error parsing FIT stream: {str(e)}")
        finally:
            # Clean up stream
            if 'fit_stream' in locals():
                fit_stream.close()


# Create a singleton instance for convenience
fit_parser = FITParser()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        parser = FITParser()
        
        try:
            parsed_data = parser.parse_file(file_path)
            print("Successfully parsed FIT file!")
            print(f"File ID: {parsed_data.file_id}")
            print(f"Device Info: {parsed_data.device_info}")
            print(f"Activity: {parsed_data.activity}")
            print(f"Sessions: {len(parsed_data.sessions)}")
            print(f"Laps: {len(parsed_data.laps)}")
            print(f"Records: {len(parsed_data.records)}")
            
            # Print some sample records
            if parsed_data.records:
                print("\nSample Records:")
                for i, record in enumerate(parsed_data.records[:5]):
                    print(f"  Record {i+1}: {record}")
                    
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python fit_parser.py <path_to_fit_file>")
