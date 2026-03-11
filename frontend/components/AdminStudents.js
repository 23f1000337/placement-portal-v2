// Component: AdminStudents — Lists students with view profile, blacklist, delete
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true, students: [], page: 1, pages: 1, total: 0,
            showModal: false, detail: null, detailApps: []
        }
    },
    mounted() { this.fetchData(); },
    methods: {
        fetchData() {
            this.loading = true;
            fetch('/api/admin/students?page=' + this.page)
                .then(r => r.json())
                .then(data => {
                    this.students = data.items;
                    this.pages = data.pages;
                    this.total = data.total;
                    this.loading = false;
                });
        },
        changePage(p) { this.page = p; this.fetchData(); },
        viewStudent(id) {
            fetch('/api/admin/student/' + id)
                .then(r => r.json())
                .then(data => {
                    this.detail = data.student;
                    this.detailApps = data.applications;
                    this.showModal = true;
                });
        },
        statusColor(s) {
            if (s == 'applied') return 'info';
            if (s == 'shortlisted') return 'warning';
            if (s == 'interview') return 'primary';
            if (s == 'selected' || s == 'placed') return 'success';
            return 'danger';
        },
        toggleBlacklist(id) {
            fetch('/api/admin/student/' + id + '/blacklist', { method: 'POST' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        },
        deleteStudent(id) {
            if (!confirm('Delete this student?')) return;
            fetch('/api/admin/student/' + id, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => { alert(data.message); this.fetchData(); });
        }
    }
}).mount('#app');
