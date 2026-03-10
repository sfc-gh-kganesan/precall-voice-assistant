const MINUTE = 60;
const HOUR = 3600;
const DAY = 86400;
const WEEK = 604800;
const MONTH = 2592000;

export function timeAgo(date: string | Date): string {
    const now = Date.now();
    const then = new Date(date).getTime();
    const seconds = Math.floor((now - then) / 1000);

    if (seconds < 10) return 'just now';
    if (seconds < MINUTE) return `${seconds}s ago`;
    if (seconds < HOUR) return `${Math.floor(seconds / MINUTE)}m ago`;
    if (seconds < DAY) return `${Math.floor(seconds / HOUR)}h ago`;
    if (seconds < WEEK) return `${Math.floor(seconds / DAY)}d ago`;
    if (seconds < MONTH) return `${Math.floor(seconds / WEEK)}w ago`;
    return new Date(date).toLocaleDateString();
}

export function formatDuration(
    startDate: string,
    endDate: string | null,
): string {
    if (!endDate) return 'In progress';
    const ms = new Date(endDate).getTime() - new Date(startDate).getTime();
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    if (seconds < MINUTE) return `${seconds}s`;
    if (seconds < HOUR) {
        const m = Math.floor(seconds / MINUTE);
        const s = seconds % MINUTE;
        return s > 0 ? `${m}m ${s}s` : `${m}m`;
    }
    const h = Math.floor(seconds / HOUR);
    const m = Math.floor((seconds % HOUR) / MINUTE);
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
}
