frappe.ui.form.on('Service Request', {
    onload: function(frm) {
        // Service Advisor View
        if (frappe.user_roles.includes("Service Advisor")) {
            frm.set_df_property('assigned_vehicle_inspector', 'hidden', 0);
            frm.set_df_property('assigned_vehicle_inspector', 'read_only', 0);

            frm.set_df_property('status', 'read_only', 1);

            frm.set_df_property('customername', 'hidden', 0);
            frm.set_df_property('vehiclenumber', 'hidden', 0);
            frm.set_df_property('requesteddate', 'hidden', 0);
            frm.set_df_property('servicetype', 'hidden', 0);

            frm.set_df_property('customername', 'read_only', 1);
            frm.set_df_property('vehiclenumber', 'read_only', 1);
            frm.set_df_property('requesteddate', 'read_only', 1);
            frm.set_df_property('servicetype', 'read_only', 1);

            frm.set_df_property('confirmation_through_call', 'hidden', 0);
            frm.set_df_property('confirmation_through_call', 'read_only', 0);

            frm.set_df_property('advisor_updated', 'read_only', 0);
            frm.set_df_property('advisor_updated', 'hidden', 1);

            frm.set_query("assigned_vehicle_inspector", function() {
                return {
                    filters: {
                        designation: "Vehicle Inspector",
                        status: "Active"
                    }
                };
            });
        }

        // Vehicle Inspector View
        else if (frappe.user_roles.includes("Vehicle Inspector")) {
            frm.set_df_property('confirmation_through_call', 'hidden', 0);
            frm.set_df_property('confirmation_through_call', 'read_only', 1);

            frm.set_df_property('assigned_vehicle_inspector', 'hidden', 0);
            frm.set_df_property('assigned_vehicle_inspector', 'read_only', 1);

            frm.set_df_property('status', 'read_only', 1);
            frm.set_df_property('advisor_updated', 'hidden', 1);
        }

        // Customer or Other Roles View
        else {
            frm.set_df_property('assigned_vehicle_inspector', 'hidden', 1);
            frm.set_df_property('confirmation_through_call', 'hidden', 1);
            frm.set_df_property('confirmation_through_call', 'read_only', 1);
            frm.set_df_property('status', 'read_only', 1);
            frm.set_df_property('advisor_updated', 'hidden', 1);
        }
    },

    validate(frm) {
        let seen = new Set();
        let duplicates = [];

        frm.doc.servicetype.forEach(row => {
            if (seen.has(row.service)) {
                duplicates.push(row.service);
            } else {
                seen.add(row.service);
            }
        });

        if (duplicates.length > 0) {
            frappe.throw(`Duplicate services selected: ${[...new Set(duplicates)].join(", ")}`);
        }
    },

    // Auto-set status when confirmation is changed
    confirmation_through_call: function(frm) {
        if (frm.doc.confirmation_through_call === "Confirmed") {
            frm.set_value('status', 'Accepted');
        } else if (frm.doc.confirmation_through_call === "Rejected") {
            frm.set_value('status', 'Rejected');
        }
    },

    status: function(frm) {
        if (frm.doc.status === "Accepted") {
            frm.set_value('confirmation_through_call', 'Confirmed');
        } else if (frm.doc.status === "Rejected") {
            frm.set_value('confirmation_through_call', 'Rejected');
        }
    },

    assigned_vehicle_inspector: function(frm) {
        if (frm.doc.assigned_vehicle_inspector && !frm.doc.advisor_updated) {
            frm.set_value("advisor_updated", 1);
        }
    },

    // Lock fields after advisor update
    refresh: function(frm) {
        if (frappe.user_roles.includes('Service Advisor')) {
            if (frm.doc.advisor_updated) {
                make_advisor_fields_readonly(frm);
                frm.set_df_property('advisor_updated', 'read_only', 1);
                console.log("🔒 Fields made read-only for advisor");
            } else {
                console.log("✏️ Advisor can edit fields");
            }
        }

        // Customer can't uncheck advisor_updated if already set
        if (frappe.user_roles.includes('Customer') && frm.doc.advisor_updated) {
            frm.set_df_property('advisor_updated', 'read_only', 1);
        }

        if (frappe.user_roles.includes('Vehicle Inspector') 
            && frm.doc.confirmation_through_call == "Confirmed") {
                
            frm.add_custom_button('Go to Vehicle Inspection', () => {
                frappe.new_doc('Vehicle Inspection', {
                    service_request_id: frm.doc.name  // Passing current Service Request ID
                });
            });
        }
    },

    // Check if advisor modified anything before save
    before_save: function(frm) {
        if (frappe.user_roles.includes('Service Advisor') && !frm.doc.advisor_updated) {
            const changed_inspector = frm.doc.__unsaved && frm.doc.assigned_vehicle_inspector !== frm.doc.__last_saved?.assigned_vehicle_inspector;
            const changed_call = frm.doc.__unsaved && frm.doc.confirmation_through_call !== frm.doc.__last_saved?.confirmation_through_call;
            const changed_status = frm.doc.__unsaved && frm.doc.status !== frm.doc.__last_saved?.status;

            if (changed_inspector || changed_call || changed_status) {
                frm.set_value('advisor_updated', 1);
                frappe.msgprint("✅ Advisor has updated fields. Locking them after this.");
            }
        }
    }
});

// Helper function to lock fields after update
function make_advisor_fields_readonly(frm) {
    const fields = ['assigned_vehicle_inspector', 'confirmation_through_call', 'status'];
    fields.forEach(field => {
        frm.set_df_property(field, 'read_only', 1);
        frm.refresh_field(field);
    });
}

frappe.ui.form.on('Service Type', {
    service_name(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const current_service = row.servicename;

        if (!current_service) return;

        let count = 0;

        // Loop through all rows to count how many times this service is selected
        frm.doc.servicetype.forEach(service => {
            if (service.servicename === current_service) {
                count++;
            }
        });

        if (count > 1) {
            frappe.msgprint(`"${current_service}" is already selected. Please select it only once.`);
            frappe.model.set_value(cdt, cdn, 'servicename', null);
        }
    }
});


