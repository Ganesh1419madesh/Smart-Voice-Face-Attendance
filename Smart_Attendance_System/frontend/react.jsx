import { useEffect, useState } from 'react';

export function LoginAnimation({ children }) {
    return (
        <main className="react-login-animation">
            <div className="react-login-grid" aria-hidden="true" />
            <section className="react-login-content">{children}</section>
        </main>
    );
}

export function DashboardAnimation({ stats = [], children }) {
    return (
        <section className="react-dashboard-animation">
            <header className="react-dashboard-header">{children}</header>
            <div className="react-dashboard-stats">
                {stats.map((stat, index) => (
                    <article
                        className="react-dashboard-stat"
                        style={{ animationDelay: `${index * 90}ms` }}
                        key={stat.label}
                    >
                        <strong>{stat.value}</strong>
                        <span>{stat.label}</span>
                    </article>
                ))}
            </div>
        </section>
    );
}

export default function AnimatedCaptureStatus({ active, label = 'Preparing camera' }) {
    const [dots, setDots] = useState('');

    useEffect(() => {
        if (!active) {
            setDots('');
            return undefined;
        }

        const timer = window.setInterval(() => {
            setDots((current) => (current.length === 3 ? '' : `${current}.`));
        }, 450);

        return () => window.clearInterval(timer);
    }, [active]);

    if (!active) return null;

    return (
        <div className="capture-status-animation" role="status" aria-live="polite">
            <span className="capture-scan-icon" aria-hidden="true">
                <span className="capture-scan-line" />
            </span>
            <span>{label}{dots}</span>
        </div>
    );
}
