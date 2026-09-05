(() => {
    const { createElement: h, useEffect, useRef, useState } = React;

    function CaptureWidget({ mode }) {
        const videoRef = useRef(null);
        const canvasRef = useRef(null);
        const streamRef = useRef(null);
        const timerRef = useRef(null);
        const framesRef = useRef([]);
        const [running, setRunning] = useState(false);
        const [samples, setSamples] = useState(0);
        const [message, setMessage] = useState('Ready for camera capture.');

        useEffect(() => () => stop(), []);

        function stop() {
            if (timerRef.current) clearInterval(timerRef.current);
            streamRef.current?.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
            setRunning(false);
        }

        async function start() {
            try {
                if (mode === 'registration' && !document.querySelector('#register-id')?.value.trim()) {
                    setMessage('Save the student record before starting capture.');
                    return;
                }
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false,
                });
                streamRef.current = stream;
                videoRef.current.srcObject = stream;
                setRunning(true);
                setMessage(mode === 'registration' ? 'Automatic capture started. Keep looking at the camera.' : 'Camera ready. Scan when you are ready.');
                if (mode === 'registration') beginAutomaticSamples();
            } catch (error) {
                setMessage(`Camera unavailable: ${error.message}`);
            }
        }

        function captureFrame() {
            const video = videoRef.current;
            const canvas = canvasRef.current;
            if (!video || !canvas || !video.videoWidth) return null;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            return canvas.toDataURL('image/jpeg', 0.86);
        }

        function beginAutomaticSamples() {
            let count = 0;
            timerRef.current = setInterval(() => {
                if (count >= 30) {
                    clearInterval(timerRef.current);
                    stop();
                    setMessage('Captured 30 samples. Uploading them now...');
                    saveRegistrationSamples();
                    return;
                }
                const frame = captureFrame();
                if (frame) {
                    framesRef.current.push(frame);
                    count += 1;
                    setSamples(count);
                    setMessage(`Automatically captured ${count} / 30 samples.`);
                }
            }, 350);
        }

        async function saveRegistrationSamples() {
            const studentId = document.querySelector('#register-id')?.value.trim();
            if (!studentId) return setMessage('Save the student record before starting capture.');
            try {
                const response = await fetch(`/api/students/${encodeURIComponent(studentId)}/face-samples`, {
                    method: 'POST', credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ samples: framesRef.current }),
                });
                const result = await response.json();
                setMessage(result.message || 'Face samples saved.');
            } catch (error) {
                setMessage(`Upload failed: ${error.message}`);
            }
        }

        async function scanAttendance() {
            const photo = captureFrame();
            if (!photo) return setMessage('Camera frame is not ready yet.');
            setMessage('Sending photo for face recognition...');
            try {
                const response = await fetch('/api/attendance/auto', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ photo, use_voice: true }),
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.message || 'Attendance scan failed.');
                const student = result.student_name
                    ? `${result.student_name} (${result.student_id})`
                    : result.student_id || 'Student';
                const voice = result.voice?.message ? ` Voice: ${result.voice.message}` : '';
                setMessage(`${student}: ${result.message || 'Attendance scan complete.'}${voice}`);
            } catch (error) {
                setMessage(`Scan failed: ${error.message}`);
            }
        }

        return h('section', { className: 'react-capture-card' },
            h('div', { className: 'video-frame' },
                h('video', { ref: videoRef, autoPlay: true, playsInline: true, muted: true }),
                !running && h('div', null, 'Camera is off')
            ),
            h('canvas', { ref: canvasRef, hidden: true }),
            h('div', { className: 'camera-actions' },
                !running && h('button', { className: 'btn btn-primary', onClick: start }, 'Start camera'),
                running && mode === 'attendance' && h('button', { className: 'btn btn-accent', onClick: scanAttendance }, 'Scan + mark attendance'),
                running && h('button', { className: 'btn btn-ghost', onClick: stop }, 'Stop')
            ),
            h('p', { className: 'form-message', role: 'status' }, mode === 'registration' ? `${message} (${samples}/30)` : message)
        );
    }

    window.mountReactCapture = (element, mode) => {
        if (element && window.ReactDOM) ReactDOM.createRoot(element).render(h(CaptureWidget, { mode }));
    };
})();