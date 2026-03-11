// Component: AdminDrives — Full drive management: approve, reject, close, delete
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, drives: [], filter: 'all', page: 1, pages: 1, total: 0 }
    },
    watch: {
        filter() { this.page = 1; this.fetchData(); }
    },
    mounted() { this.fetchData(); },
    methods: {
        fetchData() {
            this.loading = true;
            fetch('/api/admin/drives?status=' + this.filter + '&page=' + this.page)
                .then(r => r.json())
                .then(data => {
                    this.drives = data.items;
                    this.pages = data.pages;
                    this.total = data.total;
                    this.loading = false;
                });
        },
        changePage(p) { this.page = p; this.fetchData(); },
        statusColor(s) {
            if (s == 'pending') return 'warning';
            if (s == 'approved') return 'success';
            if (s == 'rejected') return 'danger';
            if (s == 'closed') return 'secondary';
            return 'secondary';
        },
        action(id, type) {
            fetch('/api/admin/drive/' + id + '/' + type, { method: 'POST' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        },
        deleteDrive(id) {
            if (!confirm('Delete this drive and all its applications?')) return;
            fetch('/api/admin/drive/' + id, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        }
    }
}).mount('#app');
