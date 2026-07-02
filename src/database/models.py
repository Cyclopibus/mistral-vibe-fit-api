"""
Database Models for FIT File API

This module defines SQLAlchemy models for storing FIT file data.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine, Index
import os

# Create the base class for declarative models
Base = declarative_base()


class User(Base):
    """User model for tracking who uploaded activities"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activities = relationship("Activity", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Device(Base):
    """Device information from FIT files"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer = Column(String(50), nullable=True)
    product_name = Column(String(100), nullable=True)
    device_index = Column(Integer, nullable=True)
    serial_number = Column(Integer, nullable=True)
    software_version = Column(Float, nullable=True)
    hardware_version = Column(Integer, nullable=True)
    
    # Relationships
    activities = relationship("Activity", back_populates="device")
    
    def __repr__(self):
        return f"<Device(id={self.id}, product='{self.product_name}')>"


class Activity(Base):
    """Activity information from FIT files"""
    __tablename__ = 'activities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(Integer, nullable=True)  # Original activity ID from FIT file
    activity_type = Column(String(50), nullable=True)
    start_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    total_distance = Column(Float, nullable=True)  # in meters
    total_ascent = Column(Float, nullable=True)  # in meters
    total_descent = Column(Float, nullable=True)  # in meters
    num_sessions = Column(Integer, nullable=True)
    num_laps = Column(Integer, nullable=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="activities")
    device = relationship("Device", back_populates="activities")
    sessions = relationship("Session", back_populates="activity", cascade="all, delete-orphan")
    laps = relationship("Lap", back_populates="activity", cascade="all, delete-orphan")
    records = relationship("Record", back_populates="activity", cascade="all, delete-orphan")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_activity_user_start', 'user_id', 'start_time'),
        Index('idx_activity_type_start', 'activity_type', 'start_time'),
    )
    
    def __repr__(self):
        return f"<Activity(id={self.id}, type='{self.activity_type}', start={self.start_time})>"


class Session(Base):
    """Session information from FIT files"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=True)  # Original session ID from FIT file
    start_time = Column(DateTime, nullable=True)
    total_elapsed_time = Column(Float, nullable=True)  # in seconds
    total_timer_time = Column(Float, nullable=True)  # in seconds
    total_distance = Column(Float, nullable=True)  # in meters
    total_ascent = Column(Float, nullable=True)  # in meters
    total_descent = Column(Float, nullable=True)  # in meters
    avg_speed = Column(Float, nullable=True)  # in m/s
    max_speed = Column(Float, nullable=True)  # in m/s
    avg_heart_rate = Column(Float, nullable=True)  # in BPM
    max_heart_rate = Column(Float, nullable=True)  # in BPM
    avg_cadence = Column(Float, nullable=True)  # in RPM
    max_cadence = Column(Float, nullable=True)  # in RPM
    avg_power = Column(Float, nullable=True)  # in watts
    max_power = Column(Float, nullable=True)  # in watts
    sport = Column(String(50), nullable=True)
    sub_sport = Column(String(50), nullable=True)
    
    # Foreign key
    activity_id = Column(Integer, ForeignKey('activities.id'), nullable=False)
    
    # Relationships
    activity = relationship("Activity", back_populates="sessions")
    
    def __repr__(self):
        return f"<Session(id={self.id}, sport='{self.sport}', start={self.start_time})>"


class Lap(Base):
    """Lap information from FIT files"""
    __tablename__ = 'laps'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lap_id = Column(Integer, nullable=True)  # Original lap ID from FIT file
    start_time = Column(DateTime, nullable=True)
    total_elapsed_time = Column(Float, nullable=True)  # in seconds
    total_timer_time = Column(Float, nullable=True)  # in seconds
    total_distance = Column(Float, nullable=True)  # in meters
    total_ascent = Column(Float, nullable=True)  # in meters
    total_descent = Column(Float, nullable=True)  # in meters
    avg_speed = Column(Float, nullable=True)  # in m/s
    max_speed = Column(Float, nullable=True)  # in m/s
    avg_heart_rate = Column(Float, nullable=True)  # in BPM
    max_heart_rate = Column(Float, nullable=True)  # in BPM
    avg_cadence = Column(Float, nullable=True)  # in RPM
    max_cadence = Column(Float, nullable=True)  # in RPM
    avg_power = Column(Float, nullable=True)  # in watts
    max_power = Column(Float, nullable=True)  # in watts
    intensity = Column(String(50), nullable=True)
    
    # Foreign key
    activity_id = Column(Integer, ForeignKey('activities.id'), nullable=False)
    
    # Relationships
    activity = relationship("Activity", back_populates="laps")
    
    def __repr__(self):
        return f"<Lap(id={self.id}, intensity='{self.intensity}', distance={self.total_distance})>"


class Record(Base):
    """Time-series record data from FIT files"""
    __tablename__ = 'records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=True)
    position_lat = Column(Float, nullable=True)  # in degrees
    position_long = Column(Float, nullable=True)  # in degrees
    distance = Column(Float, nullable=True)  # in meters
    speed = Column(Float, nullable=True)  # in m/s
    cadence = Column(Float, nullable=True)  # in RPM
    power = Column(Float, nullable=True)  # in watts
    heart_rate = Column(Float, nullable=True)  # in BPM
    altitude = Column(Float, nullable=True)  # in meters
    temperature = Column(Float, nullable=True)  # in Celsius
    time_from_course = Column(Float, nullable=True)  # in seconds
    
    # Foreign key
    activity_id = Column(Integer, ForeignKey('activities.id'), nullable=False)
    
    # Relationships
    activity = relationship("Activity", back_populates="records")
    
    # Indexes for better query performance on time-series data
    __table_args__ = (
        Index('idx_record_activity_timestamp', 'activity_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Record(id={self.id}, time={self.timestamp}, power={self.power})>"


def create_database_engine(db_url: str = None):
    """
    Create SQLAlchemy engine for the database
    
    Args:
        db_url: Database URL. If None, uses SQLite in-memory database
        
    Returns:
        SQLAlchemy engine
    """
    if db_url is None:
        # Default to SQLite in-memory database for testing
        db_url = "sqlite:///:memory:"
    
    # For SQLite, we need to handle relative paths
    if db_url.startswith("sqlite:///"):
        # Convert relative path to absolute
        db_path = db_url.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            # Create data directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
            db_path = os.path.join("data", db_path)
            db_url = f"sqlite:///{db_path}"
    
    engine = create_engine(db_url, echo=False)
    return engine


def create_tables(engine):
    """
    Create all database tables
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """
    Drop all database tables
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(engine)


if __name__ == "__main__":
    # Example usage
    engine = create_database_engine("sqlite:///fit_api.db")
    create_tables(engine)
    print("Database tables created successfully!")
