const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
    const response = await fetch(path, { credentials: 'same-origin', ...options });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
        window.location.href = '/';
        throw new Error('Authentication required');
    }
    if (!response.ok) throw new Error(data.message || 'Request failed');
    return data;
}

function showMessage(element, message, kind = '') {
    if (!element) return;
    element.textContent = message;
    element.className = `form-message ${kind}`;
}

const DASHBOARD_MENU = {
    admin: [
        { page: 'overview', label: 'Overview' },
        { page: 'attendance', label: 'Take Attendance' },
        { page: 'register', label: 'Register Student' },
        { page: 'staff', label: 'Register Staff' },
        { page: 'voice', label: 'Voice Attendance' },
        { page: 'students', label: 'Students' },
        { page: 'staff-list', label: 'Staff' },
        { page: 'departments', label: 'Departments' },
        { page: 'training', label: 'Train Models' },
        { page: 'reports', label: 'Reports' },
        { page: 'settings', label: 'Settings' },
    ],
    staff: [
        { page: 'overview', label: 'Overview' },
        { page: 'attendance', label: 'Take Attendance' },
        { page: 'voice', label: 'Voice Attendance' },
        { page: 'students', label: 'My Students' },
        { page: 'today', label: "Today's Attendance" },
        { page: 'history', label: 'Attendance History' },
        { page: 'reports', label: 'Reports' },
        { page: 'profile', label: 'My Profile' },
    ],
    student: [
        { page: 'overview', label: 'Dashboard' },
        { page: 'attendance', label: 'My Attendance' },
        { page: 'history', label: 'Attendance History' },
        { page: 'profile', label: 'My Profile' },
        { page: 'password', label: 'Change Password' },
    ]
};

const PAGE_SECTIONS = {
    overview: 'overview-page',
    attendance: 'attendance-page',
    register: 'register-page',
    voice: 'voice-page',
    reports: 'reports-page',
    students: 'students-page',
    training: 'training-page',
    staff: 'staff-page',
    'staff-list': 'students-page',
    departments: 'departments-page',
    settings: 'settings-page',
    today: 'overview-page',
    history: 'overview-page',
    profile: 'profile-page',
    password: 'password-page',
};

async function initLogin() {
    const form = $('#login-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const error = $('#login-error');
        error.classList.remove('visible');
        const button = $('button[type="submit"]', form);
        button.disabled = true;
        try {
            await api('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: $('#username').value.trim(), password: $('#password').value, role: $('#role').value }) });
            window.location.href = '/dashboard';
        } catch (err) {
            error.textContent = err.message;
            error.classList.add('visible');
        } finally { button.disabled = false; }
    });
}

function renderSidebar(role = 'admin') {
    const nav = $('#sidebar-nav');
    if (!nav) return;
    const items = DASHBOARD_MENU[role] || DASHBOARD_MENU.admin;
    const roleLabel = { admin: 'Full management dashboard', staff: 'Attendance management dashboard', student: 'Personal attendance dashboard' }[role] || 'Operations console';
    document.getElementById('sidebar-role-label')?.replaceChildren(document.createTextNode(roleLabel));
    nav.innerHTML = items.map((item, index) => `
        <button class="nav-item ${index === 0 ? 'active' : ''}" data-page="${item.page}"><span class="nav-icon">${item.label.charAt(0)}</span>${item.label}</button>
    `).join('');
    nav.querySelectorAll('.nav-item').forEach((button) => {
        button.addEventListener('click', async () => {
            nav.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('active', item === button));
            const targetSection = PAGE_SECTIONS[button.dataset.page] || 'overview-page';
            document.querySelectorAll('.page-section').forEach((section) => section.classList.toggle('active', section.id === targetSection));
            if (button.dataset.page === 'students') await loadStudents();
            if (button.dataset.page === 'departments') await loadDepartments();
            if (button.dataset.page === 'overview') await loadOverview();
            if (button.dataset.page === 'reports') setReportDates();
            if (button.dataset.page === 'training') await loadModelStatus();
            if (button.dataset.page === 'profile') await (document.body.dataset.role === 'student' ? loadStudentProfilePage() : loadProfilePage());
        });
    });
    document.querySelectorAll('[data-page-link]').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            nav.querySelector(`[data-page="${link.dataset.pageLink}"]`)?.click();
        });
    });
}

