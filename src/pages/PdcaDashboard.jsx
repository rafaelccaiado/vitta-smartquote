import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Search, Filter } from 'lucide-react';

const PdcaDashboard = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');

    useEffect(() => {
        fetchLogs();
    }, []);

    const fetchLogs = async () => {
        try {
            const response = await fetch('/api/pdca/logs');
            const data = await response.json();
            setLogs(data);
        } catch (error) {
            console.error('Error fetching PDCA logs:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async (log) => {
        const target = prompt(`Confirme o nome EXATO do exame no catálogo para o termo "${log.term}":`, log.acao.split("'")[3] || '');
        if (!target) return;

        try {
            const response = await fetch('/api/pdca/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ term: log.term, unit: log.unit, target: target }),
            });
            if (response.ok) {
                alert('Ação aprovada e sistema atualizado!');
                fetchLogs();
            }
        } catch (error) {
            alert('Erro ao aprovar ação.');
        }
    };

    const filteredLogs = logs.filter(log => {
        if (filter === 'all') return true;
        if (filter === 'synonym') return log.causa.includes('Sinônimo');
        if (filter === 'missing') return log.causa.includes('não encontrado');
        return true;
    });

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
            <div className="max-w-6xl mx-auto">
                <header className="mb-12 flex justify-between items-end">
                    <div>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent mb-2">
                            Controle de PDCA / FCA
                        </h1>
                        <p className="text-slate-400 text-lg">
                            Sistema de Autocura e Curadoria de Exames
                        </p>
                    </div>
                    <div className="flex gap-4 mb-1">
                        <div className="bg-slate-800 p-1 rounded-lg flex border border-slate-700">
                            <button onClick={() => setFilter('all')} className={`px-4 py-2 rounded-md transition ${filter === 'all' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-700'}`}>Todos</button>
                            <button onClick={() => setFilter('synonym')} className={`px-4 py-2 rounded-md transition ${filter === 'synonym' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-700'}`}>Sinônimos</button>
                            <button onClick={() => setFilter('missing')} className={`px-4 py-2 rounded-md transition ${filter === 'missing' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-700'}`}>Não Encontrados</button>
                        </div>
                    </div>
                </header>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 animate-pulse">
                        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                        <p className="text-slate-400">Carregando relatórios de inteligência...</p>
                    </div>
                ) : filteredLogs.length === 0 ? (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-12 text-center">
                        <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4 opacity-50" />
                        <h3 className="text-2xl font-semibold mb-2">Sistema em Equilíbrio</h3>
                        <p className="text-slate-400">Não há pendências de classificação FCA no momento.</p>
                    </div>
                ) : (
                    <div className="grid gap-6">
                        {filteredLogs.map((log, index) => (
                            <div key={index} className="bg-slate-800 border border-slate-700 rounded-2xl p-6 hover:border-blue-500/50 transition group shadow-xl">
                                <div className="flex justify-between items-start mb-6">
                                    <div className="flex items-center gap-3">
                                        <div className="p-3 bg-red-500/10 rounded-xl">
                                            <AlertTriangle className="w-6 h-6 text-red-400" />
                                        </div>
                                        <div>
                                            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1 block">Fato</span>
                                            <h4 className="text-xl font-medium text-white">{log.term}</h4>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <span className="text-xs text-slate-500 block mb-1">Confiança da IA</span>
                                        <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500" style={{ width: `${log.confidence * 100}%` }}></div>
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                    <div className="bg-slate-900/50 p-5 rounded-xl border border-slate-700/50">
                                        <span className="text-xs font-bold uppercase tracking-wider text-blue-400 mb-2 block">Causa</span>
                                        <p className="text-slate-200 leading-relaxed">{log.causa}</p>
                                    </div>
                                    <div className="bg-slate-900/50 p-5 rounded-xl border border-slate-700/50">
                                        <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-2 block">Ação Recomendada</span>
                                        <p className="text-slate-200 leading-relaxed">{log.acao}</p>
                                    </div>
                                </div>

                                <div className="flex justify-between items-center border-t border-slate-700/50 pt-6">
                                    <div className="text-sm text-slate-500">
                                        Unidade: <span className="text-slate-300">{log.unit}</span> • <span className="opacity-50">{new Date(log.timestamp).toLocaleString()}</span>
                                    </div>
                                    <div className="flex gap-3">
                                        <button className="px-5 py-2 rounded-lg border border-slate-600 font-medium hover:bg-slate-700 transition">Ignorar</button>
                                        <button
                                            onClick={() => handleApprove(log)}
                                            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold transition shadow-lg shadow-blue-900/20 active:scale-95"
                                        >
                                            Aprovar Ajuste
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <style>{`
        @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .group { animation: fade-in 0.4s ease-out forwards; }
      `}</style>
        </div>
    );
};

export default PdcaDashboard;
