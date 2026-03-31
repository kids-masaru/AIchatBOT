import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.PROD
    ? 'https://web-production-25bb0.up.railway.app'
    : 'http://localhost:8080';

type UserProfile = {
    name: string;
    personality_traits: string[];
    interests: string[];
    values: string[];
    current_goals: string[];
    summary: string;
};

export const ProfileEditor: React.FC = () => {
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [saveStatus, setSaveStatus] = useState('');

    const fetchProfile = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/api/profile`);
            if (!res.ok) throw new Error('Failed to fetch profile');
            const data = await res.json();
            // data might be empty if no profile exists yet
            if (Object.keys(data).length === 0) {
                // Default empty profile
                setProfile({
                    name: '',
                    personality_traits: [],
                    interests: [],
                    values: [],
                    current_goals: [],
                    summary: 'まだ分析データがありません。MORAと会話すると自動生成されます。'
                });
            } else {
                setProfile(data);
            }
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!profile) return;
        setSaveStatus('Saving...');
        try {
            const res = await fetch(`${API_BASE}/api/profile`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(profile),
            });
            if (!res.ok) throw new Error('Failed to save');
            setSaveStatus('Saved successfully!');
            setTimeout(() => setSaveStatus(''), 3000);
        } catch (err: any) {
            setSaveStatus('Error saving');
        }
    };

    // Helper to update array fields
    const updateArrayField = (field: keyof UserProfile, value: string) => {
        if (!profile) return;
        const array = value.split(',').map(s => s.trim()).filter(s => s);
        setProfile({ ...profile, [field]: array });
    };

    useEffect(() => {
        fetchProfile();
    }, []);

    if (loading) return <div className="text-gray-400">Loading profile...</div>;
    if (!profile && !loading) return <div className="text-gray-400">No profile data found.</div>;

    return (
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700 max-w-4xl mx-auto my-8">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                    🧠 Your Brain Model (Profile)
                </h2>
                <button
                    onClick={fetchProfile}
                    className="text-sm text-gray-400 hover:text-white underline"
                >
                    Reload
                </button>
            </div>

            {error && (
                <div className="bg-red-500/20 border border-red-500 text-red-100 p-4 rounded mb-6">
                    {error}
                </div>
            )}

            <div className="space-y-6">
                {/* Summary Section */}
                <div className="bg-gray-900/50 p-4 rounded border border-gray-700">
                    <label className="block text-sm font-medium text-purple-300 mb-2">AI Summary (Core Memory)</label>
                    <textarea
                        value={profile?.summary || ''}
                        onChange={(e) => setProfile(prev => prev ? { ...prev, summary: e.target.value } : null)}
                        className="w-full bg-gray-800 border border-gray-600 rounded p-3 text-gray-200 focus:ring-2 focus:ring-purple-500 h-32"
                        placeholder="AIによる要約がここに表示されます..."
                    />
                    <p className="text-xs text-gray-500 mt-2">※ 毎日3:00 AMに自動更新されますが、手動で修正して固定することも可能です。</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Personality Traits */}
                    <div>
                        <label className="block text-sm font-medium text-blue-300 mb-2">性格・特徴 (Personality)</label>
                        <input
                            type="text"
                            value={(profile?.personality_traits || []).join(', ')}
                            onChange={(e) => updateArrayField('personality_traits', e.target.value)}
                            className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-gray-200 focus:ring-2 focus:ring-blue-500"
                            placeholder="カンマ区切り (例: 明るい, 論理的)"
                        />
                    </div>

                    {/* Values */}
                    <div>
                        <label className="block text-sm font-medium text-green-300 mb-2">価値観 (Values)</label>
                        <input
                            type="text"
                            value={(profile?.values || []).join(', ')}
                            onChange={(e) => updateArrayField('values', e.target.value)}
                            className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-gray-200 focus:ring-2 focus:ring-green-500"
                            placeholder="カンマ区切り (例: 自由, 誠実)"
                        />
                    </div>

                    {/* Interests */}
                    <div>
                        <label className="block text-sm font-medium text-yellow-300 mb-2">興味・関心 (Interests)</label>
                        <input
                            type="text"
                            value={(profile?.interests || []).join(', ')}
                            onChange={(e) => updateArrayField('interests', e.target.value)}
                            className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-gray-200 focus:ring-2 focus:ring-yellow-500"
                            placeholder="カンマ区切り (例: AI, 日本酒)"
                        />
                    </div>

                    {/* Goals */}
                    <div>
                        <label className="block text-sm font-medium text-red-300 mb-2">現在の目標 (Goals)</label>
                        <input
                            type="text"
                            value={(profile?.current_goals || []).join(', ')}
                            onChange={(e) => updateArrayField('current_goals', e.target.value)}
                            className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-gray-200 focus:ring-2 focus:ring-red-500"
                            placeholder="カンマ区切り"
                        />
                    </div>
                </div>

                <div className="flex justify-end pt-4 border-t border-gray-700">
                    <span className="text-green-400 mr-4 self-center">{saveStatus}</span>
                    <button
                        onClick={handleSave}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-6 rounded transition-colors"
                        disabled={loading}
                    >
                        保存する (Save)
                    </button>
                </div>

            </div>
        </div>
    );
};
