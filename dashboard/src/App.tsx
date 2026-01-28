import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Save, Folder, FolderOpen, ChevronRight, Loader2, Bot, Bell, User, Trash2, Database, Plus, ArrowLeft } from 'lucide-react';
import axios from 'axios';
import { ProfileEditor } from './components/ProfileEditor';

// API Base URL
// In development: use local backend
// In production: use the deployed KOTO backend on Railway
const API_BASE = import.meta.env.PROD
  ? 'https://web-production-25bb0.up.railway.app'
  : 'http://localhost:8080';

// --- Types ---
interface Folder {
  id: string;
  name: string;
}

interface KnowledgeSource {
  id: string;
  name: string;
  instruction: string; // Specific instruction for this folder
}

interface Reminder {
  name: string;
  time: string;
  prompt: string;
  enabled: boolean;
}

interface NotionDatabase {
  id: string;
  name: string;
  description: string;
}

interface Config {
  user_name: string;
  user_birthday?: string;

  // Koto
  koto_personality: string;
  koto_master_prompt: string;

  // Agents
  shiori_instruction: string;
  fumi_instruction: string;
  aki_instruction: string;
  rina_instruction: string;
  toki_instruction: string;
  ren_instruction: string;

  knowledge_sources: KnowledgeSource[];
  reminders: Reminder[];
  notion_databases: NotionDatabase[];
}

// ... (LoadingSpinner, FolderBrowser omitted for brevity, they are unchanged)

