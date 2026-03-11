// Component: AdminApplications — Full application management: filter, update status, delete
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, apps: [], filter: 'all', page: 1, pages: 1, total: 0 }
    },
    watch: {
        filter() { this.page = 1; this.fetchData(); }
    },
    mounted() { this.fetchData(); },
    methods: {
        fetchData() {
            this.loading = true;
            fetch('/api/admin/applications?status=' + this.filter + '&page=' + this.page)
                .then(r => r.json())
                .then(data => {
                    this.apps = data.items;
                    this.pages = data.pages;
                    this.total = data.total;
                    this.loading = false;
                });
        },
        changePage(p) { this.page = p; this.fetchData(); },
        statusColor(s) {
            if (s == 'applied') return 'info';
            if (s == 'shortlisted') return 'warning';
            if (s == 'interview') return 'primary';
            if (s == 'selected' || s == 'placed') return 'success';
            return 'danger';
        },
        updateStatus(id, newStatus) {
            fetch('/api/admin/application/' + id + '/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        },
        deleteApp(id) {
            if (!confirm('Delete this application?')) return;
            fetch('/api/admin/application/' + id, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        }
    }
}).mount('#app');
