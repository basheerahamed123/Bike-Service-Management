// Copyright (c) 2025, basheer and contributors
// For license information, please see license.txt

frappe.query_reports["Bike Service"] = {
	"filters": [
		{
			"fieldname": "customername",
			"label": ("Customer Name"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "vehiclenumber",
			"label": ("Vehicle Number"),
			"fieldtype": "Link",
			"options": "Vehicle Details"
		},
        {
			"fieldname": "servicerequestid",
			"label": ("Service Request ID"),
			"fieldtype": "Link",
			"options": "Service Request"
		},
		{
			"fieldname": "technician",
			"label": ("Technician"),
			"fieldtype": "Link",
			"options": "Technician"
		},	
	]
};
