// Component: CompanyCreateDrive — Form to create a new placement drive
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            saving: false,
            form: {
                title: '', description: '', location: '', salary: '',
                skills_required: '', eligibility: '', eligible_branches: '',
                min_cgpa: '', eligible_year: '', deadline: ''
            }
        }
    },
    methods: {
        createDrive() {
            this.saving = true;
            fetch('/api/company/drives', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.form)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    window.location.href = '/company/dashboard';
                } else {
                    alert(data.message);
                    this.saving = false;
                }
            });
        }
    }
}).mount('#app');
