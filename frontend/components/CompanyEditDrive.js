// Component: CompanyEditDrive — Form to edit an existing placement drive
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true, saving: false, message: '', driveId: null,
            form: {}
        }
    },
    mounted() {
        this.driveId = document.getElementById('app').dataset.driveId;
        fetch('/api/company/drive/' + this.driveId)
            .then(r => r.json())
            .then(data => { this.form = data; this.loading = false; });
    },
    methods: {
        saveDrive() {
            this.saving = true;
            this.message = '';
            fetch('/api/company/drive/' + this.driveId, {
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
