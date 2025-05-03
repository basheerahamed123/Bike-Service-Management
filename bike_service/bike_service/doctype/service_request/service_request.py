import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from frappe.utils import nowdate


class ServiceRequest(Document):

    def on_update_after_submit(self):
        # Get the user ID (email) linked to the employee
        user = frappe.db.get_value("Employee", self.assigned_vehicle_inspector, "user_id")

        if not user:
            frappe.throw(f"⚠️ No user ID found for employee: {self.assigned_vehicle_inspector}")

        # Check if a ToDo already exists for this Service Request
        existing = frappe.db.exists("ToDo", {
            "owner": user,
            "reference_type": "Service Request",
            "reference_name": self.name
        })

        if existing:
            return

        # Create new ToDo
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "owner": user,
            "allocated_to": user,
            "description": f"You have been assigned to inspect Service Request: {self.name}",
            "assigned_by": frappe.session.user,
            "reference_type": "Service Request",
            "reference_name": self.name,
            "priority": "Medium",
            "status": "Open",
            "date": self.get("requesteddate") or nowdate()
        }).insert(ignore_permissions=True)

        # Send real-time notification
        frappe.publish_realtime(
            event="new_todo_notification",
            message=f"You have a new ToDo: {todo.description}",
            user=user
        )
            
    def on_change(self):
        if self.confirmation_through_call == "Confirmed":
            frappe.db.set_value("Service Request", self.name, "status", "Accepted")
        elif self.confirmation_through_call == "Rejected":
            frappe.db.set_value("Service Request", self.name, "status", "Rejected")
        
def get_permission_query_conditions(user):
    if not user: user = frappe.session.user

    roles = frappe.get_roles(user)
    if "Vehicle Inspector" in roles:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if employee:
            return f"""(`tabService Request`.assigned_vehicle_inspector = '{employee}')"""
    return None

