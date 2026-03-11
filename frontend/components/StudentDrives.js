// Component: StudentDrives — Browse available drives with search, pagination, and apply
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, drives: [], query: '', page: 1, pages: 1, total: 0 }
    },
    mounted() { this.fetchDrives(); },
    methods: {
        fetchDrives() {
            this.loading = true;
            let url = '/api/student/drives?page=' + this.page;
            if (this.query.trim()) url += '&q=' + encodeURIComponent(this.query);
            fetch(url)
                .then(r => r.json())
                .then(data => {
                    this.drives = data.items;
                    this.pages = data.pages;
                    this.total = data.total;
                    this.loading = false;
                });
        },
        changePage(p) { this.page = p; this.fetchDrives(); },
        apply(driveId) {
            if (!confirm('Apply for this drive?')) return;
            fetch('/api/student/apply/' + driveId, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    this.fetchDrives();
                });
        }
    }
}).mount('#app');
