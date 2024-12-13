import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import cint,get_url_to_form
from operator import itemgetter
from frappe.model.workflow import get_transitions



@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_active_workflow_document(internal=False):
    try:
        all_workflows = []
        workflows = frappe.get_all("Workflow",filters={"is_active":1},fields=["document_type"])
        if internal:
            return workflows
        all_workflows.append({"document_type":"All"})
        all_workflows.extend(workflows)
        return gen_response(200,"Active Workflow document get successfully",all_workflows)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read Timesheet")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_workflow_documents(start=1, page_length=10,document_type=None,internal=False):
    try:
        documents = []
        if document_type == "All" or not document_type:
            workflows = get_active_workflow_document(internal=True)

            for row in workflows:
                workflow_documents = frappe.get_list(row.document_type, filters={}, fields=["name", "workflow_state", "modified"], order_by="modified desc")
                append_document(workflow_documents=workflow_documents, documents=documents, doctype=row.document_type)
        else:
            workflow_documents = frappe.get_list(document_type, filters={}, fields=["name", "workflow_state", "modified"], order_by="modified desc")
            append_document(workflow_documents=workflow_documents, documents=documents, doctype=document_type)
            
        if internal:
            return len(documents)
        # Sort documents by modified date
        documents.sort(key=itemgetter("modified"), reverse=True)

        # Pagination
        start_index = (cint(start) - 1) * cint(page_length)
        end_index = min(start_index + cint(page_length), len(documents))
        paginated_documents = documents[start_index:end_index]

        return gen_response(200, "Workflow documents fetched successfully", paginated_documents)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read Timesheet")
    except Exception as e:
        return exception_handler(e)

def append_document(workflow_documents, documents, doctype):
    for row in workflow_documents:
        doc = frappe.get_doc(doctype, row["name"])
        try:
            transitions = get_transitions(doc)
            # Only append documents that have available actions (transitions)
            if transitions:
                row["doctype"] = doctype
                documents.append(row)
        except Exception as e:
            pass

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_actions(document_type,document_no):
    try:
        doc = frappe.get_doc(document_type,document_no)

        transitions = get_transitions(doc)
        actions = []
        for row in transitions:
            actions.append(row.get("action"))
        return gen_response(200,"Document action list get successfully",actions)
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for action")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(document_type, document_no, action):
    try:
        from frappe.model.workflow import apply_workflow

        doc = frappe.get_doc(document_type, document_no)
        apply_workflow(doc, action)
        return gen_response(200, "Workflow State Updated Successfully")
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {document_type}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_erp_link_for_document(document_type,document_no):
    try:
        return gen_response(200,"Document link get successfully",get_url_to_form(document_type, document_no))
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_print(document_type,document_no):
    try:
        default_print_format = frappe.db.get_value("Property Setter",dict(property="default_print_format", doc_type=document_type),"value") or "Standard"
        from frappe.utils.print_format import download_pdf

        return download_pdf(
            doctype=document_type,
            name=document_no,
            format=default_print_format,
        )
    except Exception as e:
        return exception_handler(e)
    