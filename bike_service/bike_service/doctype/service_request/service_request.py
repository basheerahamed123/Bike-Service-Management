import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class ServiceRequest(Document):
    def on_update_after_submit(self):
        frappe.logger().info("[DEBUG] Running before_save for Service Request")

        # Ensure it's a Service Advisor making the update
        user_roles = frappe.get_roles(frappe.session.user)
        frappe.logger().info(f"[DEBUG] Current user: {frappe.session.user}, Roles: {user_roles}")

        if "Service Advisor" not in user_roles:
            frappe.logger().info("[DEBUG] Current user is not a Service Advisor. Skipping assignment.")
            return

        # Only run if advisor has updated the fields
        if not self.advisor_updated:
            frappe.logger().info("[DEBUG] advisor_updated is not set. Skipping assignment.")
            return

        # Proceed only if vehicle inspector is assigned
        if not self.assigned_vehicle_inspector:
            frappe.logger().warning("[WARNING] No Vehicle Inspector assigned.")
            return

        # Fetch user_id from Employee
        user = frappe.db.get_value("Employee", self.assigned_vehicle_inspector, "user_id")
        frappe.logger().info(f"[DEBUG] User ID from Employee: {user}")

        if not user:
            frappe.logger().warning(f"[WARNING] No user_id found for Employee: {self.assigned_vehicle_inspector}")
            return

        # Check if ToDo already exists
        existing = frappe.db.exists("ToDo", {
            "owner": user,
            "reference_type": "Service Request",
            "reference_name": self.name
        })
        frappe.logger().info(f"[DEBUG] Existing ToDo found: {existing}")

        if existing:
            frappe.logger().info("[DEBUG] ToDo already exists, skipping creation.")
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

        frappe.logger().info(f"[DEBUG] New ToDo created: {todo.name}")

        # Send real-time notification
        frappe.publish_realtime(
            event="new_todo_notification",
            message=f"You have a new ToDo: {todo.description}",
            user=user
        )

        frappe.logger().info(f"[DEBUG] Realtime event triggered for user: {user}")

    def before_save(self):
        if self.confirmation_through_call == "Confirmed":
            self.status = "Accepted"
        elif self.confirmation_through_call == "Rejected":
            self.status = "Rejected"

        if self.status == "Accepted":
            self.confirmation_through_call = "Confirmed"
        elif self.status == "Rejected":
            self.confirmation_through_call = "Rejected"

    def fix_confirmation_status_mismatch():
        docs = frappe.get_all("Service Request", fields=["name", "confirmation_through_call", "status"])
        for d in docs:
            doc = frappe.get_doc("Service Request", d.name)
            updated = False

            if doc.confirmation_through_call == "Confirmed" and doc.status != "Accepted":
                doc.status = "Accepted"
                updated = True
            elif doc.confirmation_through_call == "Rejected" and doc.status != "Rejected":
                doc.status = "Rejected"
                updated = True
            elif doc.status == "Accepted" and doc.confirmation_through_call != "Confirmed":
                doc.confirmation_through_call = "Confirmed"
                updated = True
            elif doc.status == "Rejected" and doc.confirmation_through_call != "Rejected":
                doc.confirmation_through_call = "Rejected"
                updated = True

            if updated:
                doc.flags.ignore_permissions = True
                doc.save()

        frappe.db.commit()
        print("Fixed confirmation and status mismatches.")
            
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

