import frappe
from frappe import _
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    get_employee_by_user,
    exception_handler,
)
import json
from datetime import datetime

"""save user location"""

"""{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [72.855663, 19.080709],
          [72.871113, 19.09531],
          [72.873344, 19.078438],
          [72.86459, 19.067731],
          [72.848454, 19.073084],
          [72.854633, 19.081521],
          [72.840214, 19.105204]
        ]
      }
    }
  ]
}
"""


@frappe.whitelist()
@ess_validate(methods=["POST"])
def user_location(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("location"):
            return gen_response(500, "location is required.")
        
        current_employee = get_employee_by_user(frappe.session.user)
        if not current_employee:
            return gen_response(404, "Employee not found for current user")

        # Get office geofencing settings
        office_geofence = frappe.get_all(
            "Office Geofencing",
            fields=["latitude", "longitude", "radius"],
            limit=1
        )

        # Process location data
        location_data = process_location_data(data.get("location"))
        
        # Check if locations are within geofence if office geofence exists
        if office_geofence:
            geofence = office_geofence[0]
            for coord in location_data["features"][0]["geometry"]["coordinates"]:
                if not is_point_in_geofence(
                    coord[1],  # latitude
                    coord[0],  # longitude
                    geofence.latitude,
                    geofence.longitude,
                    geofence.radius
                ):
                    frappe.log_error(
                        f"Location outside geofence: {coord}",
                        "Employee Location Tracking"
                    )

        # Get or create Employee Location document
        location_doc = get_or_create_location_doc(current_employee, data.get("date"))
        
        # Update location data
        update_location_doc(location_doc, location_data)
        
        return gen_response(200, "Location updated successfully.")

    except Exception as e:
        return exception_handler(e)

def process_location_data(location_data):
    """Process and validate location data"""
    try:
        if isinstance(location_data, str):
            location_data = json.loads(location_data)
        
        # Ensure data is in correct format
        if not isinstance(location_data, dict):
            raise ValueError("Invalid location data format")
        
        # Validate required fields
        if not all(key in location_data for key in ["type", "features"]):
            raise ValueError("Missing required fields in location data")
        
        # Validate coordinates
        for feature in location_data["features"]:
            if not feature.get("geometry", {}).get("coordinates"):
                raise ValueError("Missing coordinates in feature")
            
            # Ensure coordinates are valid numbers
            for coord in feature["geometry"]["coordinates"]:
                if not (isinstance(coord[0], (int, float)) and 
                       isinstance(coord[1], (int, float))):
                    raise ValueError("Invalid coordinate values")
        
        return location_data
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in location data")
    except Exception as e:
        raise ValueError(f"Error processing location data: {str(e)}")

def get_or_create_location_doc(employee, date):
    """Get existing location doc or create new one"""
    filters = {
        "employee": employee.get("name"),
        "date": date or frappe.utils.today()
    }
    
    if frappe.db.exists("Employee Location", filters):
        return frappe.get_doc("Employee Location", filters)
    else:
        return frappe.get_doc({
            "doctype": "Employee Location",
            "employee": employee.get("name"),
            "date": date or frappe.utils.today()
        })

def update_location_doc(doc, location_data):
    """Update location document with new data"""
    try:
        # Add timestamp to each location point
        timestamp = datetime.now().isoformat()
        for feature in location_data["features"]:
            feature["properties"]["timestamp"] = timestamp
        
        # Update document
        doc.location_map = json.dumps(location_data)
        doc.save()
        
        # Log successful update
        frappe.logger().info(f"Location updated for employee {doc.employee}")
        
    except Exception as e:
        frappe.log_error(
            f"Error updating location document: {str(e)}",
            "Employee Location Update"
        )
        raise

def is_point_in_geofence(lat, lng, center_lat, center_lng, radius):
    """Check if a point is within the geofence"""
    from math import sin, cos, sqrt, atan2, radians
    
    # Convert coordinates to radians
    lat1, lng1, lat2, lng2 = map(radians, [lat, lng, center_lat, center_lng])
    
    # Calculate distance using Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = 6371 * c  # Earth's radius in km
    
    return distance <= radius
