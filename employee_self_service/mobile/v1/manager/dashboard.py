import frappe
import json
from frappe import _
from frappe.utils import pretty_date, getdate, fmt_money
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
    get_global_defaults,
)
from employee_self_service.mobile.v1.manager.manager_utils import get_action


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats():
    try:
        stats = {
            "clock_in": 48,
            "clock_out": 10,
            "not_clock_in": 7,
            "on_leave": 10,
            "approval": 13,
            "tasks": 40
        }
        return gen_response(200, "Stats get successfully", stats)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats_list(type):
    try:
        data = [
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
        ]
        return gen_response(200, "Stats get successfully", data)
    except Exception as e:
        return exception_handler(e)