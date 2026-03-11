// Component: AdminSearch — Search companies, students, and drives for admin
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { query: '', searchType: 'student', results: {}, searched: false }
    },
    methods: {
        search() {
            if (!this.query.trim()) return;
            this.searched = true;
            fetch('/api/admin/search?q=' + encodeURIComponent(this.query) + '&type=' + this.searchType)
                .then(r => r.json())
                .then(data => { this.results = data; });
        }
    }
}).mount('#app');
