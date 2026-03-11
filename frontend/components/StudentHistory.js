// Component: StudentHistory — Shows placement history (selected/rejected/placed results)
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { loading: true, apps: [] }
    },
    mounted() {
        fetch('/api/student/history')
            .then(r => r.json())
            .then(data => { this.apps = data; this.loading = false; });
    }
}).mount('#app');
