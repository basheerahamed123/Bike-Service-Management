import frappe
from frappe.model.document import Document

class VehicleInspection(Document):
    def on_submit(self):
        self.create_job_card()

    def create_job_card(self):
        # Avoid duplicate creation if already exists
        if frappe.db.exists("Service Job Card", {"vehicleinspectionid": self.name}):
            frappe.msgprint("⚠️ A Service Job Card is already created for this inspection.")
            return

        job_card = frappe.new_doc("Service Job Card")

        # Basic field mappings
        job_card.service_request_id = self.service_request_id
        job_card.vehicle_number = self.vehicle_number
        job_card.inspection_date = self.inspection_date
        job_card.vehicle_inspector_name = self.vehicle_inspector_name
        job_card.customername = self.customername
        job_card.brand = self.brand
        job_card.model = self.model
        job_card.year = self.year
        job_card.photo_of_vehicle = self.photo_of_vehicle
        job_card.vehicleinspectionid = self.name

        # Add services
        for item in self.servicetype:
            job_card.append("servicetype", {
                "service": item.service,
                "serviceamount": item.serviceamount
            })

        # Add vehicle problems (only where 'is_present' is checked)
        for problem in self.vehicle_problems:
            if problem.is_present:
                job_card.append("vehicle_problems", {
                    "problem_type": problem.problem_type,
                    "is_present": problem.is_present,
                    "descriptionremarks": problem.descriptionremarks
                })

        # Save the job card
        job_card.insert(ignore_permissions=True)

        self.db_set('service_job_card', job_card.name)


        # 🔗 Link the job card back to the inspection
        self.service_job_card = job_card.name
        self.save(ignore_permissions=True)

        frappe.logger().info(f"[DEBUG] Service Job Card created: {job_card.name}")
        frappe.msgprint(f"✅ Service Job Card <b>{job_card.name}</b> created successfully.")



@frappe.whitelist()
def fetch_service_request_items(service_request_id):
    return frappe.get_all(
        "Job Service",
        filters={"parent": service_request_id},
        fields=["service", "serviceamount"]
    )


def get_permission_query_conditions(user):
    if not user:
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return ""

    roles = frappe.get_roles(user)

    conditions = []

    if "Technician" in roles:
        conditions.append(f"""
            EXISTS (
                SELECT 1 FROM `tabService Job Card`
                WHERE `tabService Job Card`.vehicleinspectionid = `tabVehicle Inspection`.name
                AND `tabService Job Card`.assigned_technician = '{employee}'
            )
        """)

    if "Vehicle Inspector" in roles:
        conditions.append(f"`tabVehicle Inspection`.vehicle_inspector_name = '{employee}'")

    if "Service Advisor" in roles:
        # Allow all or restrict based on your logic
        conditions.append("1=1")  # allow all

    return " OR ".join(f"({cond})" for cond in conditions)



