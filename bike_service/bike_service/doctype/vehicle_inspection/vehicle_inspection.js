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

    validate(frm) {
        let seen = new Set();
        let duplicates = [];
    
        frm.doc.vehicle_problems.forEach(row => {
            if (seen.has(row.problem_type)) {
                duplicates.push(row.problem_type);
            } else {
                seen.add(row.problem_type);
            }
        });
    
        if (duplicates.length > 0) {
            frappe.throw(`Duplicate problems selected: ${[...new Set(duplicates)].join(", ")}`);
        }
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

frappe.ui.form.on('Vehicle Problem Checklist', {
    problem_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const current_problem = row.problem_type;

        if (!current_problem) return;

        let count = 0;

        // Check how many times the same problem_type is selected
        frm.doc.vehicle_problems.forEach(problem => {
            if (problem.problem_type === current_problem) {
                count++;
            }
        });

        if (count > 1) {
            frappe.msgprint(`"${current_problem}" is already selected. Please select it only once.`);
            frappe.model.set_value(cdt, cdn, 'problem_type', null);
        }
    }
});

