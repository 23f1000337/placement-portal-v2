// Component: CompanyApplications — Lists applications with interview/placed management + student detail
const { createApp } = Vue;
createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true, driveId: null, driveTitle: '', apps: [],
            showModal: false, studentDetail: null
        }
    },
    mounted() {
        this.driveId = document.getElementById('app').dataset.driveId;
        this.fetchData();
    },
    methods: {
        fetchData() {
            fetch('/api/company/drive/' + this.driveId + '/applications')
                .then(r => r.json())
                .then(data => {
                    this.driveTitle = data.drive.title;
                    this.apps = data.applications.map(a => ({
                        ...a, newStatus: a.status
                    }));
                    this.loading = false;
                });
        },
        statusColor(s) {
            if (s == 'applied') return 'info';
            if (s == 'shortlisted') return 'warning';
            if (s == 'interview') return 'primary';
            if (s == 'selected' || s == 'placed') return 'success';
            return 'danger';
        },
        viewStudent(id) {
            fetch('/api/company/student/' + id)
                .then(r => r.json())
                .then(data => {
                    this.studentDetail = data.student;
                    this.showModal = true;
                });
        },
        updateStatus(a) {
            fetch('/api/company/application/' + a.id + '/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: a.newStatus,
                    interview_date: a.interview_date || '',
                    notes: a.notes || ''
                })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                this.fetchData();
            });
        }
    }
}).mount('#app');
