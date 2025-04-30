import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Vehicle Inspection ID", "fieldname": "vehicleinspectionid", "fieldtype": "Link", "options": "Vehicle Inspection", "width": 150},
        {"label": "Customer Name", "fieldname": "customername", "fieldtype": "Data", "width": 150},
        {"label": "Vehicle Number", "fieldname": "vehicle_number", "fieldtype": "Link", "options": "Vehicle Details", "width": 120},
        {"label": "Service Request ID", "fieldname": "service_request_id", "fieldtype": "Link", "options": "Service Request", "width": 140},
        {"label": "Brand", "fieldname": "brand", "fieldtype": "Data", "width": 150},
        {"label": "Model", "fieldname": "model", "fieldtype": "Data", "width": 150},
        {"label": "Year", "fieldname": "year", "fieldtype": "Data", "width": 80},
        {"label": "Services", "fieldname": "service_details", "fieldtype": "Data", "width": 250},
        {"label": "Parts Used", "fieldname": "parts_used", "fieldtype": "Data", "width": 250},
        {"label": "Total Service Amount", "fieldname": "total_service_amount", "fieldtype": "Currency", "width": 140},
        {"label": "Total Parts Amount", "fieldname": "total_parts_amount", "fieldtype": "Currency", "width": 140},
        {"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency", "width": 140},
        {"label": "Status", "fieldname": "status", "fieldtype": "Select", "options": "Open\nCompleted\nCancelled", "width": 120},
    ]

def get_data(filters):
    query = """
        SELECT
            s.vehicleinspectionid, 
            s.customername,
            s.vehicle_number,
            s.service_request_id,
            s.brand,
            s.model,
            s.year,
            s.status,

            GROUP_CONCAT(DISTINCT CONCAT(sl.service, ' (₹', ROUND(sl.serviceamount, 2), ')') SEPARATOR ', ') AS service_details,
            GROUP_CONCAT(DISTINCT CONCAT(sle.item, ' x', sle.quantity, ' (₹', ROUND(sle.itemamount, 2), ')') SEPARATOR ', ') AS parts_used,

            ROUND(SUM(DISTINCT sl.serviceamount), 2) AS total_service_amount,
            ROUND(SUM(DISTINCT sle.itemamount), 2) AS total_parts_amount,
            ROUND(SUM(DISTINCT sl.serviceamount) + SUM(DISTINCT sle.itemamount), 2) AS total_amount

        FROM `tabService Job Card` AS s
        LEFT JOIN `tabJob Service` AS sl ON sl.parent = s.name
        LEFT JOIN `tabParts Used` AS sle ON sle.parent = s.name
        GROUP BY s.name
        ORDER BY s.creation DESC
    """
    return frappe.db.sql(query, as_dict=True)