async function loadProfilePage() {
    const card = $('#staff-profile-card');
    const form = $('#staff-profile-form');
    if (!card) return;
    try {
        const response = await api('/api/staff/me');
        const profile = response.profile;
        if (!profile) {
            card.innerHTML = '<p class="muted">No teacher profile found yet. Register your profile below.</p>';
            return;
        }
        card.innerHTML = `
            <div class="profile-avatar">${(profile.name || 'T').charAt(0).toUpperCase()}</div>
            <div class="profile-meta">
                <h3>${profile.name || 'Teacher'}</h3>
                <p>${profile.designation || 'Teacher'} • ${profile.department || 'Department not set'}</p>
            </div>
            <div class="profile-grid">
                <div class="profile-item"><span>Username</span><strong>${profile.username || '-'}</strong></div>
                <div class="profile-item"><span>Teacher ID</span><strong>${profile.staff_id || '-'}</strong></div>
                <div class="profile-item"><span>Email</span><strong>${profile.email || '-'}</strong></div>
                <div class="profile-item"><span>Phone</span><strong>${profile.phone || '-'}</strong></div>
            </div>
        `;
        if (form) {
            $('#staff-id').value = profile.staff_id || '';
            $('#staff-name').value = profile.name || '';
            $('#staff-department').value = profile.department || '';
            $('#staff-email').value = profile.email || '';
            $('#staff-phone').value = profile.phone || '';
        }
    } catch (error) {
        card.innerHTML = `<p class="muted">${error.message}</p>`;
    }
}

async function loadStudentProfilePage() {
    const card = $('#student-profile-card');
    const form = $('#student-profile-form');
    if (!card || !form) return;
    try {
        const response = await api('/api/student/me');
        const profile = response.profile;
        if (!profile) {
            card.innerHTML = '<p class="muted">No student record is linked to this account. Ask an administrator to register your student details first.</p>';
            return;
        }
        card.innerHTML = `
            <div class="profile-avatar">${(profile.name || 'S').charAt(0).toUpperCase()}</div>
            <div class="profile-meta">
                <h3>${profile.name || 'Student'}</h3>
                <p>${profile.course || 'Student'} • ${profile.department || 'Department not set'}</p>
            </div>
            <div class="profile-grid">
                <div class="profile-item"><span>Student ID</span><strong>${profile.student_id || '-'}</strong></div>
                <div class="profile-item"><span>Year</span><strong>${profile.year || '-'}</strong></div>
                <div class="profile-item"><span>Email</span><strong>${profile.email || '-'}</strong></div>
                <div class="profile-item"><span>Phone</span><strong>${profile.phone || '-'}</strong></div>
            </div>
        `;
        $('#student-profile-id').value = profile.student_id || '';
        $('#student-profile-name').value = profile.name || '';
        $('#student-profile-department').value = profile.department || '';
        $('#student-profile-course').value = profile.course || '';
        $('#student-profile-year').value = profile.year || 1;
        $('#student-profile-email').value = profile.email || '';
        $('#student-profile-phone').value = profile.phone || '';
    } catch (error) {
        card.innerHTML = `<p class="muted">${error.message}</p>`;
    }
}

