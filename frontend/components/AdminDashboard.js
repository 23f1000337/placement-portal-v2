// Component: AdminDashboard — Shows admin dashboard stats (total companies, students, drives, applications)
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, stats: {} }
    },
    mounted() {
        fetch('/api/admin/stats')
            .then(r => r.json())
            .then(data => { this.stats = data; this.loading = false; });
    }
}).mount('#app');
