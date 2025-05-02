import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from frappe import _


class ServiceJobCard(Document):

    def before_save(self):
        # Block reassignment of technician
        if self.get_db_value("assigned_technician") and self.get_db_value("assigned_technician") != self.assigned_technician:
            frappe.throw(_("Technician has already been assigned and cannot be changed."))

        # Create ToDo when technician is assigned for the first time
        if not self.get_db_value("assigned_technician") and self.assigned_technician:
            self.create_todo = True  # Flag to use in on_update

        if self.is_new() or self.has_value_changed("assigned_technician"):
            if self.assigned_technician:
                self.send_technician_todo()



        # 2. Lock the entire document if it was already marked Completed
        if self.name and frappe.db.exists(self.doctype, self.name):
            old_doc = frappe.get_doc(self.doctype, self.name)
            if old_doc.status == "Completed":
                for field in self.meta.get_valid_columns():
                    if field not in ["modified", "modified_by", "owner", "creation"]:
                        if self.get(field) != old_doc.get(field):
                            frappe.throw(_("You cannot modify the document after it is marked as Completed."))

        if self.name and frappe.db.exists(self.doctype, self.name):
            old_doc = frappe.get_doc(self.doctype, self.name)
            if old_doc.status == "Cancelled":
                for field in self.meta.get_valid_columns():
                    if field not in ["modified", "modified_by", "owner", "creation"]:
                        if self.get(field) != old_doc.get(field):
                            frappe.throw(_("You cannot modify the document because it is Cancelled"))

        for row in self.additional_changes_to_be_done:
            if not row.name:
                continue  # skip unsaved rows

            db_row = frappe.db.get_value(
                "Additional Changes",
                row.name,
                ["status_of_changes", "customer_remarks"],
                as_dict=True
            )

            if db_row:
                if db_row.status_of_changes in ["Approved", "Rejected"]:
                    if row.status_of_changes != db_row.status_of_changes or row.customer_remarks != db_row.customer_remarks:
                        frappe.throw(
                            _("You cannot modify status or customer remarks for rows that are already Approved or Rejected.")
                        )

    def on_update_after_submit(self):
        for row in self.additional_changes_to_be_done:
            db_row = frappe.db.get_value(
                "Additional Changes",
                row.name,
                ["status_of_changes", "customer_remarks"],
                as_dict=True
            )

            if db_row:
                if db_row.status_of_changes in ["Approved", "Rejected"]:
                    # Compare and throw if tampered
                    if (
                        row.status_of_changes != db_row.status_of_changes or
                        row.customer_remarks != db_row.customer_remarks
                    ):
                        frappe.throw("❌ You cannot update Approved or Rejected rows.")

    def on_change(self):
        if self.service_request_id and self.status in ["Completed", "Cancelled"]:
            service_request = frappe.get_doc("Service Request", self.service_request_id)
            
            if self.status == "Completed":
                frappe.db.set_value("Service Request", self.service_request_id, "status_of_service", "Completed")
            elif self.status == "Cancelled":
                frappe.db.set_value("Service Request", self.service_request_id, "status_of_service", "Cancelled")
            frappe.db.commit()


    def send_technician_todo(self):
        user = frappe.db.get_value("Employee", self.assigned_technician, "user_id")
        if not user:
            frappe.log_error(f"No user ID found for technician {self.assigned_technician}", "ToDo Creation Error")
            return

        # Ensure the document is saved and has a name
        if not self.name:
            frappe.throw("Document must be saved before creating ToDo")

        existing = frappe.db.exists("ToDo", {
            "owner": user,
            "reference_type": "Service Job Card",
            "reference_name": self.name
        })

        if not existing:
            try:
                todo = frappe.get_doc({
                    "doctype": "ToDo",
                    "owner": user,
                    "allocated_to": user,
                    "description": f"You have been assigned to work on Job Card: {self.name}",
                    "reference_type": "Service Job Card",
                    "reference_name": self.name,
                    "priority": "Medium",
                    "status": "Open",
                    "date": self.get("start_time") or nowdate()
                }).insert(ignore_permissions=True)

                frappe.publish_realtime(
                    event="new_todo_notification",
                    message=f"You have a new ToDo: {todo.description}",
                    user=user
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "ToDo Creation Failed")



def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    if "Technician" in roles:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if employee:
            return "(`tabService Job Card`.assigned_technician = '{0}')".format(employee)
    return None


