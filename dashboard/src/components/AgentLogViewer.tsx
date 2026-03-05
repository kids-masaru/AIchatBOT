import { useState, useEffect } from 'react';
import { Activity, RefreshCw, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.PROD
    ? 'https://web-production-25bb0.up.railway.app'
    : 'http://localhost:8080';

interface LogEntry {
    timestamp: string;
    user_id: string;
    tool_name: string;
    args_summary: Record<string, string>;
    result_summary: string;
    round: number;
}

// Color mapping by tool category
const getToolColor = (name: string): string => {
    if (name.startsWith('consult_')) return 'border-purple-300 bg-purple-50';
    if (name.includes('notion')) return 'border-blue-300 bg-blue-50';
    if (name.includes('google') || name.includes('gmail') || name.includes('calendar') || name.includes('drive') || name.includes('sheet') || name.includes('doc') || name.includes('slide')) return 'border-green-300 bg-green-50';
    if (name.includes('web') || name.includes('fetch')) return 'border-orange-300 bg-orange-50';
    return 'border-gray-200 bg-gray-50';
};

const getToolEmoji = (name: string): string => {
    if (name.startsWith('consult_fumi')) return '📝';
    if (name.startsWith('consult_aki')) return '📚';
    if (name.startsWith('consult_toki')) return '📜';
    if (name.startsWith('consult_ren')) return '📣';
    if (name.startsWith('consult_rina')) return '📅';
    if (name.includes('notion')) return '📋';
    if (name.includes('google') || name.includes('drive')) return '📁';
    if (name.includes('gmail')) return '📧';
    if (name.includes('calendar')) return '📅';
    if (name.includes('web') || name.includes('search')) return '🔍';
    if (name.includes('weather')) return '🌤️';
    if (name.includes('calculate')) return '🧮';
    return '🔧';
};

export const AgentLogViewer = () => {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [autoRefresh, setAutoRefresh] = useState(false);
    const [expanded, setExpanded] = useState(false);

    const fetchLogs = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_BASE}/api/agent-logs?limit=20`);
            setLogs(res.data.logs || []);
        } catch (err) {
            console.error('Failed to fetch agent logs', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (expanded) fetchLogs();
    }, [expanded]);

    useEffect(() => {
        if (!autoRefresh || !expanded) return;
        const interval = setInterval(fetchLogs, 10000);
        return () => clearInterval(interval);
    }, [autoRefresh, expanded]);

    return (
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div
                className="px-6 py-4 bg-gray-50/50 border-b border-gray-100 flex items-center justify-between cursor-pointer hover:bg-gray-100/50 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-gray-400" />
                    <h2 className="text-sm font-bold text-gray-600 uppercase tracking-wider">Agent Activity</h2>
                    {logs.length > 0 && (
                        <span className="bg-indigo-100 text-indigo-600 text-[10px] font-bold px-2 py-0.5 rounded-full">
                            {logs.length}
                        </span>
                    )}
                </div>
                <span className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
            </div>

            {expanded && (
                <div className="p-4">
                    {/* Controls */}
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <button
                                onClick={fetchLogs}
                                disabled={loading}
                                className="text-xs font-bold text-gray-600 bg-gray-100 px-3 py-1.5 rounded-lg hover:bg-gray-200 transition-colors flex items-center gap-1"
                            >
                                {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                                更新
                            </button>
                            <label className="flex items-center gap-1.5 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={autoRefresh}
                                    onChange={(e) => setAutoRefresh(e.target.checked)}
                                    className="w-3.5 h-3.5 text-indigo-600 rounded"
                                />
                                <span className="text-xs text-gray-500 font-medium">10秒自動更新</span>
                            </label>
                        </div>
                        <p className="text-[10px] text-gray-400">
                            💡 LINEで「裏側見せて」と送るとリアルタイムログをLINEに配信
                        </p>
                    </div>

                    {/* Logs */}
                    {logs.length === 0 ? (
                        <div className="text-center py-8 border-2 border-dashed border-gray-100 rounded-xl">
                            <Activity className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                            <p className="text-sm text-gray-400 font-medium">まだアクティビティがありません</p>
                            <p className="text-xs text-gray-300 mt-1">ことちゃんにタスクをお願いすると、ここにログが表示されます</p>
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                            {logs.map((log, i) => (
                                <div
                                    key={i}
                                    className={`border rounded-lg p-3 text-sm ${getToolColor(log.tool_name)} transition-all hover:shadow-sm`}
                                >
                                    <div className="flex items-center justify-between mb-1.5">
                                        <span className="font-bold text-gray-800 text-xs">
                                            {getToolEmoji(log.tool_name)} {log.tool_name}
                                        </span>
                                        <span className="text-[10px] text-gray-400 font-mono">{log.timestamp}</span>
                                    </div>

                                    {Object.keys(log.args_summary).length > 0 && (
                                        <div className="mb-1.5">
                                            <span className="text-[10px] font-bold text-gray-500 uppercase">引数:</span>
                                            <div className="mt-0.5 text-xs text-gray-600 bg-white/60 rounded px-2 py-1 font-mono break-all">
                                                {Object.entries(log.args_summary).map(([k, v]) => (
                                                    <div key={k}><span className="text-gray-400">{k}:</span> {v}</div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    <div>
                                        <span className="text-[10px] font-bold text-gray-500 uppercase">結果:</span>
                                        <div className="mt-0.5 text-xs text-gray-600 bg-white/60 rounded px-2 py-1 font-mono break-all max-h-24 overflow-y-auto">
                                            {log.result_summary}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </section>
    );
};
