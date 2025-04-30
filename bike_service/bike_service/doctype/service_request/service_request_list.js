frappe.listview_settings['Service Request'] = {
    get_indicator: function(doc) {
        if ((doc.docstatus === 0 || doc.docstatus === 1) && doc.status === 'Accepted') {
            return [__('Accepted'), 'green', 'status,=,Accepted'];
        } else if ((doc.docstatus === 0 || doc.docstatus === 1) && doc.status === 'Rejected') {
            return [__('Rejected'), 'red', 'status,=,Rejected'];
        } else if ((doc.docstatus === 0 || doc.docstatus === 1) && doc.status === 'Pending') {
            return [__('Pending'), 'orange', 'status,=,Pending'];
        }
    }
};
