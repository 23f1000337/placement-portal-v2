// Component: AdminCompanies — Lists companies with approve/reject/delete actions for admin
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, companies: [], filter: 'all', page: 1, pages: 1, total: 0 }
    },
    watch: {
        filter() { this.page = 1; this.fetchData(); }
    },
    mounted() { this.fetchData(); },
    methods: {
        fetchData() {
            this.loading = true;
            fetch('/api/admin/companies?status=' + this.filter + '&page=' + this.page)
                .then(r => r.json())
                .then(data => {
                    this.companies = data.items;
                    this.pages = data.pages;
                    this.total = data.total;
                    this.loading = false;
                });
        },
        changePage(p) { this.page = p; this.fetchData(); },
        statusColor(s) {
            return s == 'pending' ? 'warning' : s == 'approved' ? 'success' : 'danger';
        },
        action(id, type) {
            fetch('/api/admin/company/' + id + '/' + type, { method: 'POST' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        },
        deleteCompany(id) {
            if (!confirm('Delete this company?')) return;
            fetch('/api/admin/company/' + id, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        }
    }
}).mount('#app');
