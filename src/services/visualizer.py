"""
Visualization Service for FIT File API

This module provides functionality to generate plots and visualizations
for FIT file data using Matplotlib.
"""

import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure


class Visualizer:
    """
    Visualization Service for generating plots
    
    This class provides methods to create various plots from FIT file data.
    All plots use the darker green color (#006400) as specified in the requirements.
    """
    
    def __init__(self):
        """Initialize the visualizer"""
        # Set default style
        plt.style.use('default')
        self.darker_green = '#006400'  # Darker green as specified
    
    def generate_plot(
        self,
        activity_data: Dict[str, Any],
        metric: str = "power",
        width: int = 800,
        height: int = 600,
        dpi: int = 100
    ) -> bytes:
        """
        Generate a plot for the specified metric from activity data
        
        Args:
            activity_data: Activity data dictionary from storage
            metric: Metric to plot (e.g., 'power', 'speed', 'heart_rate', 'cadence')
            width: Width of the plot in pixels
            height: Height of the plot in pixels
            dpi: Dots per inch for the plot
            
        Returns:
            PNG image data as bytes
        """
        if not activity_data or not activity_data.get("records"):
            return self._generate_empty_plot(metric, width, height, dpi)
        
        records = activity_data["records"]
        activity = activity_data["activity"]
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Check if the metric exists in the data
        if metric not in df.columns or df[metric].isna().all():
            return self._generate_empty_plot(metric, width, height, dpi)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        try:
            # Convert timestamp to datetime if needed
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                
                # Plot the metric over time
                ax.plot(df['timestamp'], df[metric], 
                       color=self.darker_green, 
                       linewidth=2, 
                       label=metric)
                
                # Format x-axis for dates
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                plt.xticks(rotation=45)
                
            else:
                # Plot without timestamp
                ax.plot(df[metric], color=self.darker_green, linewidth=2, label=metric)
            
            # Set title and labels
            activity_type = activity.get("activity_type", "Activity")
            activity_id = activity.get("id", "Unknown")
            start_time = activity.get("start_time", "")
            
            title = f"{activity_type} - Activity {activity_id}"
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    title += f" ({start_dt.strftime('%Y-%m-%d %H:%M')})"
                except:
                    pass
            
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel(self._get_metric_label(metric), fontsize=12)
            
            # Add grid
            ax.grid(True, alpha=0.3)
            
            # Add legend
            ax.legend(loc='best')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            plt.close(fig)
            return self._generate_error_plot(str(e), width, height, dpi)
    
    def _generate_empty_plot(
        self,
        metric: str,
        width: int,
        height: int,
        dpi: int = 100
    ) -> bytes:
        """Generate a plot indicating no data available"""
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        try:
            ax.text(0.5, 0.5, f'No {metric} data available', 
                   ha='center', va='center', fontsize=14, color='gray')
            ax.set_title(f'No {metric} Data', fontsize=16, fontweight='bold')
            ax.axis('off')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception:
            plt.close(fig)
            return b""  # Return empty bytes
    
    def _generate_error_plot(
        self,
        error: str,
        width: int,
        height: int,
        dpi: int = 100
    ) -> bytes:
        """Generate a plot indicating an error"""
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        try:
            ax.text(0.5, 0.5, f'Error: {error}', 
                   ha='center', va='center', fontsize=12, color='red')
            ax.set_title('Plot Error', fontsize=16, fontweight='bold')
            ax.axis('off')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception:
            plt.close(fig)
            return b""  # Return empty bytes
    
    def _get_metric_label(self, metric: str) -> str:
        """Get a user-friendly label for a metric"""
        metric_labels = {
            'power': 'Power (Watts)',
            'speed': 'Speed (m/s)',
            'heart_rate': 'Heart Rate (BPM)',
            'cadence': 'Cadence (RPM)',
            'altitude': 'Altitude (m)',
            'distance': 'Distance (m)',
            'temperature': 'Temperature (°C)',
            'position_lat': 'Latitude',
            'position_long': 'Longitude',
        }
        return metric_labels.get(metric, metric)
    
    def generate_comparison_plot(
        self,
        activity_data_list: List[Dict[str, Any]],
        metric: str = "power",
        width: int = 1000,
        height: int = 600,
        dpi: int = 100
    ) -> bytes:
        """
        Generate a comparison plot for multiple activities
        
        Args:
            activity_data_list: List of activity data dictionaries
            metric: Metric to compare
            width: Width of the plot in pixels
            height: Height of the plot in pixels
            dpi: Dots per inch for the plot
            
        Returns:
            PNG image data as bytes
        """
        if not activity_data_list:
            return self._generate_empty_plot(metric, width, height, dpi)
        
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        try:
            for i, activity_data in enumerate(activity_data_list):
                if not activity_data or not activity_data.get("records"):
                    continue
                
                records = activity_data["records"]
                activity = activity_data["activity"]
                
                # Convert to DataFrame
                df = pd.DataFrame(records)
                
                # Check if the metric exists
                if metric not in df.columns or df[metric].isna().all():
                    continue
                
                # Convert timestamp to datetime if needed
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    # Normalize timestamps to start from 0 for comparison
                    if len(df) > 0:
                        start_time = df['timestamp'].iloc[0]
                        df['normalized_time'] = (df['timestamp'] - start_time).dt.total_seconds()
                        
                        ax.plot(df['normalized_time'], df[metric], 
                               color=self.darker_green, 
                               linewidth=2, 
                               alpha=0.7,
                               label=f"Activity {activity.get('id', i+1)}")
                else:
                    ax.plot(df[metric], 
                           color=self.darker_green, 
                           linewidth=2, 
                           alpha=0.7,
                           label=f"Activity {activity.get('id', i+1)}")
            
            # Set title and labels
            ax.set_title(f'Comparison: {self._get_metric_label(metric)}', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Time (seconds from start)', fontsize=12)
            ax.set_ylabel(self._get_metric_label(metric), fontsize=12)
            
            # Add grid and legend
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            plt.close(fig)
            return self._generate_error_plot(str(e), width, height, dpi)
    
    def generate_multi_metric_plot(
        self,
        activity_data: Dict[str, Any],
        metrics: List[str] = None,
        width: int = 1000,
        height: int = 600,
        dpi: int = 100
    ) -> bytes:
        """
        Generate a plot with multiple metrics for a single activity
        
        Args:
            activity_data: Activity data dictionary
            metrics: List of metrics to plot (default: power, speed, heart_rate, cadence)
            width: Width of the plot in pixels
            height: Height of the plot in pixels
            dpi: Dots per inch for the plot
            
        Returns:
            PNG image data as bytes
        """
        if not activity_data or not activity_data.get("records"):
            return self._generate_empty_plot("multiple metrics", width, height, dpi)
        
        if metrics is None:
            metrics = ['power', 'speed', 'heart_rate', 'cadence']
        
        records = activity_data["records"]
        activity = activity_data["activity"]
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Create figure with subplots
        n_metrics = len(metrics)
        if n_metrics == 0:
            return self._generate_empty_plot("multiple metrics", width, height, dpi)
        
        fig, axes = plt.subplots(n_metrics, 1, figsize=(width/dpi, height/dpi), dpi=dpi)
        
        if n_metrics == 1:
            axes = [axes]  # Ensure axes is a list
        
        try:
            for i, metric in enumerate(metrics):
                ax = axes[i]
                
                # Check if metric exists
                if metric not in df.columns or df[metric].isna().all():
                    ax.text(0.5, 0.5, f'No {metric} data', 
                           ha='center', va='center', fontsize=10, color='gray')
                    ax.set_title(f'{self._get_metric_label(metric)} - No Data')
                    continue
                
                # Convert timestamp to datetime if needed
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    ax.plot(df['timestamp'], df[metric], 
                           color=self.darker_green, 
                           linewidth=1.5, 
                           label=metric)
                    
                    # Format x-axis for dates
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    plt.xticks(rotation=45)
                else:
                    ax.plot(df[metric], 
                           color=self.darker_green, 
                           linewidth=1.5, 
                           label=metric)
                
                ax.set_title(f'{self._get_metric_label(metric)}', fontsize=10, fontweight='bold')
                ax.set_ylabel(self._get_metric_label(metric).split('(')[0].strip(), fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best', fontsize=8)
            
            # Set common x-label
            if 'timestamp' in df.columns:
                axes[-1].set_xlabel('Time', fontsize=10)
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            plt.close(fig)
            return self._generate_error_plot(str(e), width, height, dpi)
    
    def generate_summary_plot(
        self,
        activity_data: Dict[str, Any],
        width: int = 800,
        height: int = 600,
        dpi: int = 100
    ) -> bytes:
        """
        Generate a summary plot with key metrics for an activity
        
        Args:
            activity_data: Activity data dictionary
            width: Width of the plot in pixels
            height: Height of the plot in pixels
            dpi: Dots per inch for the plot
            
        Returns:
            PNG image data as bytes
        """
        if not activity_data or not activity_data.get("records"):
            return self._generate_empty_plot("summary", width, height, dpi)
        
        records = activity_data["records"]
        activity = activity_data["activity"]
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=(width/dpi, height/dpi), dpi=dpi)
        
        try:
            # Plot 1: Power
            if 'power' in df.columns and df['power'].notna().any():
                axes[0, 0].plot(df.index, df['power'], color=self.darker_green, linewidth=1.5)
                axes[0, 0].set_title('Power (Watts)', fontsize=10, fontweight='bold')
                axes[0, 0].grid(True, alpha=0.3)
            else:
                axes[0, 0].text(0.5, 0.5, 'No Power Data', ha='center', va='center', color='gray')
                axes[0, 0].set_title('Power (Watts)', fontsize=10, fontweight='bold')
            
            # Plot 2: Speed
            if 'speed' in df.columns and df['speed'].notna().any():
                axes[0, 1].plot(df.index, df['speed'], color=self.darker_green, linewidth=1.5)
                axes[0, 1].set_title('Speed (m/s)', fontsize=10, fontweight='bold')
                axes[0, 1].grid(True, alpha=0.3)
            else:
                axes[0, 1].text(0.5, 0.5, 'No Speed Data', ha='center', va='center', color='gray')
                axes[0, 1].set_title('Speed (m/s)', fontsize=10, fontweight='bold')
            
            # Plot 3: Heart Rate
            if 'heart_rate' in df.columns and df['heart_rate'].notna().any():
                axes[1, 0].plot(df.index, df['heart_rate'], color=self.darker_green, linewidth=1.5)
                axes[1, 0].set_title('Heart Rate (BPM)', fontsize=10, fontweight='bold')
                axes[1, 0].grid(True, alpha=0.3)
            else:
                axes[1, 0].text(0.5, 0.5, 'No Heart Rate Data', ha='center', va='center', color='gray')
                axes[1, 0].set_title('Heart Rate (BPM)', fontsize=10, fontweight='bold')
            
            # Plot 4: Cadence
            if 'cadence' in df.columns and df['cadence'].notna().any():
                axes[1, 1].plot(df.index, df['cadence'], color=self.darker_green, linewidth=1.5)
                axes[1, 1].set_title('Cadence (RPM)', fontsize=10, fontweight='bold')
                axes[1, 1].grid(True, alpha=0.3)
            else:
                axes[1, 1].text(0.5, 0.5, 'No Cadence Data', ha='center', va='center', color='gray')
                axes[1, 1].set_title('Cadence (RPM)', fontsize=10, fontweight='bold')
            
            # Set main title
            activity_type = activity.get("activity_type", "Activity")
            activity_id = activity.get("id", "Unknown")
            fig.suptitle(f'{activity_type} Summary - Activity {activity_id}', 
                        fontsize=14, fontweight='bold')
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            plt.close(fig)
            return self._generate_error_plot(str(e), width, height, dpi)


# Create a singleton instance for convenience
visualizer = Visualizer()


if __name__ == "__main__":
    # Example usage
    viz = Visualizer()
    
    # Create sample activity data for testing
    sample_activity = {
        "activity": {
            "id": 1,
            "activity_type": "cycling",
            "start_time": "2023-06-15T10:00:00"
        },
        "records": []
    }
    
    # Add sample records
    import numpy as np
    for i in range(100):
        sample_activity["records"].append({
            "timestamp": "2023-06-15T10:00:00" + f"+{i:03d}:00",
            "power": 200 + np.random.normal(0, 50),
            "speed": 10 + np.random.normal(0, 2),
            "heart_rate": 140 + np.random.normal(0, 10),
            "cadence": 80 + np.random.normal(0, 5)
        })
    
    # Test plot generation
    try:
        plot_data = viz.generate_plot(sample_activity, "power")
        print(f"Generated plot of size: {len(plot_data)} bytes")
        
        plot_data = viz.generate_multi_metric_plot(sample_activity)
        print(f"Generated multi-metric plot of size: {len(plot_data)} bytes")
        
        plot_data = viz.generate_summary_plot(sample_activity)
        print(f"Generated summary plot of size: {len(plot_data)} bytes")
        
    except Exception as e:
        print(f"Error generating plots: {e}")
