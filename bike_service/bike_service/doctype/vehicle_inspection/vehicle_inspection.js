frappe.ui.form.on('Vehicle Inspection', {
    onload: function(frm) {
        // Make form read-only for everyone except Vehicle Inspector
        if (!frappe.user_roles.includes("Vehicle Inspector")) {
            frm.fields.forEach(function(field) {
                frm.set_df_property(field.df.fieldname, 'read_only', 1);
            });
        }

        // Auto-fill checklist only for new docs
        if (frm.is_new() && !frm.__default_checklist_added) {
            let default_problems = [
                "Odometer Check",
                "Brake Condition",
                "Oil Leakage",
                "Tyre Condition",
                "Chain Tightness",
                "Lights & Indicators",
                "Battery Health",
                "Suspension Check",
                "Customer Remarks",
            ];

            frm.clear_table('vehicle_problems');

            default_problems.forEach(problem => {
                let row = frm.add_child('vehicle_problems');
                row.problem_type = problem;
                row.is_present = 0;
                row.description_remarks = '';
            });

            frm.refresh_field('vehicle_problems');
            frm.__default_checklist_added = true;
        }

        frm.set_query('service_request_id', function() {
            return {
                filters: {
                    status: 'Accepted',
                    status_of_service: ['!=', 'Completed']
                }
            };
        });
        
    },

    service_request_id: function(frm) {
        if (frm.doc.service_request_id) {
            frappe.call({
                method: "bike_service.bike_service.doctype.vehicle_inspection.vehicle_inspection.fetch_service_request_items",
                args: {
                    service_request_id: frm.doc.service_request_id
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table("servicetype");
                        r.message.forEach(item => {
                            let row = frm.add_child("servicetype");
                            row.service = item.service;
                            row.serviceamount = item.serviceamount;
                        });
                        frm.refresh_field("servicetype");
                    }
                }
            });
        }
    },

    refresh: function(frm) {
        // Show button only if Service Advisor and job card exists
        if (frappe.user_roles.includes('Service Advisor') && frm.doc.service_job_card) {
            frm.add_custom_button('View Job Card', () => {
                frappe.set_route('Form', 'Service Job Card', frm.doc.service_job_card);
            }, __('Actions'));
        }
    }
});

