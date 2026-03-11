// Component: StudentDashboard — Student dashboard with placement stats overview
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, info: { student: {} } }
    },
    mounted() {
        fetch('/api/student/info')
            .then(r => r.json())
            .then(data => { this.info = data; this.loading = false; });
    }
}).mount('#app');