async function saveStudentProfile(event) {
    event.preventDefault();
    const message = $('#student-profile-message');
    const payload = {
        student_id: $('#student-profile-id').value.trim(),
        name: $('#student-profile-name').value.trim(),
        department: $('#student-profile-department').value.trim(),
        course: $('#student-profile-course').value.trim(),
        year: Number($('#student-profile-year').value) || 1,
        email: $('#student-profile-email').value.trim(),
        phone: $('#student-profile-phone').value.trim(),
    };
    try {
        const result = await api('/api/student/me', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        showMessage(message, result.message, 'success');
        await loadStudentProfilePage();
    } catch (error) {
        showMessage(message, error.message, 'error');
    }
}

async function saveStaffProfile(event) {
    event.preventDefault();
    const form = $('#staff-profile-form');
    const message = $('#staff-profile-message');
    const payload = {
        staff_id: $('#staff-id').value.trim(),
        name: $('#staff-name').value.trim(),
        department: $('#staff-department').value.trim(),
        email: $('#staff-email').value.trim(),
        phone: $('#staff-phone').value.trim(),
    };
    try {
        const result = await api('/api/staff/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        showMessage(message, result.message, 'success');
        await loadProfilePage();
    } catch (err) {
        showMessage(message, err.message, 'error');
    }
}

async function changePassword(event) {
    event.preventDefault();
    const message = $('#password-message');
    const newPassword = $('#new-password').value;
    if (newPassword !== $('#confirm-password').value) {
        showMessage(message, 'New passwords do not match.', 'error');
        return;
    }
    try {
        const result = await api('/api/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: $('#current-password').value,
                new_password: newPassword,
            }),
        });
        showMessage(message, result.message, 'success');
        event.target.reset();
    } catch (error) {
        showMessage(message, error.message, 'error');
    }
}

async function registerStaff(event) {
    event.preventDefault();
    const message = $('#staff-register-message');
    const payload = {
        staff_id: $('#staff-register-id').value.trim(),
        name: $('#staff-register-name').value.trim(),
        department: $('#staff-register-department').value.trim(),
        designation: $('#staff-register-designation').value.trim(),
        email: $('#staff-register-email').value.trim(),
        phone: $('#staff-register-phone').value.trim(),
    };
    try {
        const result = await api('/api/staff/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        showMessage(message, result.message, 'success');
        event.target.reset();
        $('#staff-register-designation').value = 'Teacher';
    } catch (error) {
        showMessage(message, error.message, 'error');
    }
}

async function loadUserSession() {
    try {
        const session = await api('/api/session');
        const role = session.role || 'admin';
        document.body.dataset.role = role;
        const roleName = role.charAt(0).toUpperCase() + role.slice(1);
        $('#sidebar-user-label').textContent = `Logged in as: ${session.user} (${roleName})`;
        renderSidebar(role);
        if (role === 'staff') {
            loadProfilePage();
        }
        if (role === 'student') {
            $('#staff-profile-layout').hidden = true;
            $('#student-profile-layout').hidden = false;
            $('#profile-page-title').textContent = 'My student profile';
            $('#profile-page-description').textContent = 'View and update your registered student details.';
            loadStudentProfilePage();
        }
    } catch (error) {
        window.location.href = '/';
    }
}

function photoCell(record) {
    return record.photo_path ? `<a class="photo-link" href="/api/photos/${encodeURIComponent(record.photo_path)}" target="_blank" rel="noreferrer"><img src="/api/photos/${encodeURIComponent(record.photo_path)}" alt="Attendance capture"></a>` : '<span class="muted">Not captured</span>';
}

async function loadOverview() {
    const [stats, records] = await Promise.all([api('/api/dashboard/stats'), api('/api/attendance/today')]);
    $$('[data-stat]').forEach((element) => { element.textContent = stats[element.dataset.stat] ?? 0; });
    const body = $('#attendance-rows');
    body.innerHTML = records.length ? records.map((record) => `<tr><td><strong>${record.student_id}</strong></td><td>${record.name}</td><td>${record.department}</td><td>${record.time_in || '--'}</td><td>${record.time_out || '--'}</td><td><span class="badge ${record.status.toLowerCase()}">${record.status}</span></td><td>${photoCell(record)}</td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No attendance marks yet today.</td></tr>';
}

async function loadStudents(query = '') {
    const students = await api(`/api/students${query ? `?q=${encodeURIComponent(query)}` : ''}`);
    $('#student-rows').innerHTML = students.length ? students.map((student) => `<tr><td><strong>${student.student_id}</strong></td><td>${student.name}</td><td>${student.department}</td><td>${student.course || '--'}</td><td>${student.has_face ? 'Ready' : '--'}</td><td>${student.has_voice ? 'Ready' : '--'}</td><td><button class="btn btn-danger btn-small" data-delete-student="${encodeURIComponent(student.student_id)}" type="button">Delete</button></td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No students match that search.</td></tr>';
    $('#student-options').innerHTML = students.map((student) => `<option value="${student.student_id}">${student.name}</option>`).join('');
}

async function loadDepartments() {
    const students = await api('/api/students');
    const departments = students.reduce((groups, student) => {
        const name = student.department?.trim() || 'Unassigned';
        const group = groups[name] || { total: 0, face: 0, voice: 0 };
        group.total += 1;
        group.face += student.has_face ? 1 : 0;
        group.voice += student.has_voice ? 1 : 0;
        groups[name] = group;
        return groups;
    }, {});
    const rows = Object.entries(departments).sort(([first], [second]) => first.localeCompare(second));
    $('#department-rows').innerHTML = rows.length
        ? rows.map(([name, group]) => `<tr><td><strong>${name}</strong></td><td>${group.total}</td><td>${group.face} / ${group.total}</td><td>${group.voice} / ${group.total}</td></tr>`).join('')
        : '<tr><td colspan="4" class="empty-state">No departments found.</td></tr>';
}

let cameraStream = null;
let markedStudent = null;
let pendingPhoto = null;
let registerStream = null;
let registerStudentId = null;
let faceSamples = [];
let registerCaptureTimer = null;

async function startCamera() {
    const video = $('#camera');
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }, audio: false });
        video.srcObject = cameraStream;
        $('#camera-placeholder').hidden = true;
        $('#start-camera').disabled = true;
        $('#stop-camera').disabled = false;
    } catch (err) { showMessage($('#attendance-message'), `Camera unavailable: ${err.message}`, 'error'); }
}

