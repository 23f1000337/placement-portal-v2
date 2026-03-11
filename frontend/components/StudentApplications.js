// Component: StudentApplications — Lists student's applications with CSV export and status polling
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true, apps: [],
            exporting: false, exportMsg: '', exportFile: '', taskId: ''
        }
    },
    mounted() {
        fetch('/api/student/applications')
            .then(r => r.json())
            .then(data => { this.apps = data; this.loading = false; });
    },
    methods: {
        statusColor(s) {
            if (s == 'applied') return 'info';
            if (s == 'shortlisted') return 'warning';
            if (s == 'interview') return 'primary';
            if (s == 'selected' || s == 'placed') return 'success';
            return 'danger';
        },
        exportCSV() {
            this.exporting = true;
            this.exportMsg = '';
            this.exportFile = '';
            fetch('/api/student/export-csv', { method: 'POST' })
                .then(r => { if (!r.ok) throw new Error('Server error'); return r.json(); })
                .then(data => {
                    if (data.filename) {
                        // sync fallback — file ready immediately
                        this.exportFile = data.filename;
                        this.exportMsg = 'Export ready!';
                        this.exporting = false;
                    } else {
                        this.taskId = data.task_id;
                        this.exportMsg = 'Export started, checking status...';
                        this.pollExport();
                    }
                })
                .catch(() => {
                    this.exportMsg = 'Export failed.';
                    this.exporting = false;
                });
        },
        pollExport() {
            fetch('/api/student/export-status/' + this.taskId)
                .then(r => r.json())
                .then(data => {
                    if (data.ready) {
                        this.exportFile = data.filename;
                        this.exportMsg = data.filename ? 'Export ready!' : (data.error || 'Export failed');
                        this.exporting = false;
                    } else {
                        setTimeout(() => this.pollExport(), 2000);
                    }
                })
                .catch(() => {
                    this.exportMsg = 'Could not check export status.';
                    this.exporting = false;
                });
        }
    }
}).mount('#app');
