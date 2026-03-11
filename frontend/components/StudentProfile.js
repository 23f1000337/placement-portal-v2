// Component: StudentProfile — Student profile editing with resume upload
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true, saving: false, message: '',
            form: {}
        }
    },
    mounted() {
        fetch('/api/student/info')
            .then(r => r.json())
            .then(data => { this.form = data.student; this.loading = false; });
    },
    methods: {
        saveProfile() {
            this.saving = true;
            this.message = '';
            const fd = new FormData();
            fd.append('name', this.form.name || '');
            fd.append('branch', this.form.branch || '');
            fd.append('year', this.form.year || '');
            fd.append('cgpa', this.form.cgpa || '');
            fd.append('phone', this.form.phone || '');
            fd.append('skills', this.form.skills || '');
            fd.append('about', this.form.about || '');
            fd.append('experience', this.form.experience || '');
            if (this.$refs.resumeFile.files[0]) {
                fd.append('resume', this.$refs.resumeFile.files[0]);
            }
            fetch('/api/student/profile', { method: 'PUT', body: fd })
                .then(r => r.json())
                .then(data => {
                    this.message = data.message;
                    if (data.resume) this.form.resume = data.resume;
                    this.saving = false;
                });
        }
    }
}).mount('#app');
