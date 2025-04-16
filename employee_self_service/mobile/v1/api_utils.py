import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import cstr

import wrapt


def gen_response(status, message, data=[]):
    frappe.response["http_status_code"] = status
    if status == 500:
        frappe.response["message"] = BeautifulSoup(str(message)).get_text()
    else:
        frappe.response["message"] = message
    frappe.response["data"] = data


def exception_handler(e):
    frappe.log_error(title="ESS Mobile App Error", message=frappe.get_traceback())
    if hasattr(e, "http_status_code"):
        return gen_response(e.http_status_code, BeautifulSoup(str(e)).get_text())
    else:
        return gen_response(500, BeautifulSoup(str(e)).get_text())


def generate_key(user):
    """Generate and persist API keys for a user.
    
    Args:
        user (str): User ID to generate keys for
        
    Returns:
        dict: Dictionary containing api_key and api_secret
    """
    try:
        # Log the user we're trying to update
        frappe.logger().debug(f"Generating API keys for user: {user}")
        
        # Get user document with all fields
        user_details = frappe.get_doc("User", user)
        frappe.logger().debug(f"Current user state - api_key: {bool(user_details.api_key)}, api_secret: {bool(user_details.api_secret)}")
        
        # Generate new keys if either is missing
        if not user_details.api_key or not user_details.api_secret:
            api_secret = frappe.generate_hash(length=15)
            api_key = frappe.generate_hash(length=15)
            
            frappe.logger().debug(f"Generated new keys - api_key: {api_key}, api_secret: {api_secret}")
            
            # Update both values in a single transaction
            frappe.db.begin()
            try:
                frappe.db.set_value("User", user, "api_key", api_key, update_modified=False)
                frappe.db.set_value("User", user, "api_secret", api_secret, update_modified=False)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                raise
            
            # Verify the values were saved
            saved_user = frappe.get_doc("User", user)
            if saved_user.api_key != api_key or saved_user.api_secret != api_secret:
                frappe.logger().error(f"Keys were not saved correctly for user {user}")
                raise Exception("Failed to persist API keys")
            
            frappe.logger().debug("API keys successfully saved")
            return {"api_secret": api_secret, "api_key": api_key}
        else:
            # Return existing keys
            return {
                "api_secret": user_details.get_password("api_secret"),
                "api_key": user_details.get("api_key")
            }
    except Exception as e:
        frappe.logger().error(f"API Key Generation Error for user {user}: {str(e)}")
        frappe.logger().error(frappe.get_traceback())
        raise


def ess_validate(methods):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if not frappe.local.request.method in methods:
            return gen_response(500, "Invalid Request Method")
        return wrapped(*args, **kwargs)

    return wrapper


def get_employee_by_user(user, fields=["name"]):
    if isinstance(fields, str):
        fields = [fields]
    emp_data = frappe.get_cached_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=1,
    )
    return emp_data


def validate_employee_data(employee_data):
    if not employee_data.get("company"):
        return gen_response(
            500,
            "Company not set in employee doctype. Contact HR manager for set company",
        )


def get_ess_settings():
    return frappe.get_doc(
        "Employee Self Service Settings", "Employee Self Service Settings"
    )


def get_global_defaults():
    return frappe.get_doc("Global Defaults", "Global Defaults")


def remove_default_fields(data):
    # Example usage:
    # remove_default_fields(
    #     json.loads(
    #         frappe.get_doc("Address", "name").as_json()
    #     )
    # )
    for row in [
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
        "idx",
        "doctype",
        "links",
    ]:
        if data.get(row):
            del data[row]
    return data


def prepare_json_data(key_list, data):
    return_data = {}
    for key in data:
        if key in key_list:
            return_data[key] = data.get(key)
    return return_data


def get_actions(doc, doc_data=None):
    from frappe.model.workflow import get_transitions

    if not frappe.db.exists(
        "Workflow", dict(document_type=doc.get("doctype"), is_active=1)
    ):
        doc_data["workflow_state"] = doc.get("status")
        return []
    transitions = get_transitions(doc)
    actions = []
    for row in transitions:
        actions.append(row.get("action"))
    return actions


def check_workflow_exists(doctype):
    doc_workflow = frappe.get_all(
        "Workflow",
        filters={"document_type": doctype, "is_active": 1},
        fields=["workflow_state_field"],
    )
    if doc_workflow:
        return doc_workflow[0].workflow_state_field
    else:
        return False


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(reference_doctype, reference_name, action):
    try:
        from frappe.model.workflow import apply_workflow

        doc = frappe.get_doc(reference_doctype, reference_name)
        apply_workflow(doc, action)
        return gen_response(200, "Workflow State Updated Successfully")
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {reference_doctype}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


def convert_timezone(timestamp, from_timestamp, time_zone):
    from pytz import UnknownTimeZoneError, timezone

    fromtimezone = timezone(from_timestamp).localize(timestamp)
    try:
        return fromtimezone.astimezone(timezone(time_zone))
    except UnknownTimeZoneError:
        return fromtimezone


def get_system_timezone() -> str:
    """Return the system timezone."""
    return (
        frappe.get_system_settings("time_zone") or "Asia/Kolkata"
    )  # Default to India ?!
