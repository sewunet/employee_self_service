// Copyright (c) 2023, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Office Geofencing', {
	refresh: function(frm) {
		// Add map view button
		frm.add_custom_button(__('View on Map'), function() {
			show_map(frm);
		});

		// Add button to check employee locations
		frm.add_custom_button(__('Check Employee Locations'), function() {
			check_employee_locations(frm);
		});

		// Add validation for coordinates
		frm.set_query('latitude', function() {
			return {
				filters: {
					'latitude': ['between', [-90, 90]]
				}
			};
		});

		frm.set_query('longitude', function() {
			return {
				filters: {
					'longitude': ['between', [-180, 180]]
				}
			};
		});

		// Add validation for radius
		frm.set_query('radius', function() {
			return {
				filters: {
					'radius': ['>', 0]
				}
			};
		});

		// Add custom field for location history
		if (!frm.fields_dict.location_history) {
			frm.add_custom_field('location_history', {
				fieldname: 'location_history',
				label: __('Location History'),
				fieldtype: 'HTML',
				read_only: 1
			});
		}
	},

	validate: function(frm) {
		// Validate coordinates
		if (frm.doc.latitude < -90 || frm.doc.latitude > 90) {
			frappe.throw(__('Latitude must be between -90 and 90 degrees'));
		}
		if (frm.doc.longitude < -180 || frm.doc.longitude > 180) {
			frappe.throw(__('Longitude must be between -180 and 180 degrees'));
		}
		if (frm.doc.radius <= 0) {
			frappe.throw(__('Radius must be greater than 0'));
		}
	}
});

function show_map(frm) {
	// Create map container
	let map_container = $('<div>')
		.css({
			'height': '400px',
			'width': '100%',
			'margin': '10px 0'
		});

	// Add map container to form
	frm.fields_dict.map_html.$wrapper.empty().append(map_container);

	// Initialize map
	let map = L.map(map_container[0]).setView([frm.doc.latitude || 0, frm.doc.longitude || 0], 13);
	L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
		attribution: '© OpenStreetMap contributors'
	}).addTo(map);

	// Add marker for office location
	let marker = L.marker([frm.doc.latitude || 0, frm.doc.longitude || 0], {
		draggable: true
	}).addTo(map);
	
	// Add circle for geofence
	let circle = L.circle([frm.doc.latitude || 0, frm.doc.longitude || 0], {
		color: 'red',
		fillColor: '#f03',
		fillOpacity: 0.2,
		radius: frm.doc.radius || 100
	}).addTo(map);

	// Update marker and circle on form changes
	frm.doc.latitude && frm.doc.longitude && marker.setLatLng([frm.doc.latitude, frm.doc.longitude]);
	frm.doc.radius && circle.setRadius(frm.doc.radius);

	// Add event listeners
	marker.on('dragend', function(e) {
		let newLatLng = e.target.getLatLng();
		frm.set_value('latitude', newLatLng.lat);
		frm.set_value('longitude', newLatLng.lng);
		circle.setLatLng(newLatLng);
	});

	// Add radius control
	let radius_control = L.control.radius({
		position: 'topleft',
		circle: circle,
		onChange: function(radius) {
			frm.set_value('radius', radius);
		}
	});
	map.addControl(radius_control);

	// Add employee location markers if available
	if (frm.doc.location_history) {
		try {
			const locationData = JSON.parse(frm.doc.location_history);
			if (locationData.features && locationData.features[0].geometry.coordinates) {
				const coordinates = locationData.features[0].geometry.coordinates;
				coordinates.forEach((coord, index) => {
					L.circleMarker(coord, {
						radius: 5,
						color: '#3388ff',
						fillColor: '#3388ff',
						fillOpacity: 0.7
					}).addTo(map).bindPopup(`Location ${index + 1}`);
				});
			}
		} catch (e) {
			console.error('Error parsing location history:', e);
		}
	}
}

function check_employee_locations(frm) {
	frappe.call({
		method: 'employee_self_service.mobile.v1.location.user_location',
		args: {
			date: frappe.datetime.get_today()
		},
		callback: function(r) {
			if (r.message) {
				frm.set_value('location_history', JSON.stringify(r.message));
				show_map(frm);
			}
		}
	});
}

// Helper function to check if a point is within the geofence
function is_point_in_geofence(lat, lng, center_lat, center_lng, radius) {
	const R = 6371; // Earth's radius in km
	const dLat = toRad(lat - center_lat);
	const dLng = toRad(lng - center_lng);
	const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
			  Math.cos(toRad(center_lat)) * Math.cos(toRad(lat)) *
			  Math.sin(dLng/2) * Math.sin(dLng/2);
	const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
	const distance = R * c;
	return distance <= radius;
}

function toRad(degrees) {
	return degrees * Math.PI / 180;
}