function stopCamera() {
    cameraStream?.getTracks().forEach((track) => track.stop());
    cameraStream = null;
    $('#camera').srcObject = null;
    $('#camera-placeholder').hidden = false;
    $('#start-camera').disabled = false;
    $('#stop-camera').disabled = true;
}

function capturePhoto() {
    if (!cameraStream) return;
    const video = $('#camera');
    const canvas = $('#photo-canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    pendingPhoto = canvas.toDataURL('image/jpeg', 0.86);
}

async function markAttendance() {
    if (!cameraStream) {
        await startCamera();
        if (!cameraStream) return;
    }
    capturePhoto();
    if (!pendingPhoto) return showMessage($('#attendance-message'), 'The camera frame was not ready. Try again.', 'error');
    const button = $('#mark-attendance');
    button.disabled = true;
    showMessage($('#attendance-message'), 'Saving attendance photo and checking voice...', '');
    try {
        const result = await api('/api/attendance/auto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ photo: pendingPhoto, use_voice: $('#attendance-use-voice').checked }) });
        markedStudent = result.student_id;
        const voiceMessage = result.voice?.message ? ` Voice: ${result.voice.message}` : '';
        showMessage($('#attendance-message'), `${result.student_name || result.student_id}: ${result.message}${voiceMessage}`, result.success ? 'success' : '');
        pendingPhoto = null;
        await loadOverview();
    } catch (err) { showMessage($('#attendance-message'), err.message, 'error'); }
    finally { button.disabled = false; }
}

async function savePhoto(studentId) {
    const result = await api('/api/attendance/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ student_id: studentId, photo: pendingPhoto }) });
    pendingPhoto = null;
    $('#capture-preview').hidden = true;
    showMessage($('#attendance-message'), result.message, 'success');
}

async function registerStudent(event) {
    event.preventDefault();
    const message = $('#register-message');
    const payload = {
        student_id: $('#register-id').value.trim(), name: $('#register-name').value.trim(),
        department: $('#register-department').value.trim(), course: $('#register-course').value.trim(),
        year: Number($('#register-year').value) || 1, email: $('#register-email').value.trim(),
        phone: $('#register-phone').value.trim()
    };
    try {
        const result = await api('/api/students/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        registerStudentId = payload.student_id;
        showMessage(message, result.message + ' Start the camera to capture samples.', 'success');
        await loadStudents();
    } catch (err) { showMessage(message, err.message, 'error'); }
}

async function startRegisterCamera() {
    try {
        registerStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }, audio: false });
        $('#register-camera').srcObject = registerStream;
        $('#register-camera-placeholder').hidden = true;
        $('#register-start-camera').disabled = true;
        faceSamples = [];
        $('#sample-count').textContent = '0 / 30';
        showMessage($('#sample-message'), 'Automatic capture started. Keep your face in the frame.', '');
        registerCaptureTimer = window.setInterval(captureFaceSample, 500);
    } catch (err) { showMessage($('#sample-message'), `Camera unavailable: ${err.message}`, 'error'); }
}

function captureFaceSample() {
    if (!registerStream || faceSamples.length >= 30) return;
    const video = $('#register-camera');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    faceSamples.push(canvas.toDataURL('image/jpeg', 0.88));
    $('#sample-count').textContent = `${faceSamples.length} / 30`;
    showMessage($('#sample-message'), `Automatically captured sample ${faceSamples.length} of 30.`, 'success');
    if (faceSamples.length >= 30) {
        window.clearInterval(registerCaptureTimer);
        registerCaptureTimer = null;
        saveFaceSamples();
    }
}

async function saveFaceSamples() {
    if (!registerStudentId || !faceSamples.length) return;
    try {
        const result = await api(`/api/students/${encodeURIComponent(registerStudentId)}/face-samples`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ samples: faceSamples }) });
        showMessage($('#sample-message'), result.message, 'success');
        faceSamples = [];
        $('#sample-count').textContent = '30 / 30';
        registerStream?.getTracks().forEach((track) => track.stop());
        registerStream = null;
        $('#register-camera').srcObject = null;
        $('#register-camera-placeholder').hidden = false;
        $('#register-start-camera').disabled = false;
    } catch (err) { showMessage($('#sample-message'), err.message, 'error'); }
}

