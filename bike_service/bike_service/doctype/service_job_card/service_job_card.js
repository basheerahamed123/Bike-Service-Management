frappe.ui.form.Form.prototype.get_docfield_names = function () {
    return this.meta.fields.map(f => f.fieldname).filter(f => !!f);
};


frappe.ui.form.on('Service Job Card', {
    onload: function(frm) {
        const roles = frappe.user_roles || [];

        // Lock all fields initially
        Object.keys(frm.fields_dict).forEach(fieldname => {
            frm.set_df_property(fieldname, 'read_only', 1);
        });

        // Technician access
        if (roles.includes("Technician")) {
            frm.set_df_property("additional_changes_to_be_done", "read_only", 0);
            frm.set_df_property("partsused", "read_only", 0);
            frm.set_df_property("partsused", "hidden", 0);  // ✅ Ensure it's shown
            frm.set_df_property("service_status", "read_only", 0);
        }

        // Service Advisor access
        if (roles.includes("Service Advisor")) {
            frm.set_df_property("status", "read_only", 0);
            frm.set_df_property("additional_changes_to_be_done", "read_only", 0);
            frm.set_df_property("service_status", "read_only", 1);

            let show_table = (frm.doc.additional_changes_to_be_done || []).some(row => row.additional_changes);
            frm.set_df_property("additional_changes_to_be_done", "hidden", !show_table);

            frm.set_df_property("assigned_technician", "read_only", !!frm.doc.assigned_technician);

            frm.set_query("assigned_technician", () => {
                return { filters: { designation: "Technician" } };
            });
        }

        // // Lock everything if Completed or Cancelled
        // if (["Completed", "Cancelled"].includes(frm.doc.status)) {
        //     Object.keys(frm.fields_dict).forEach(fieldname => {
        //         frm.set_df_property(fieldname, 'read_only', 1);
        //     });

        //     frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property('customer_remarks', 'read_only', 1);
        //     frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property('status_of_changes', 'read_only', 1);
        // }
    },

    refresh: function(frm) {
        if (frm.doc.docstatus == 0 && roles.includes("Service Advisor")){
            frm.set_df_property('service_status', 'read_only', 1);
        }
       
    },

    service_status: function(frm) {
        if (frm.doc.service_status === "Completed") {
            frm.set_df_property('service_status', 'read_only', 1);
        }
    },


    refresh(frm) {
        const is_technician = frappe.user_roles.includes("Technician");
        const is_advisor = frappe.user_roles.includes("Service Advisor");
        const is_final = ["Completed", "Cancelled"].includes(frm.doc.status);
        const is_submitted = frm.doc.docstatus === 1;

        if (frm.doc.service_status === "Completed") {
            frm.set_df_property('service_status', 'read_only', 1);
        } else {
            frm.set_df_property('service_status', 'read_only', 0);
        }

        if (is_advisor && is_submitted) {
            frm.set_df_property('service_status', 'read_only', 1);
        }

        // ===== 1. Lock Entire Form if Final =====
        if (is_submitted && is_final) {
            lock_all_fields(frm);
            frm.disable_save();
        }

        // ===== 2. Status Field Control =====
        frm.set_df_property("status", "read_only", !(is_advisor && !is_final));

        // ===== 3. Grid Field Control =====
        if (frm.fields_dict.additional_changes_to_be_done) {
            if (is_submitted) {
                if (is_technician) {
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("additional_changes", "read_only", 0);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("status_of_changes", "read_only", 1);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("customer_remarks", "read_only", 1);
                } else if (is_advisor && !is_final) {
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("additional_changes", "read_only", 1);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("status_of_changes", "read_only", 0);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("customer_remarks", "read_only", 0);
                } else {
                    lock_grid_fields(frm);
                }
            } else {
                // Before submit
                if (is_technician) {
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("additional_changes", "read_only", 0);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("status_of_changes", "read_only", 1);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("customer_remarks", "read_only", 1);
                } else if (is_advisor) {
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("additional_changes", "read_only", 1);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("status_of_changes", "read_only", 0);
                    frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("customer_remarks", "read_only", 0);
                }
            }
        }

        // ===== 4. Generate Invoice Button =====
        if (frm.doc.status === "Completed" && is_submitted) {
            frm.add_custom_button(__('Generate Invoice'), function () {
                frappe.call({
                    method: 'bike_service.bike_service.doctype.service_job_card.service_job_card.create_invoice',
                    args: { doc: frm.doc },
                    callback: function (r) {
                        if (!r.exc) {
                            if (r.message) {
                                frappe.show_alert({ message: __('✅ Invoice <b>{0}</b> created', [r.message]), indicator: 'green' });
                                frappe.set_route('Form', 'Sales Invoice', r.message);
                            } else {
                                frappe.show_alert({ message: __('Invoice already exists or could not be created.'), indicator: 'orange' });
                            }
                        }
                    }
                });
            }, __('Actions'));
        }
    },

    on_submit: function(frm) {
        const roles = frappe.user_roles || [];

        if (roles.includes("Service Advisor")) {
            frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property('customer_remarks', 'read_only', 0);
            frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property('status_of_changes', 'read_only', 0);
            frm.fields_dict.additional_changes_to_be_done.grid.refresh();
        }
    },


});

function lock_all_fields(frm) {
    frm.fields.forEach(field => {
        if (!["Section Break", "Column Break"].includes(field.df.fieldtype)) {
            frm.set_df_property(field.df.fieldname, 'read_only', 1);
        }
    });
    lock_grid_fields(frm);
}

function lock_grid_fields(frm) {
    if (frm.fields_dict.additional_changes_to_be_done) {
        frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("additional_changes", "read_only", 1);
        frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("status_of_changes", "read_only", 1);
        frm.fields_dict.additional_changes_to_be_done.grid.update_docfield_property("customer_remarks", "read_only", 1);
    }
}

frappe.ui.form.on("Additional Changes", {
    status_of_changes: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        frappe.call({
            method: "bike_service.bike_service.doctype.service_job_card.service_job_card.get_original_additional_change",
            args: {
                child_row_name: row.name
            },
            callback: function (r) {
                const db_row = r.message;
                if (["Approved", "Rejected"].includes(db_row.status_of_changes)) {
                    if (row.status_of_changes !== db_row.status_of_changes) {
                        frappe.msgprint("❌ Cannot change status. Already finalized.");
                        frappe.model.set_value(cdt, cdn, "status_of_changes", db_row.status_of_changes);
                    }
                }
            }
        });
    },

    customer_remarks: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        frappe.call({
            method: "bike_service.bike_service.doctype.service_job_card.service_job_card.get_original_additional_change",
            args: {
                child_row_name: row.name
            },
            callback: function (r) {
                const db_row = r.message;
                if (["Approved", "Rejected"].includes(db_row.status_of_changes)) {
                    if (row.customer_remarks !== db_row.customer_remarks) {
                        frappe.msgprint("❌ Cannot change remarks. Already finalized.");
                        frappe.model.set_value(cdt, cdn, "customer_remarks", db_row.customer_remarks);
                    }
                }
            }
        });
    }
});




