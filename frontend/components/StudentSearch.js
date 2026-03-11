// Component: StudentSearch — Search drives and companies
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return { query: '', searchType: 'drive', results: {}, searched: false }
    },
    methods: {
        search() {
            if (!this.query.trim()) return;
            this.searched = true;
            fetch('/api/student/search?q=' + encodeURIComponent(this.query) + '&type=' + this.searchType)
                .then(r => r.json())
                .then(data => { this.results = data; });
        }
    }
}).mount('#app');
