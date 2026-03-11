// Component: CompanyProfile — Company profile editing form
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true, saving: false, message: '',
            form: { name: '', industry: '', website: '', description: '', hr_name: '', hr_email: '', hr_phone: '' }
        }
    },
    mounted() {
        fetch('/api/company/info')
            .then(r => r.json())
            .then(data => {
                this.form = { ...data.company };
                this.loading = false;
            });
    },
    methods: {
        saveProfile() {
            this.saving = true;
            this.message = '';
            fetch('/api/company/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.form)
            })
            .then(r => r.json())
            .then(data => {
                this.message = data.message;
                this.saving = false;
            });
        }
    }
}).mount('#app');
