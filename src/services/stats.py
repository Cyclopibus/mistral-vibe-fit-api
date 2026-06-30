"""
Stats and Comparison Engine for FIT File API

This module provides functionality to calculate statistics and compare activities.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from src.services.storage import DataStorage


class StatsEngine:
    """
    Stats Engine for calculating statistics and comparisons
    
    This class provides methods to aggregate metrics, calculate trends,
    and compare activities.
    """
    
    def __init__(self, storage: DataStorage = None):
        """
        Initialize the stats engine
        
        Args:
            storage: DataStorage instance. If None, creates a new one.
        """
        self.storage = storage or DataStorage()
    
    def aggregate_metrics(
        self, 
        user_id: int = None,
        start_date: str = None, 
        end_date: str = None,
        metric: str = None,
        activity_type: str = None
    ) -> Dict[str, Any]:
        """
        Aggregate metrics for a given time period and metric
        
        Args:
            user_id: Filter by user ID
            start_date: Filter by start date (YYYY-MM-DD format)
            end_date: Filter by end date (YYYY-MM-DD format)
            metric: Metric to aggregate (e.g., 'power', 'speed', 'heart_rate', 'distance')
            activity_type: Filter by activity type
            
        Returns:
            Dictionary with aggregated statistics
        """
        # Get activities for the specified period
        activities = self.storage.query_activities(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            activity_type=activity_type,
            limit=1000  # Large limit to get all activities
        )
        
        if not activities:
            return {"error": "No activities found for the specified criteria"}
        
        # Collect all records for the specified metric
        all_values = []
        activity_count = 0
        total_distance = 0.0
        total_duration = 0.0
        
        for activity in activities:
            # Get full activity data including records
            full_activity = self.storage.get_activity(activity["id"])
            if not full_activity:
                continue
            
            activity_count += 1
            
            # Add to totals
            if full_activity["activity"]["total_distance"]:
                total_distance += full_activity["activity"]["total_distance"]
            if full_activity["activity"]["duration"]:
                total_duration += full_activity["activity"]["duration"]
            
            # Extract metric values from records
            for record in full_activity["records"]:
                if metric and metric in record and record[metric] is not None:
                    all_values.append(record[metric])
        
        if not all_values:
            return {
                "error": f"No {metric} data found",
                "activity_count": activity_count,
                "total_distance_meters": total_distance,
                "total_duration_seconds": total_duration
            }
        
        # Calculate statistics
        try:
            stats = {
                "metric": metric,
                "activity_count": activity_count,
                "total_distance_meters": total_distance,
                "total_duration_seconds": total_duration,
                "count": len(all_values),
                "min": float(np.min(all_values)),
                "max": float(np.max(all_values)),
                "mean": float(np.mean(all_values)),
                "median": float(np.median(all_values)),
                "std": float(np.std(all_values)),
                "sum": float(np.sum(all_values))
            }
            
            # Add percentiles
            stats["p25"] = float(np.percentile(all_values, 25))
            stats["p75"] = float(np.percentile(all_values, 75))
            
            return stats
            
        except Exception as e:
            return {"error": f"Error calculating statistics: {str(e)}"}
    
    def compare_activities(self, activity_ids: List[int]) -> Dict[str, Any]:
        """
        Compare multiple activities side by side
        
        Args:
            activity_ids: List of activity IDs to compare
            
        Returns:
            Dictionary with comparison data for each activity
        """
        if not activity_ids or len(activity_ids) < 2:
            return {"error": "At least 2 activity IDs required for comparison"}
        
        comparison = {}
        
        for activity_id in activity_ids:
            activity_data = self.storage.get_activity(activity_id)
            if not activity_data:
                continue
            
            activity = activity_data["activity"]
            sessions = activity_data["sessions"]
            laps = activity_data["laps"]
            records = activity_data["records"]
            
            # Calculate activity-level statistics
            activity_stats = {
                "id": activity["id"],
                "activity_type": activity["activity_type"],
                "start_time": activity["start_time"],
                "duration_seconds": activity["duration"],
                "total_distance_meters": activity["total_distance"],
                "total_ascent_meters": activity["total_ascent"],
                "total_descent_meters": activity["total_descent"],
                "num_sessions": activity["num_sessions"],
                "num_laps": activity["num_laps"]
            }
            
            # Calculate average metrics from records
            if records:
                df = pd.DataFrame(records)
                
                # Calculate averages for key metrics
                for metric in ['speed', 'power', 'heart_rate', 'cadence', 'altitude']:
                    if metric in df.columns and df[metric].notna().any():
                        activity_stats[f"avg_{metric}"] = float(df[metric].mean())
                        activity_stats[f"max_{metric}"] = float(df[metric].max())
                        activity_stats[f"min_{metric}"] = float(df[metric].min())
            
            # Calculate session-level statistics
            if sessions:
                for i, session in enumerate(sessions):
                    prefix = f"session_{i}_"
                    activity_stats[prefix + "sport"] = session.get("sport")
                    activity_stats[prefix + "sub_sport"] = session.get("sub_sport")
                    if session.get("avg_speed") is not None:
                        activity_stats[prefix + "avg_speed"] = session.get("avg_speed")
                    if session.get("max_speed") is not None:
                        activity_stats[prefix + "max_speed"] = session.get("max_speed")
                    if session.get("avg_power") is not None:
                        activity_stats[prefix + "avg_power"] = session.get("avg_power")
                    if session.get("max_power") is not None:
                        activity_stats[prefix + "max_power"] = session.get("max_power")
                    if session.get("avg_heart_rate") is not None:
                        activity_stats[prefix + "avg_heart_rate"] = session.get("avg_heart_rate")
                    if session.get("max_heart_rate") is not None:
                        activity_stats[prefix + "max_heart_rate"] = session.get("max_heart_rate")
            
            comparison[f"activity_{activity_id}"] = activity_stats
        
        # Calculate comparison metrics
        if len(comparison) >= 2:
            comparison["summary"] = self._calculate_comparison_summary(comparison)
        
        return comparison
    
    def _calculate_comparison_summary(self, comparison_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate summary statistics for activity comparison
        
        Args:
            comparison_data: Dictionary with activity comparison data
            
        Returns:
            Summary statistics
        """
        summary = {}
        
        # Extract all activity data
        activities = []
        for key, data in comparison_data.items():
            if key.startswith("activity_"):
                activities.append(data)
        
        if not activities:
            return summary
        
        # Calculate summary for key metrics
        key_metrics = [
            'duration_seconds', 'total_distance_meters', 'total_ascent_meters',
            'avg_speed', 'avg_power', 'avg_heart_rate', 'avg_cadence'
        ]
        
        for metric in key_metrics:
            values = []
            for activity in activities:
                if metric in activity and activity[metric] is not None:
                    values.append(activity[metric])
            
            if values and len(values) > 0:
                try:
                    summary[f"{metric}_min"] = min(values)
                    summary[f"{metric}_max"] = max(values)
                    summary[f"{metric}_mean"] = sum(values) / len(values)
                    summary[f"{metric}_range"] = max(values) - min(values)
                except (TypeError, ValueError):
                    # Skip if values can't be compared
                    pass
        
        return summary
    
    def get_time_series_trends(
        self, 
        user_id: int = None,
        start_date: str = None, 
        end_date: str = None,
        metric: str = "power",
        activity_type: str = None,
        time_window: str = "daily"
    ) -> Dict[str, Any]:
        """
        Calculate time series trends for a metric
        
        Args:
            user_id: Filter by user ID
            start_date: Filter by start date (YYYY-MM-DD format)
            end_date: Filter by end date (YYYY-MM-DD format)
            metric: Metric to analyze (e.g., 'power', 'speed', 'heart_rate')
            activity_type: Filter by activity type
            time_window: Time window for aggregation ('daily', 'weekly', 'monthly')
            
        Returns:
            Dictionary with time series data
        """
        # Get activities for the specified period
        activities = self.storage.query_activities(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            activity_type=activity_type,
            limit=1000
        )
        
        if not activities:
            return {"error": "No activities found for the specified criteria"}
        
        # Collect data by time window
        time_series = {}
        
        for activity in activities:
            full_activity = self.storage.get_activity(activity["id"])
            if not full_activity or not full_activity["records"]:
                continue
            
            activity_start = activity["start_time"]
            if not activity_start:
                continue
            
            # Parse the start time
            try:
                start_dt = datetime.fromisoformat(activity_start.replace('Z', '+00:00'))
            except:
                try:
                    start_dt = datetime.fromisoformat(activity_start)
                except:
                    continue
            
            # Determine the time window key
            if time_window == "daily":
                window_key = start_dt.strftime("%Y-%m-%d")
            elif time_window == "weekly":
                # Week starting on Monday
                week_start = start_dt - timedelta(days=start_dt.weekday())
                window_key = week_start.strftime("%Y-%m-%d")
            elif time_window == "monthly":
                window_key = start_dt.strftime("%Y-%m")
            else:
                window_key = start_dt.strftime("%Y-%m-%d")
            
            # Extract metric values from records
            metric_values = []
            for record in full_activity["records"]:
                if metric in record and record[metric] is not None:
                    metric_values.append(record[metric])
            
            if metric_values:
                if window_key not in time_series:
                    time_series[window_key] = {
                        "count": 0,
                        "sum": 0.0,
                        "min": float('inf'),
                        "max": float('-inf'),
                        "values": []
                    }
                
                time_series[window_key]["count"] += 1
                time_series[window_key]["sum"] += sum(metric_values)
                time_series[window_key]["min"] = min(time_series[window_key]["min"], min(metric_values))
                time_series[window_key]["max"] = max(time_series[window_key]["max"], max(metric_values))
                time_series[window_key]["values"].extend(metric_values)
        
        # Calculate final statistics for each time window
        result = {}
        for window_key, data in time_series.items():
            if data["values"]:
                result[window_key] = {
                    "count": data["count"],
                    "mean": data["sum"] / len(data["values"]),
                    "min": data["min"],
                    "max": data["max"],
                    "total": data["sum"]
                }
        
        return {
            "metric": metric,
            "time_window": time_window,
            "data": result
        }
    
    def get_activity_summary(self, activity_id: int) -> Dict[str, Any]:
        """
        Get comprehensive summary for a single activity
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            Dictionary with comprehensive activity summary
        """
        activity_data = self.storage.get_activity(activity_id)
        if not activity_data:
            return {"error": "Activity not found"}
        
        activity = activity_data["activity"]
        sessions = activity_data["sessions"]
        laps = activity_data["laps"]
        records = activity_data["records"]
        
        summary = {
            "activity_id": activity["id"],
            "activity_type": activity["activity_type"],
            "start_time": activity["start_time"],
            "duration_seconds": activity["duration"],
            "total_distance_meters": activity["total_distance"],
            "total_ascent_meters": activity["total_ascent"],
            "total_descent_meters": activity["total_descent"]
        }
        
        # Calculate speed metrics
        if activity["duration"] and activity["total_distance"]:
            summary["avg_speed_mps"] = activity["total_distance"] / activity["duration"]
            summary["avg_speed_kph"] = (activity["total_distance"] / activity["duration"]) * 3.6
        
        # Calculate metrics from records
        if records:
            df = pd.DataFrame(records)
            
            # Basic statistics for each metric
            metrics = ['speed', 'power', 'heart_rate', 'cadence', 'altitude', 'distance']
            for metric in metrics:
                if metric in df.columns and df[metric].notna().any():
                    summary[f"{metric}_min"] = float(df[metric].min())
                    summary[f"{metric}_max"] = float(df[metric].max())
                    summary[f"{metric}_mean"] = float(df[metric].mean())
                    summary[f"{metric}_median"] = float(df[metric].median())
                    summary[f"{metric}_std"] = float(df[metric].std())
        
        # Session statistics
        if sessions:
            session_data = []
            for session in sessions:
                session_summary = {
                    "session_id": session.get("session_id"),
                    "sport": session.get("sport"),
                    "sub_sport": session.get("sub_sport"),
                    "duration_seconds": session.get("total_timer_time"),
                    "distance_meters": session.get("total_distance"),
                    "avg_speed_mps": session.get("avg_speed"),
                    "max_speed_mps": session.get("max_speed"),
                    "avg_power_watts": session.get("avg_power"),
                    "max_power_watts": session.get("max_power"),
                    "avg_heart_rate_bpm": session.get("avg_heart_rate"),
                    "max_heart_rate_bpm": session.get("max_heart_rate"),
                    "avg_cadence_rpm": session.get("avg_cadence"),
                    "max_cadence_rpm": session.get("max_cadence")
                }
                session_data.append(session_summary)
            
            summary["sessions"] = session_data
        
        # Lap statistics
        if laps:
            lap_data = []
            for lap in laps:
                lap_summary = {
                    "lap_id": lap.get("lap_id"),
                    "intensity": lap.get("intensity"),
                    "duration_seconds": lap.get("total_timer_time"),
                    "distance_meters": lap.get("total_distance"),
                    "avg_speed_mps": lap.get("avg_speed"),
                    "max_speed_mps": lap.get("max_speed"),
                    "avg_power_watts": lap.get("avg_power"),
                    "max_power_watts": lap.get("max_power"),
                    "avg_heart_rate_bpm": lap.get("avg_heart_rate"),
                    "max_heart_rate_bpm": lap.get("max_heart_rate"),
                    "avg_cadence_rpm": lap.get("avg_cadence"),
                    "max_cadence_rpm": lap.get("max_cadence")
                }
                lap_data.append(lap_summary)
            
            summary["laps"] = lap_data
        
        return summary
    
    def get_bike_specific_metrics(self, activity_id: int) -> Dict[str, Any]:
        """
        Get bike-specific metrics for an activity
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            Dictionary with bike-specific metrics
        """
        activity_data = self.storage.get_activity(activity_id)
        if not activity_data:
            return {"error": "Activity not found"}
        
        activity = activity_data["activity"]
        records = activity_data["records"]
        
        if not records:
            return {"error": "No record data available"}
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(records)
        
        bike_metrics = {
            "activity_id": activity["id"],
            "activity_type": activity["activity_type"],
            "start_time": activity["start_time"]
        }
        
        # Power analysis
        if 'power' in df.columns and df['power'].notna().any():
            power_data = df['power'].dropna()
            bike_metrics['power'] = {
                "avg_watts": float(power_data.mean()),
                "max_watts": float(power_data.max()),
                "min_watts": float(power_data.min()),
                "std_watts": float(power_data.std()),
                "total_kilojoules": float(power_data.sum() * activity["duration"] / len(power_data) / 1000) if activity["duration"] else None
            }
        
        # Cadence analysis
        if 'cadence' in df.columns and df['cadence'].notna().any():
            cadence_data = df['cadence'].dropna()
            bike_metrics['cadence'] = {
                "avg_rpm": float(cadence_data.mean()),
                "max_rpm": float(cadence_data.max()),
                "min_rpm": float(cadence_data.min()),
                "std_rpm": float(cadence_data.std())
            }
        
        # Speed analysis
        if 'speed' in df.columns and df['speed'].notna().any():
            speed_data = df['speed'].dropna()
            bike_metrics['speed'] = {
                "avg_mps": float(speed_data.mean()),
                "avg_kph": float(speed_data.mean() * 3.6),
                "max_mps": float(speed_data.max()),
                "max_kph": float(speed_data.max() * 3.6),
                "min_mps": float(speed_data.min()),
                "std_mps": float(speed_data.std())
            }
        
        # Heart rate analysis
        if 'heart_rate' in df.columns and df['heart_rate'].notna().any():
            hr_data = df['heart_rate'].dropna()
            bike_metrics['heart_rate'] = {
                "avg_bpm": float(hr_data.mean()),
                "max_bpm": float(hr_data.max()),
                "min_bpm": float(hr_data.min()),
                "std_bpm": float(hr_data.std())
            }
        
        # GPS analysis
        if 'position_lat' in df.columns and 'position_long' in df.columns:
            gps_data = df[['position_lat', 'position_long']].dropna()
            if len(gps_data) > 1:
                # Calculate distance between points (simplified)
                bike_metrics['gps'] = {
                    "points": len(gps_data),
                    "has_gps": True
                }
            else:
                bike_metrics['gps'] = {"has_gps": False}
        
        # Altitude analysis
        if 'altitude' in df.columns and df['altitude'].notna().any():
            altitude_data = df['altitude'].dropna()
            bike_metrics['altitude'] = {
                "avg_meters": float(altitude_data.mean()),
                "max_meters": float(altitude_data.max()),
                "min_meters": float(altitude_data.min()),
                "ascent_meters": float(altitude_data.diff().clip(lower=0).sum()) if len(altitude_data) > 1 else 0.0,
                "descent_meters": float(-altitude_data.diff().clip(upper=0).sum()) if len(altitude_data) > 1 else 0.0
            }
        
        return bike_metrics


# Create a singleton instance for convenience
stats_engine = StatsEngine()


if __name__ == "__main__":
    # Example usage
    stats = StatsEngine()
    
    # Test with sample data
    print("Stats Engine Example Usage:")
    
    # Aggregate metrics
    try:
        result = stats.aggregate_metrics(metric="power", activity_type="cycling")
        print(f"Power aggregation: {result}")
    except Exception as e:
        print(f"Error in aggregation: {e}")
    
    # Compare activities (would need actual activity IDs)
    try:
        comparison = stats.compare_activities([1, 2])  # Example IDs
        print(f"Comparison: {comparison}")
    except Exception as e:
        print(f"Error in comparison: {e}")
