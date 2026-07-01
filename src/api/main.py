"""
Litestar API for Garmin FIT File Analysis

This module provides RESTful endpoints for uploading, querying, and analyzing
Garmin FIT files.
"""

import os
import tempfile
import io
from datetime import datetime
from typing import List, Optional, Union
from pathlib import Path

from litestar import Litestar, post, get, Request
from litestar.datastructures import UploadFile
from litestar.response import Response, File
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.exceptions import HTTPException
from litestar.params import Body
from litestar.openapi import OpenAPIConfig
from litestar.datastructures import State
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web
import matplotlib.pyplot as plt

from src.parsers.fit_parser import FITParser
from src.services.storage import DataStorage
from src.services.stats import StatsEngine
from src.services.visualizer import Visualizer


# Initialize services
parser = FITParser()
storage = DataStorage()
stats_engine = StatsEngine(storage)
visualizer = Visualizer()


@get("/health")
async def health_check() -> dict:
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        Dictionary with health status and version information
    """
    try:
        # Check database connection
        db_status = "healthy"
        try:
            storage.get_activity_count()
        except Exception:
            db_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "database": db_status,
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@get("/")
async def root() -> dict:
    """
    Root endpoint with API information.
    
    Returns:
        Dictionary with API name, version, and available endpoints
    """
    return {
        "name": "Garmin FIT File API",
        "version": "1.0.0",
        "description": "API for parsing, storing, and analyzing Garmin FIT files",
        "docs": "/schema",
        "health": "/health",
        "endpoints": {
            "upload": "POST /upload - Upload and parse FIT files",
            "activities": "GET /activities - List activities",
            "activity_detail": "GET /activities/{id} - Get activity details",
            "stats": "GET /stats - Get aggregate statistics",
            "compare": "GET /compare - Compare activities",
            "export": "GET /export/{id} - Export activity data",
            "plot": "GET /plot/{id} - Generate plots",
            "bike_metrics": "GET /bike-metrics/{id} - Get bike-specific metrics",
            "trends": "GET /trends - Get time series trends"
        }
    }


@post("/upload")
async def upload_file(request: Request) -> dict:
    """
    Upload and parse a FIT file.
    
    Expects a FIT file upload and returns the activity ID.
    """
    try:
        # Get the form data
        form_data = await request.form()
        
        # Get the file
        file = form_data.get("file")
        if not file or not hasattr(file, 'file'):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="No file provided or invalid file format"
            )
        
        # Save the uploaded file temporarily
        temp_path = None
        try:
            # Read the file content
            content = file.file.read()
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            # Parse the FIT file
            parsed_data = parser.parse_file(temp_path)
            
            # Store the activity
            activity_id = storage.store_activity(parsed_data)
            
            return {
                "activity_id": activity_id,
                "message": f"Successfully uploaded and parsed FIT file. Activity ID: {activity_id}"
            }
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error uploading/parsing FIT file: {str(e)}"
        )


@get("/activities")
async def list_activities(
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activity_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """
    List activities with optional filters.
    
    Supports filtering by user, date range, activity type, and pagination.
    """
    try:
        activities = storage.query_activities(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            activity_type=activity_type,
            limit=limit,
            offset=offset
        )
        
        total_count = storage.get_activity_count(user_id=user_id)
        
        return {
            "activities": activities,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error querying activities: {str(e)}"
        )


@get("/activities/{activity_id:int}")
async def get_activity(activity_id: int) -> dict:
    """
    Get detailed information for a specific activity.
    
    Returns activity details including sessions, laps, and time-series records.
    """
    try:
        activity_data = storage.get_activity(activity_id)
        
        if not activity_data:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        return activity_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving activity: {str(e)}"
        )


@get("/stats")
async def get_stats(
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    metric: str = "power",
    activity_type: Optional[str] = None
) -> dict:
    """
    Get aggregate statistics for a metric over a time period.
    
    Supports filtering by user, date range, activity type, and metric.
    """
    try:
        stats_result = stats_engine.aggregate_metrics(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            metric=metric,
            activity_type=activity_type
        )
        
        if "error" in stats_result:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=stats_result["error"]
            )
        
        return {
            "metric": metric,
            "statistics": stats_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error calculating statistics: {str(e)}"
        )


@get("/compare")
async def compare_activities(activity_ids: str) -> dict:
    """
    Compare multiple activities side by side.
    
    Expects a comma-separated list of activity IDs.
    """
    try:
        # Parse activity IDs
        ids = [int(id.strip()) for id in activity_ids.split(",") if id.strip()]
        
        if len(ids) < 2:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="At least 2 activity IDs required for comparison"
            )
        
        comparison_result = stats_engine.compare_activities(ids)
        
        if "error" in comparison_result:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=comparison_result["error"]
            )
        
        return {"comparison": comparison_result}
        
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity IDs: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error comparing activities: {str(e)}"
        )


@get("/export/{activity_id:int}")
async def export_activity(
    activity_id: int,
    format: str = "csv"
) -> Response:
    """
    Export activity data in the specified format.
    
    Supports CSV and JSON export formats.
    """
    try:
        activity_data = storage.get_activity(activity_id)
        
        if not activity_data:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Create DataFrame from records
        if activity_data["records"]:
            df = pd.DataFrame(activity_data["records"])
        else:
            df = pd.DataFrame()
        
        if format.lower() == "csv":
            # Generate CSV
            csv_data = df.to_csv(index=False)
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=activity_{activity_id}.csv"
                }
            )
        elif format.lower() == "json":
            # Generate JSON
            json_data = df.to_json(orient="records", date_format="iso")
            return Response(
                content=json_data,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=activity_{activity_id}.json"
                }
            )
        else:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Use 'csv' or 'json'."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error exporting activity: {str(e)}"
        )


@get("/plot/{activity_id:int}")
async def plot_activity(
    activity_id: int,
    metric: str = "power",
    width: int = 800,
    height: int = 600
) -> Response:
    """
    Generate a plot for the specified activity and metric.
    
    Returns a PNG image of the plot.
    """
    try:
        activity_data = storage.get_activity(activity_id)
        
        if not activity_data:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Generate plot
        plot_data = visualizer.generate_plot(
            activity_data=activity_data,
            metric=metric,
            width=width,
            height=height
        )
        
        return Response(
            content=plot_data,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=activity_{activity_id}_{metric}.png"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error generating plot: {str(e)}"
        )


@get("/bike-metrics/{activity_id:int}")
async def get_bike_metrics(activity_id: int) -> dict:
    """
    Get bike-specific metrics for an activity.
    
    Returns detailed bike metrics including power, cadence, speed, etc.
    """
    try:
        bike_metrics = stats_engine.get_bike_specific_metrics(activity_id)
        
        if "error" in bike_metrics:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=bike_metrics["error"]
            )
        
        return bike_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving bike metrics: {str(e)}"
        )


@get("/trends")
async def get_trends(
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    metric: str = "power",
    activity_type: Optional[str] = None,
    time_window: str = "daily"
) -> dict:
    """
    Get time series trends for a metric.
    
    Supports daily, weekly, and monthly time windows.
    """
    try:
        trends_result = stats_engine.get_time_series_trends(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            metric=metric,
            activity_type=activity_type,
            time_window=time_window
        )
        
        if "error" in trends_result:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=trends_result["error"]
            )
        
        return trends_result
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error calculating trends: {str(e)}"
        )


# Create the Litestar app
app = Litestar(
    route_handlers=[
        health_check,
        root,
        upload_file,
        list_activities,
        get_activity,
        get_stats,
        compare_activities,
        export_activity,
        plot_activity,
        get_bike_metrics,
        get_trends,
    ],
    debug=True,
    openapi_config=OpenAPIConfig(
        title="Garmin FIT File API",
        description="API for parsing, storing, and analyzing Garmin FIT files",
        version="1.0.0"
    )
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
