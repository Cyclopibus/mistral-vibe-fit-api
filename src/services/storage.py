"""
Storage Service for FIT File API

This module provides functionality to store and retrieve FIT file data
from the database.
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, func, and_, or_, desc, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError
import os

from src.database.models import (
    Base, User, Device, Activity, Session, Lap, Record,
    create_database_engine, create_tables
)
from src.parsers.fit_parser import ParsedFITData


class DataStorage:
    """
    Data Storage Service for FIT file data
    
    This class provides methods to store parsed FIT data and query it efficiently.
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize the storage service
        
        Args:
            db_url: Database URL. If None, uses SQLite database
        """
        if db_url is None:
            # Default to SQLite database
            db_url = "sqlite:///fit_api.db"
        
        self.engine = create_database_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
        # Create tables if they don't exist
        create_tables(self.engine)
    
    def _get_or_create_user(self, user_id: int = None, username: str = None, email: str = None) -> User:
        """
        Get or create a user
        
        Args:
            user_id: User ID (if known)
            username: Username
            email: Email address
            
        Returns:
            User object
        """
        session = self.Session()
        try:
            user = None
            
            if user_id is not None:
                # Try to find by ID
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    # Update email if provided
                    if email and not user.email:
                        user.email = email
                        session.commit()
                    return user
            
            if username is not None:
                # Try to find by username
                user = session.query(User).filter(User.username == username).first()
                if user:
                    # Update email if provided
                    if email and not user.email:
                        user.email = email
                        session.commit()
                    return user
            
            # Create new user
            user = User(
                username=username or f"user_{datetime.now().timestamp()}",
                email=email
            )
            session.add(user)
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _get_or_create_device(self, device_info) -> Device:
        """
        Get or create a device
        
        Args:
            device_info: DeviceInfo object from parsed FIT data
            
        Returns:
            Device object
        """
        if device_info is None:
            return None
        
        session = self.Session()
        try:
            # Try to find existing device by serial number
            if device_info.serial_number is not None:
                device = session.query(Device).filter(
                    Device.serial_number == device_info.serial_number
                ).first()
                if device:
                    return device
            
            # Try to find by manufacturer and product name
            if device_info.manufacturer and device_info.product_name:
                device = session.query(Device).filter(
                    Device.manufacturer == device_info.manufacturer,
                    Device.product_name == device_info.product_name
                ).first()
                if device:
                    return device
            
            # Create new device
            device = Device(
                manufacturer=device_info.manufacturer,
                product_name=device_info.product_name,
                device_index=device_info.device_index,
                serial_number=device_info.serial_number,
                software_version=device_info.software_version,
                hardware_version=device_info.hardware_version
            )
            session.add(device)
            session.commit()
            return device
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def store_activity(self, parsed_data: ParsedFITData, user_id: int = None, username: str = None, email: str = None) -> int:
        """
        Store parsed FIT data in the database
        
        Args:
            parsed_data: ParsedFITData object from FIT parser
            user_id: User ID to associate with the activity
            username: Username to associate with the activity
            email: Email to associate with the user
            
        Returns:
            ID of the created activity
        """
        session = self.Session()
        try:
            # Get or create user
            user = None
            if user_id is not None or username is not None:
                user = self._get_or_create_user(user_id, username, email)
            
            # Get or create device
            device = self._get_or_create_device(parsed_data.device_info)
            
            # Create activity
            activity = Activity(
                activity_id=parsed_data.activity.activity_id if parsed_data.activity else None,
                activity_type=parsed_data.activity.activity_type if parsed_data.activity else None,
                start_time=parsed_data.activity.start_time if parsed_data.activity else None,
                duration=parsed_data.activity.duration if parsed_data.activity else None,
                total_distance=parsed_data.activity.total_distance if parsed_data.activity else None,
                total_ascent=parsed_data.activity.total_ascent if parsed_data.activity else None,
                total_descent=parsed_data.activity.total_descent if parsed_data.activity else None,
                num_sessions=parsed_data.activity.num_sessions if parsed_data.activity else None,
                num_laps=parsed_data.activity.num_laps if parsed_data.activity else None,
                user=user,
                device=device
            )
            
            session.add(activity)
            session.flush()  # Get the activity ID
            
            # Store sessions
            for session_data in parsed_data.sessions:
                db_session = Session(
                    session_id=session_data.session_id,
                    start_time=session_data.start_time,
                    total_elapsed_time=session_data.total_elapsed_time,
                    total_timer_time=session_data.total_timer_time,
                    total_distance=session_data.total_distance,
                    total_ascent=session_data.total_ascent,
                    total_descent=session_data.total_descent,
                    avg_speed=session_data.avg_speed,
                    max_speed=session_data.max_speed,
                    avg_heart_rate=session_data.avg_heart_rate,
                    max_heart_rate=session_data.max_heart_rate,
                    avg_cadence=session_data.avg_cadence,
                    max_cadence=session_data.max_cadence,
                    avg_power=session_data.avg_power,
                    max_power=session_data.max_power,
                    sport=session_data.sport,
                    sub_sport=session_data.sub_sport,
                    activity=activity
                )
                session.add(db_session)
            
            # Store laps
            for lap_data in parsed_data.laps:
                db_lap = Lap(
                    lap_id=lap_data.lap_id,
                    start_time=lap_data.start_time,
                    total_elapsed_time=lap_data.total_elapsed_time,
                    total_timer_time=lap_data.total_timer_time,
                    total_distance=lap_data.total_distance,
                    total_ascent=lap_data.total_ascent,
                    total_descent=lap_data.total_descent,
                    avg_speed=lap_data.avg_speed,
                    max_speed=lap_data.max_speed,
                    avg_heart_rate=lap_data.avg_heart_rate,
                    max_heart_rate=lap_data.max_heart_rate,
                    avg_cadence=lap_data.avg_cadence,
                    max_cadence=lap_data.max_cadence,
                    avg_power=lap_data.avg_power,
                    max_power=lap_data.max_power,
                    intensity=lap_data.intensity,
                    activity=activity
                )
                session.add(db_lap)
            
            # Store records
            for record_data in parsed_data.records:
                db_record = Record(
                    timestamp=record_data.timestamp,
                    position_lat=record_data.position_lat,
                    position_long=record_data.position_long,
                    distance=record_data.distance,
                    speed=record_data.speed,
                    cadence=record_data.cadence,
                    power=record_data.power,
                    heart_rate=record_data.heart_rate,
                    altitude=record_data.altitude,
                    temperature=record_data.temperature,
                    time_from_course=record_data.time_from_course,
                    activity=activity
                )
                session.add(db_record)
            
            session.commit()
            return activity.id
            
        except Exception as e:
            session.rollback()
            raise ValueError(f"Error storing activity: {str(e)}")
        finally:
            session.close()
    
    def get_activity(self, activity_id: int) -> Dict[str, Any]:
        """
        Get activity details and all associated data
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            Dictionary containing activity details, sessions, laps, and records
        """
        session = self.Session()
        try:
            # Get activity
            activity = session.query(Activity).filter(Activity.id == activity_id).first()
            if not activity:
                return None
            
            # Convert to dictionary
            result = {
                "activity": {
                    "id": activity.id,
                    "activity_id": activity.activity_id,
                    "activity_type": activity.activity_type,
                    "start_time": activity.start_time.isoformat() if activity.start_time else None,
                    "duration": activity.duration,
                    "total_distance": activity.total_distance,
                    "total_ascent": activity.total_ascent,
                    "total_descent": activity.total_descent,
                    "num_sessions": activity.num_sessions,
                    "num_laps": activity.num_laps,
                    "user_id": activity.user_id,
                    "device_id": activity.device_id
                },
                "sessions": [],
                "laps": [],
                "records": []
            }
            
            # Add sessions
            for db_session in activity.sessions:
                result["sessions"].append({
                    "id": db_session.id,
                    "session_id": db_session.session_id,
                    "start_time": db_session.start_time.isoformat() if db_session.start_time else None,
                    "total_elapsed_time": db_session.total_elapsed_time,
                    "total_timer_time": db_session.total_timer_time,
                    "total_distance": db_session.total_distance,
                    "total_ascent": db_session.total_ascent,
                    "total_descent": db_session.total_descent,
                    "avg_speed": db_session.avg_speed,
                    "max_speed": db_session.max_speed,
                    "avg_heart_rate": db_session.avg_heart_rate,
                    "max_heart_rate": db_session.max_heart_rate,
                    "avg_cadence": db_session.avg_cadence,
                    "max_cadence": db_session.max_cadence,
                    "avg_power": db_session.avg_power,
                    "max_power": db_session.max_power,
                    "sport": db_session.sport,
                    "sub_sport": db_session.sub_sport
                })
            
            # Add laps
            for db_lap in activity.laps:
                result["laps"].append({
                    "id": db_lap.id,
                    "lap_id": db_lap.lap_id,
                    "start_time": db_lap.start_time.isoformat() if db_lap.start_time else None,
                    "total_elapsed_time": db_lap.total_elapsed_time,
                    "total_timer_time": db_lap.total_timer_time,
                    "total_distance": db_lap.total_distance,
                    "total_ascent": db_lap.total_ascent,
                    "total_descent": db_lap.total_descent,
                    "avg_speed": db_lap.avg_speed,
                    "max_speed": db_lap.max_speed,
                    "avg_heart_rate": db_lap.avg_heart_rate,
                    "max_heart_rate": db_lap.max_heart_rate,
                    "avg_cadence": db_lap.avg_cadence,
                    "max_cadence": db_lap.max_cadence,
                    "avg_power": db_lap.avg_power,
                    "max_power": db_lap.max_power,
                    "intensity": db_lap.intensity
                })
            
            # Add records
            for db_record in activity.records:
                result["records"].append({
                    "id": db_record.id,
                    "timestamp": db_record.timestamp.isoformat() if db_record.timestamp else None,
                    "position_lat": db_record.position_lat,
                    "position_long": db_record.position_long,
                    "distance": db_record.distance,
                    "speed": db_record.speed,
                    "cadence": db_record.cadence,
                    "power": db_record.power,
                    "heart_rate": db_record.heart_rate,
                    "altitude": db_record.altitude,
                    "temperature": db_record.temperature,
                    "time_from_course": db_record.time_from_course
                })
            
            return result
            
        except Exception as e:
            raise ValueError(f"Error retrieving activity: {str(e)}")
        finally:
            session.close()
    
    def query_activities(
        self, 
        user_id: int = None, 
        start_date: str = None, 
        end_date: str = None,
        activity_type: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query activities with optional filters
        
        Args:
            user_id: Filter by user ID
            start_date: Filter by start date (YYYY-MM-DD format)
            end_date: Filter by end date (YYYY-MM-DD format)
            activity_type: Filter by activity type
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of activity dictionaries
        """
        session = self.Session()
        try:
            query = session.query(Activity)
            
            # Apply filters
            if user_id is not None:
                query = query.filter(Activity.user_id == user_id)
            
            if start_date is not None:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Activity.start_time >= start_dt)
            
            if end_date is not None:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # Include the entire end date
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(Activity.start_time <= end_dt)
            
            if activity_type is not None:
                query = query.filter(Activity.activity_type == activity_type)
            
            # Order by start time (newest first)
            query = query.order_by(desc(Activity.start_time))
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            activities = query.all()
            
            result = []
            for activity in activities:
                result.append({
                    "id": activity.id,
                    "activity_id": activity.activity_id,
                    "activity_type": activity.activity_type,
                    "start_time": activity.start_time.isoformat() if activity.start_time else None,
                    "duration": activity.duration,
                    "total_distance": activity.total_distance,
                    "total_ascent": activity.total_ascent,
                    "total_descent": activity.total_descent,
                    "num_sessions": activity.num_sessions,
                    "num_laps": activity.num_laps,
                    "user_id": activity.user_id,
                    "device_id": activity.device_id
                })
            
            return result
            
        except Exception as e:
            raise ValueError(f"Error querying activities: {str(e)}")
        finally:
            session.close()
    
    def get_activity_count(self, user_id: int = None) -> int:
        """
        Get total count of activities
        
        Args:
            user_id: Filter by user ID
            
        Returns:
            Count of activities
        """
        session = self.Session()
        try:
            query = session.query(Activity)
            
            if user_id is not None:
                query = query.filter(Activity.user_id == user_id)
            
            return query.count()
            
        except Exception as e:
            raise ValueError(f"Error counting activities: {str(e)}")
        finally:
            session.close()
    
    def delete_activity(self, activity_id: int) -> bool:
        """
        Delete an activity and all its associated data
        
        Args:
            activity_id: ID of the activity to delete
            
        Returns:
            True if deletion was successful
        """
        session = self.Session()
        try:
            activity = session.query(Activity).filter(Activity.id == activity_id).first()
            if not activity:
                return False
            
            session.delete(activity)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            raise ValueError(f"Error deleting activity: {str(e)}")
        finally:
            session.close()
    
    def get_device_info(self, device_id: int) -> Dict[str, Any]:
        """
        Get device information
        
        Args:
            device_id: ID of the device
            
        Returns:
            Device information dictionary
        """
        session = self.Session()
        try:
            device = session.query(Device).filter(Device.id == device_id).first()
            if not device:
                return None
            
            return {
                "id": device.id,
                "manufacturer": device.manufacturer,
                "product_name": device.product_name,
                "device_index": device.device_index,
                "serial_number": device.serial_number,
                "software_version": device.software_version,
                "hardware_version": device.hardware_version
            }
            
        except Exception as e:
            raise ValueError(f"Error retrieving device info: {str(e)}")
        finally:
            session.close()
    
    def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            user_id: ID of the user
            
        Returns:
            User information dictionary
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
            
        except Exception as e:
            raise ValueError(f"Error retrieving user info: {str(e)}")
        finally:
            session.close()
    
    def clear_all_data(self):
        """
        Clear all data from the database (for testing purposes)
        """
        session = self.Session()
        try:
            # Delete all records first (due to foreign key constraints)
            session.query(Record).delete()
            session.query(Lap).delete()
            session.query(Session).delete()
            session.query(Activity).delete()
            session.query(Device).delete()
            session.query(User).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            raise ValueError(f"Error clearing data: {str(e)}")
        finally:
            session.close()
    
    def close(self):
        """Close the database connection"""
        self.Session.remove()
        self.engine.dispose()


# Create a singleton instance for convenience
storage = DataStorage()


if __name__ == "__main__":
    # Example usage
    storage = DataStorage("sqlite:///test_fit_api.db")
    
    # Test with a sample FIT file if available
    import sys
    if len(sys.argv) > 1:
        from src.parsers.fit_parser import FITParser
        
        fit_file = sys.argv[1]
        parser = FITParser()
        
        try:
            parsed_data = parser.parse_file(fit_file)
            activity_id = storage.store_activity(parsed_data, username="test_user")
            print(f"Stored activity with ID: {activity_id}")
            
            # Retrieve the activity
            activity_data = storage.get_activity(activity_id)
            print(f"Retrieved activity: {activity_data['activity']}")
            print(f"Number of records: {len(activity_data['records'])}")
            
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python storage.py <path_to_fit_file>")