@frappe.whitelist()
def create_invoice(doc, method=None):

    if frappe.flags.in_job_card_submission:
        return  # Prevent auto-call during submission

    if "Billing/Cashier" not in frappe.get_roles():
        frappe.throw("❌ Only users with the 'Billing/Cashier' role can generate invoices.")

    if isinstance(doc, str):
        doc = frappe.parse_json(doc)

    if doc.get("doctype") != "Service Job Card":
        return

    doc_name = doc.get("name")
    if not doc_name:
        frappe.throw(_("Missing document name in request."))

    service_doc = frappe.get_doc("Service Job Card", doc_name)

    if service_doc.status != "Completed":
        return

    existing_invoice = frappe.db.exists("Sales Invoice Item", {
        "custom_service_job_card": service_doc.name
    })

    if existing_invoice:
        frappe.msgprint(f"Invoice already exists: <b>{existing_invoice}</b>")
        return existing_invoice

    company_name = "Pontus PPL"
    income_account = "Basheer - PP"

    checkbox_fields = {
        "odometer_check": "Odometer Check",
        "electricals_check": "Electricals Check",
        "engine_check": "Engine Check",
        "brake_test": "Brake Test",
        "suspension_check": "Suspension Check",
        "battery_check": "Battery Check",
        "tyre_check": "Tyre Check"
    }

    checked_services = [label for field, label in checkbox_fields.items() if getattr(service_doc, field, 0)]
    checked_services_text = ""
    if checked_services:
        checked_services_text = "\nServices Checked:\n- " + "\n- ".join(checked_services)

    common_description = f"""Vehicle Number: {service_doc.vehicle_number}
Service Request ID: {service_doc.service_request_id}
{checked_services_text}
"""

    try:
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = service_doc.customername
        invoice.due_date = frappe.utils.nowdate()
        invoice.company = company_name

        # Add services
        if service_doc.servicetype:
            for service in service_doc.servicetype:
                invoice.append("items", {
                    "item_name": service.service,
                    "qty": 1,
                    "rate": service.serviceamount,
                    "custom_service_job_card": service_doc.name,
                    "description": f"Service: {service.service}\n{common_description}",
                    "income_account": income_account
                })

        # Add parts used
        if service_doc.partsused:
            for part in service_doc.partsused:
                invoice.append("items", {
                    "item_name": part.item,
                    "qty": part.quantity or 1,
                    "rate": part.itemamount,
                    "description": f"Part: {part.item}\n{common_description}",
                    "income_account": income_account
                })

        # # Add additional changes with editable charge amount
        # if service_doc.additional_changes_to_be_done:
        #     for change in service_doc.additional_changes_to_be_done:
        #         if change.status_of_changes == "Approved":
        #             charge_amount = change.charge_amount if hasattr(change, 'charge_amount') else 0
        #             row = invoice.append("items", {
        #                 "item_name": change.additional_changes,
        #                 "qty": 1,
        #                 "rate": charge_amount,  # Using the charge_amount
        #                 "description": f"Additional Change: {change.additional_changes}\n{common_description}",
        #                 "income_account": income_account
        #             })

        #             # Make the `rate` field editable after appending the item row
        #             row.set("rate", charge_amount)

        invoice.insert(ignore_permissions=True)

        # Make sure the `rate` field in the items is editable
        for item in invoice.items:
            item.set('rate', item.rate)  # Ensure that rate is editable

        # invoice.submit()

        frappe.msgprint(f"Invoice <b>{invoice.name}</b> created successfully.")
        return invoice.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Invoice Creation Error")
        frappe.throw(_("Failed to create invoice: {0}").format(str(e)))


@frappe.whitelist()
def trigger_request_notification(job_card):
    # Fetching users who have "Service Advisor" role from the "Has Role" doctype
    advisors = frappe.db.get_all(
        "User",
        fields=["name"],
        filters={
            "name": ["in", frappe.db.get_all("Has Role", filters={"role": "Service Advisor"}, pluck="parent")]
        },
        distinct=True
    )

    # If advisors are found, trigger a notification or create a ToDo
    if advisors:
        for advisor in advisors:
            # Example: Create a ToDo for the advisor
            todo = frappe.get_doc({
                "doctype": "ToDo",
                "owner": advisor["name"],
                "description": f"New request from job card {job_card} requires your attention.",
                "reference_type": "Service Job Card",
                "reference_name": job_card,
                "status": "Open"
            }).insert(ignore_permissions=True)

            # Optionally publish real-time event to notify the user
            frappe.publish_realtime(
                event="new_request_notification",
                message=f"Request from Job Card {job_card} assigned to {advisor['name']}",
                user=advisor["name"]
            )


@frappe.whitelist()
def update_additional_change_row(parent_name, child_row_name, new_status, new_remarks):
    parent_doc = frappe.get_doc("Service Job Card", parent_name)

    for row in parent_doc.additional_changes_to_be_done:
        if row.name == child_row_name:
            # Get existing values from DB
            db_row = frappe.db.get_value(
                "Additional Changes",
                row.name,
                ["status_of_changes", "customer_remarks"],
                as_dict=True
            )

            if not db_row:
                frappe.throw(_("Row not found."))

            # Once changed from 'Pending' to 'Approved' or 'Rejected', it is final
            if db_row.status_of_changes in ["Approved", "Rejected"]:
                if new_status != db_row.status_of_changes or new_remarks != db_row.customer_remarks:
                    frappe.throw(_("❌ You cannot modify a row once it is marked Approved or Rejected."))

            # Prevent switching between Approved and Rejected
            if db_row.status_of_changes == "Approved" and new_status == "Rejected":
                frappe.throw(_("❌ You cannot change status from Approved to Rejected."))

            if db_row.status_of_changes == "Rejected" and new_status == "Approved":
                frappe.throw(_("❌ You cannot change status from Rejected to Approved."))

            # Allow updates only for pending or first-time set
            row.status_of_changes = new_status
            row.customer_remarks = new_remarks

    parent_doc.save(ignore_permissions=True)
    frappe.msgprint("✅ Row updated successfully.")

@frappe.whitelist()
def get_original_additional_change(child_row_name):
    row = frappe.db.get_value(
        "Additional Changes",
        child_row_name,
        ["status_of_changes", "customer_remarks"],
        as_dict=True
    )
    if not row:
        frappe.throw("Row not found.")
    return row

  