async function runVoiceRecognition() {
    const button = $('#voice-recognize');
    button.disabled = true;
    showMessage($('#voice-recognition-message'), 'Listening on the server microphone...', '');
    try {
        const result = await api('/api/voice/recognize', { method: 'POST' });
        showMessage($('#voice-recognition-message'), result.message || 'Voice recognition complete.', result.recognized && result.attendance?.success ? 'success' : 'error');
        await loadOverview();
    } catch (err) { showMessage($('#voice-recognition-message'), err.message, 'error'); }
    finally { button.disabled = false; }
}

async function registerVoice() {
    const studentId = $('#voice-student').value.trim();
    if (!studentId) return showMessage($('#voice-register-message'), 'Enter a student ID first.', 'error');
    const button = $('#voice-register');
    button.disabled = true;
    showMessage($('#voice-register-message'), 'Recording samples on the server microphone. Please follow the terminal prompts.', '');
    try {
        const result = await api('/api/voice/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ student_id: studentId, count: Number($('#voice-count').value) || 5 }) });
        showMessage($('#voice-register-message'), result.message, result.success ? 'success' : 'error');
    } catch (err) { showMessage($('#voice-register-message'), err.message, 'error'); }
    finally { button.disabled = false; }
}

function setReportDates() {
    const today = new Date().toISOString().slice(0, 10);
    const weekAgo = new Date(Date.now() - 6 * 86400000).toISOString().slice(0, 10);
    $('#report-date').value = today;
    $('#report-start').value = weekAgo;
    $('#report-end').value = today;
}

function downloadReport(type) {
    let query = '';
    if (type === 'daily') query = `?date=${encodeURIComponent($('#report-date').value)}`;
    if (type === 'range') query = `?start=${encodeURIComponent($('#report-start').value)}&end=${encodeURIComponent($('#report-end').value)}&department=${encodeURIComponent($('#report-department').value.trim())}`;
    if (type === 'student') query = `?student_id=${encodeURIComponent($('#report-student').value.trim())}`;
    window.location.href = `/api/reports/${type}${query}`;
}

async function loadModelStatus() {
    const status = await api('/api/models/status');
    $('#face-model-status').textContent = status.face_model_current
        ? 'Model ready and current.'
        : `${status.face_sample_total || 0} captured image(s) found. Retrain to validate the faces.`;
    $('#voice-model-status').textContent = status.voice_model
        ? 'Model ready.'
        : 'Record voice samples for at least 2 students, then train the voice model.';
}

async function trainModel(type) {
    const messageElement = $(`#${type}-training-message`);
    const button = $(`#train-${type}`);
    const startedAt = Date.now();
    const updateElapsed = () => {
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        showMessage(messageElement, `Training ${type} model... ${seconds} seconds elapsed`, '');
    };

    button.disabled = true;
    updateElapsed();
    const timer = setInterval(updateElapsed, 1000);
    try {
        const result = await api(`/api/models/train-${type}`, { method: 'POST' });
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        showMessage(messageElement, `${result.message} Completed in ${seconds} seconds.`, result.success ? 'success' : 'error');
        await loadModelStatus();
    } catch (err) {
        const seconds = Math.floor((Date.now() - startedAt) / 1000);
        showMessage(messageElement, `${err.message} Failed after ${seconds} seconds.`, 'error');
    } finally {
        clearInterval(timer);
        button.disabled = false;
    }
}

function bindDashboard() {
    $('#today-label').textContent = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date());
    loadUserSession();
    $$('.nav-item').forEach((button) => button.addEventListener('click', async () => {
        $$('.nav-item').forEach((item) => item.classList.toggle('active', item === button));
        $$('.page-section').forEach((section) => section.classList.toggle('active', section.id === `${button.dataset.page}-page`));
        if (button.dataset.page === 'students') await loadStudents();
        if (button.dataset.page === 'overview') await loadOverview();
        if (button.dataset.page === 'reports') setReportDates();
        if (button.dataset.page === 'training') await loadModelStatus();
    }));
    $('#refresh').addEventListener('click', loadOverview);
    $('#student-refresh').addEventListener('click', () => loadStudents($('#student-search').value.trim()));
    $('#department-refresh').addEventListener('click', loadDepartments);
    $('#student-search').addEventListener('input', (event) => loadStudents(event.target.value.trim()));
    if (window.mountReactCapture) {
        mountReactCapture($('#react-attendance-root'), 'attendance');
        mountReactCapture($('#react-registration-root'), 'registration');
    }
    $('#register-form').addEventListener('submit', registerStudent);
    $('#staff-profile-form')?.addEventListener('submit', saveStaffProfile);
    $('#staff-register-form')?.addEventListener('submit', registerStaff);
    $('#student-profile-form')?.addEventListener('submit', saveStudentProfile);
    $('#password-form')?.addEventListener('submit', changePassword);
    $('#voice-recognize').addEventListener('click', runVoiceRecognition);
    $('#voice-register').addEventListener('click', registerVoice);
    $('#daily-report').addEventListener('click', () => downloadReport('daily'));
    $('#range-report').addEventListener('click', () => downloadReport('range'));
    $('#student-report').addEventListener('click', () => downloadReport('student'));
    $('#train-face').addEventListener('click', () => trainModel('face'));
    $('#train-voice').addEventListener('click', () => trainModel('voice'));
    $('#logout').addEventListener('click', async () => { await api('/api/logout', { method: 'POST' }); window.location.href = '/'; });
    $('#student-rows').addEventListener('click', async (event) => {
        const button = event.target.closest('[data-delete-student]');
        if (!button || !window.confirm(`Delete student ${decodeURIComponent(button.dataset.deleteStudent)}?`)) return;
        await api(`/api/students/${button.dataset.deleteStudent}`, { method: 'DELETE' });
        await loadStudents($('#student-search').value.trim());
        await loadOverview();
    });
    $('#staff-profile-form')?.addEventListener('submit', saveStaffProfile);
    setReportDates();
    loadStudents().catch(() => {});
    loadOverview().catch((err) => console.error(err));
}

initLogin();
if ($('.dashboard')) bindDashboard();
