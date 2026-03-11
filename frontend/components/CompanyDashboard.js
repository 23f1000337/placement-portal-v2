// Component: CompanyDashboard — Company dashboard with stats and CSV export
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, info: { company: {} }, drives: [], exporting: false, exportFile: '' }
    },
    mounted() { this.fetchData(); },
    methods: {
        fetchData() {
            this.loading = true;
            Promise.all([
                fetch('/api/company/info').then(r => r.json()),
                fetch('/api/company/drives').then(r => r.json())
            ]).then(([info, drives]) => {
                this.info = info;
                this.drives = drives;
                this.loading = false;
            });
        },
        statusColor(s) {
            if (s == 'pending') return 'warning';
            if (s == 'approved') return 'success';
            if (s == 'rejected') return 'danger';
            return 'secondary';
        },
        closeDrive(id) {
            if (!confirm('Close this drive?')) return;
            fetch('/api/company/drive/' + id + '/close', { method: 'POST' })
                .then(r => r.json())
                .then(() => this.fetchData());
        },
        deleteDrive(id) {
            if (!confirm('Delete this drive and all its applications?')) return;
            fetch('/api/company/drive/' + id, { method: 'DELETE' })
                .then(r => r.json())
                .then(() => this.fetchData());
        },
        exportCSV() {
            this.exporting = true;
            this.exportFile = '';
            fetch('/api/company/export-csv', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) this.exportFile = data.filename;
                    else alert(data.message || 'Export failed');
                    this.exporting = false;
                })
                .catch(() => { this.exporting = false; });
        }
    }
}).mount('#app');