function App() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showBrowser, setShowBrowser] = useState(false);

  const [config, setConfig] = useState<Config>({
    user_name: '',
    koto_personality: '',
    koto_master_prompt: '',
    shiori_instruction: '',
    fumi_instruction: '',
    aki_instruction: '',
    rina_instruction: '',
    toki_instruction: '',
    ren_instruction: '',
    knowledge_sources: [],
    reminders: [],
    notion_databases: []
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/config`);
      const data = res.data;

      // Backward compatibility mappings
      // Map old 'personality' to 'koto_personality' if new one is missing
      if (!data.koto_personality && data.personality) data.koto_personality = data.personality;
      if (!data.koto_master_prompt && data.master_prompt) data.koto_master_prompt = data.master_prompt;

      // Agent prompt mappings
      if (!data.shiori_instruction && data.profiler_prompt) data.shiori_instruction = data.profiler_prompt;
      if (!data.fumi_instruction && data.maker_prompt) data.fumi_instruction = data.maker_prompt;

      // Expert mappings fallback
      if (!data.toki_instruction && data.expert_history_instruction) data.toki_instruction = data.expert_history_instruction;
      if (!data.ren_instruction && data.expert_comms_instruction) data.ren_instruction = data.expert_comms_instruction;

      // Ensure arrays
      if (!data.knowledge_sources) data.knowledge_sources = [];
      if (!data.reminders) data.reminders = [];
      if (!data.notion_databases) data.notion_databases = [];

      setConfig(data);
    } catch (error) {
      console.error('Failed to fetch config', error);
    } finally {
      setLoading(false);
    }
  };

  // ... (handleSave, addFolder, etc. unchanged)

  // ... (JSX Start)

  {/* 1. Basic Profile Card */ }
  <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <div className="px-6 py-4 bg-gray-50/50 border-b border-gray-100 flex items-center gap-2">
      <User className="w-4 h-4 text-gray-400" />
      <h2 className="text-sm font-bold text-gray-600 uppercase tracking-wider">Basic Profile</h2>
    </div>
    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">My Name</label>
        <input type="text" value={config.user_name} onChange={e => setConfig({ ...config, user_name: e.target.value })} className="w-full px-4 py-2.5 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none" placeholder="User Name" />
      </div>
      <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">KOTO Personality</label>
        <input type="text" value={config.koto_personality} onChange={e => setConfig({ ...config, koto_personality: e.target.value })} className="w-full px-4 py-2.5 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none" placeholder="AI Personality" />
      </div>
      <div className="md:col-span-2">
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">My Birthday (Horoscope)</label>
        <input type="date" value={config.user_birthday || ''} onChange={e => setConfig({ ...config, user_birthday: e.target.value })} className="w-full md:w-1/3 px-4 py-2.5 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none" />
      </div>
    </div>
  </section>

  {/* Master Prompt Card */ }
  <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <div className="px-6 py-4 bg-gray-50/50 border-b border-gray-100 flex items-center gap-2">
      <Bot className="w-4 h-4 text-gray-400" />
      <h2 className="text-sm font-bold text-gray-600 uppercase tracking-wider">Agent Team Instructions</h2>
    </div>
    <div className="p-6 space-y-8">

      {/* KOTO */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-pink-500 rounded-full"></div>
          <label className="text-xs font-bold text-gray-700 uppercase">KOTO (Main Secretary)</label>
        </div>
        <textarea
          value={config.koto_master_prompt}
          onChange={e => setConfig({ ...config, koto_master_prompt: e.target.value })}
          className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
          rows={4}
          placeholder="KOTOへの特別指示（例：山崎フォルダはここ見て、など）"
        />
      </div>

      {/* SHIORI */}
      <div className="border-t border-gray-100 pt-6">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
          <label className="text-xs font-bold text-gray-700 uppercase">SHIORI (Profiler)</label>
        </div>
        <textarea
          value={config.shiori_instruction || ''}
          onChange={e => setConfig({ ...config, shiori_instruction: e.target.value })}
          className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
          rows={4}
          placeholder="栞さんへの指示（プロファイリングの方針）"
        />
      </div>

      {/* FUMI */}
      <div className="border-t border-gray-100 pt-6">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
          <label className="text-xs font-bold text-gray-700 uppercase">FUMI (Creator)</label>
        </div>
        <textarea
          value={config.fumi_instruction || ''}
          onChange={e => setConfig({ ...config, fumi_instruction: e.target.value })}
          className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
          rows={4}
          placeholder="フミさんへの指示（資料作成のトーンなど）"
        />
      </div>

      {/* AKI */}
      <div className="border-t border-gray-100 pt-6">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <label className="text-xs font-bold text-gray-700 uppercase">AKI (Librarian)</label>
        </div>
        <textarea
          value={config.aki_instruction || ''}
          onChange={e => setConfig({ ...config, aki_instruction: e.target.value })}
          className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
          rows={4}
          placeholder="アキさんへの指示（フォルダ整理・検索の方針）"
        />
      </div>

      {/* RINA */}
      <div className="border-t border-gray-100 pt-6">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
          <label className="text-xs font-bold text-gray-700 uppercase">RINA (Scheduler)</label>
        </div>
        <textarea
          value={config.rina_instruction || ''}
          onChange={e => setConfig({ ...config, rina_instruction: e.target.value })}
          className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
          rows={4}
          placeholder="リナさんへの指示（スケジューリングのルール）"
        />
      </div>

      {/* EXPERTS (TOKI & REN) */}
      <div className="border-t border-gray-100 pt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            <label className="text-xs font-bold text-gray-700 uppercase">TOKI (Historian)</label>
          </div>
          <textarea
            value={config.toki_instruction || ''}
            onChange={e => setConfig({ ...config, toki_instruction: e.target.value })}
            className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
            rows={4}
            placeholder="トキさんへの指示（過去ログ分析の視点）"
          />
        </div>
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 bg-teal-500 rounded-full"></div>
            <label className="text-xs font-bold text-gray-700 uppercase">REN (Communicator)</label>
          </div>
          <textarea
            value={config.ren_instruction || ''}
            onChange={e => setConfig({ ...config, ren_instruction: e.target.value })}
            className="w-full px-4 py-3 bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 rounded-lg text-sm font-medium transition-all outline-none resize-none"
            rows={4}
            placeholder="レンさんへの指示（広報・連絡のトーン）"
          />
        </div>
      </div>

    </div>
  </section>

  {/* [NEW] AI Profile Editor (Mental Model) */ }
  <ProfileEditor />

  {/* 2. Reminders Card */ }
  <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <div className="px-6 py-4 bg-gray-50/50 border-b border-gray-100 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Bell className="w-4 h-4 text-gray-400" />
        <h2 className="text-sm font-bold text-gray-600 uppercase tracking-wider">Reminders</h2>
      </div>
      {config.reminders.length < 3 && (
        <button
          onClick={() => setConfig(prev => ({
            ...prev,
            reminders: [...prev.reminders, { name: '新しいリマインダー', time: '12:00', prompt: '', enabled: true }]
          }))}
          className="text-xs font-bold text-white bg-black px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-1 shadow-sm"
        >
          <Plus className="w-3 h-3" /> 追加
        </button>
      )}
    </div>
    <div className="p-6 space-y-4">
      {config.reminders.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed border-gray-100 rounded-xl">
          <Bell className="w-8 h-8 text-gray-200 mx-auto mb-2" />
          <p className="text-sm text-gray-400 font-medium">リマインダーがありません</p>
        </div>
      ) : (
        <div className="space-y-4">
          {config.reminders.map((reminder, index) => (
            <motion.div layout key={index} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={reminder.enabled}
                    onChange={(e) => {
                      const newReminders = [...config.reminders];
                      newReminders[index] = { ...reminder, enabled: e.target.checked };
                      setConfig({ ...config, reminders: newReminders });
                    }}
                    className="w-4 h-4 text-indigo-600 rounded"
                  />
                  <input
                    type="text"
                    value={reminder.name}
                    onChange={(e) => {
                      const newReminders = [...config.reminders];
                      newReminders[index] = { ...reminder, name: e.target.value };
                      setConfig({ ...config, reminders: newReminders });
                    }}
                    className="font-bold text-gray-800 text-sm bg-transparent border-none outline-none"
                    placeholder="リマインダー名"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="time"
                    value={reminder.time}
                    onChange={(e) => {
                      const newReminders = [...config.reminders];
                      newReminders[index] = { ...reminder, time: e.target.value };
                      setConfig({ ...config, reminders: newReminders });
                    }}
                    className="px-2 py-1 bg-gray-50 rounded text-sm"
                  />
                  <button
                    onClick={() => setConfig(prev => ({ ...prev, reminders: prev.reminders.filter((_, i) => i !== index) }))}
                    className="text-gray-300 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <textarea
                value={reminder.prompt}
                onChange={(e) => {
                  const newReminders = [...config.reminders];
                  newReminders[index] = { ...reminder, prompt: e.target.value };
                  setConfig({ ...config, reminders: newReminders });
                }}
                className="w-full px-3 py-2 bg-gray-50 rounded-lg text-sm outline-none resize-none"
                rows={2}
                placeholder="AIへの指示（例: 今日の天気と予定を教えて）"
              />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  </section>

  {/* 2. Knowledge Base Card */ }
  <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden relative">
    <div className="px-6 py-4 bg-gray-50/50 border-b border-gray-100 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Database className="w-4 h-4 text-gray-400" />
        <h2 className="text-sm font-bold text-gray-600 uppercase tracking-wider">Knowledge Sources</h2>
      </div>
      <button onClick={() => setShowBrowser(true)} className="text-xs font-bold text-white bg-black px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-1 shadow-sm">
        <Plus className="w-3 h-3" /> Add Folder
      </button>
    </div>

    <div className="p-6 space-y-4">
      {config.knowledge_sources.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed border-gray-100 rounded-xl">
          <Folder className="w-8 h-8 text-gray-200 mx-auto mb-2" />
          <p className="text-sm text-gray-400 font-medium">No knowledge sources connected.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {config.knowledge_sources.map((source) => (
            <motion.div layout key={source.id} className="group relative bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-yellow-50 rounded-lg flex items-center justify-center">
                    <Folder className="w-4 h-4 text-yellow-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-800 text-sm">{source.name}</h3>
                    <p className="text-[10px] text-gray-400 font-mono">ID: {source.id}</p>
                  </div>
                </div>
                <button onClick={() => removeFolder(source.id)} className="text-gray-300 hover:text-red-500 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Config Prompt Area */}
              <div className="bg-gray-50 rounded-lg p-3">
                <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Instruction Context</label>
                <textarea
                  value={source.instruction}
                  onChange={(e) => updateInstruction(source.id, e.target.value)}
                  className="w-full bg-transparent text-sm text-gray-700 outline-none resize-none placeholder-gray-300"
                  rows={2}
                  placeholder="Example: Use this for sales questions..."
                />
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  </section>

  {/* Notion Databases Card */ }
  <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <div className="px-6 py-4 bg-gray-50/50 border-b border-gray-100 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Database className="w-4 h-4 text-gray-400" />
        <h2 className="text-sm font-bold text-gray-600 uppercase tracking-wider">Notion Databases</h2>
      </div>
      <button
        onClick={() => {
          const id = prompt("NotionデータベースのIDを入力してください（URLの末尾32文字）：");
          if (id) {
            const name = prompt("このデータベースの名前を入力してください（例：仕事タスク）：") || "Notion DB";
            setConfig(prev => ({
              ...prev,
              notion_databases: [...prev.notion_databases, { id, name, description: "" }]
            }));
          }
        }}
        className="text-xs font-bold text-white bg-black px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-1 shadow-sm"
      >
        <Plus className="w-3 h-3" /> Add Database
      </button>
    </div>
    <div className="p-6 space-y-4">
      {config.notion_databases.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed border-gray-100 rounded-xl">
          <Database className="w-8 h-8 text-gray-200 mx-auto mb-2" />
          <p className="text-sm text-gray-400 font-medium">Notionデータベースが登録されていません</p>
          <p className="text-xs text-gray-300 mt-1">「Add Database」から追加してください</p>
        </div>
      ) : (
        <div className="space-y-3">
          {config.notion_databases.map((db, index) => (
            <motion.div layout key={db.id} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-indigo-500" />
                  <div>
                    <h3 className="font-bold text-gray-800 text-sm">{db.name}</h3>
                    <p className="text-[10px] text-gray-400 font-mono">ID: {db.id.slice(0, 8)}...</p>
                  </div>
                </div>
                <button
                  onClick={() => setConfig(prev => ({ ...prev, notion_databases: prev.notion_databases.filter(d => d.id !== db.id) }))}
                  className="text-gray-300 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <input
                value={db.description}
                onChange={(e) => {
                  const updated = [...config.notion_databases];
                  updated[index] = { ...db, description: e.target.value };
                  setConfig({ ...config, notion_databases: updated });
                }}
                className="w-full bg-gray-50 rounded-lg px-3 py-2 text-sm outline-none"
                placeholder="説明（例：仕事のタスク管理用）"
              />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  </section>

  {/* Footer Action */ }
  <div className="flex justify-end pt-4 pb-12">
    <button onClick={handleSave} disabled={saving} className="bg-indigo-600 text-white px-8 py-3 rounded-xl font-bold shadow-lg hover:bg-indigo-700 hover:shadow-xl hover:-translate-y-0.5 transition-all text-sm flex items-center gap-2">
      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
      Save Configuration
    </button>
  </div>

        </div >

    {/* Modal */ }
    <AnimatePresence>
  { showBrowser && <FolderBrowser onSelect={addFolder} onCancel={() => setShowBrowser(false)} /> }
        </AnimatePresence >

      </div >
    </div >
  );
}

export default App;
