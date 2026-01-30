```javascript
import { useState } from 'react';

const GROUPS = [
  { id: 'A', name: 'Grupo A: Impresso Nítido', desc: 'Zero alucinação, 100% termos conhecidos.' },
  { id: 'B', name: 'Grupo B: Manuscrito Bom', desc: 'Maioria identificado. Fallback aceitável.' },
  { id: 'C', name: 'Grupo C: Manuscrito Ruim', desc: 'OCR seguro. Fallback esperado.' }
];

export default function QAPackRunner() {
  const [files, setFiles] = useState({ A: null, B: null, C: null });
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [showDebug, setShowDebug] = useState(false);

  const handleFileChange = (groupId, e) => {
    if (e.target.files && e.target.files[0]) {
      setFiles(prev => ({ ...prev, [groupId]: e.target.files[0] }));
      setResults(prev => ({ ...prev, [groupId]: null }));
    }
  };

  const evaluateDecision = (groupId, data) => {
    const metrics = data?.debug_meta?.qa_metrics;
    if (!metrics) return { status: 'NO-GO', reason: 'Falha: JSON incompleto.' };
    
    const { coverage, verified_ratio, fallback_rate_flag } = metrics;
    // const { matched_count } = data.debug_meta; // Removed from Group A rule

    // Regras Globais
    if (coverage === false) return { status: 'NO-GO', reason: 'Critical: Coverage False (OCR Falhou).' };

    // Grupo A - Impresso
    if (groupId === 'A') {
      if (verified_ratio < 0.9) return { status: 'NO-GO', reason: `Verified < 0.9(${ verified_ratio }).` };
      if (fallback_rate_flag === true) return { status: 'NO-GO', reason: 'Fallback Flag Ativado.' };
      return { status: 'GO', reason: 'Impresso OK (High Verified, No Fallback).' };
    }

    // Grupo B - Manuscrito Bom
    if (groupId === 'B') {
        if (verified_ratio < 0.5) return { status: 'WARNING', reason: `Verified Baixo(${ verified_ratio }).` };
        if (verified_ratio >= 0.6) return { status: 'GO', reason: 'Manuscrito Bom OK.' };
        return { status: 'WARNING', reason: 'Verified Limítrofe (0.5-0.6).' };
    }

    // Grupo C - Ruim
    if (groupId === 'C') {
        // Coverage já validado acima
        return { status: 'GO', reason: 'Coverage OK (Fallback aceito).' };
    }

    return { status: 'UNKNOWN', reason: 'Grupo desconhecido.' };
  };

  const executeQA = async () => {
    setLoading(true);
    const newResults = {};

    for (const group of GROUPS) {
      const file = files[group.id];
      if (!file) {
        newResults[group.id] = { error: 'Sem arquivo.' };
        continue;
      }

      const formData = new FormData();
      formData.append('file', file);
      const startTime = performance.now();

      try {
        const endpoint = import.meta.env.DEV ? '/qa-proxy/api/ocr' : '/api/ocr';
        const res = await fetch(endpoint, {
          method: 'POST',
          body: formData,
          headers: { 'X-OCR-Entrypoint': 'antigravity-qa-runner' }
        });

        const duration = (performance.now() - startTime).toFixed(0);
        
        let data;
        try {
             data = await res.json();
        } catch(e) {
             newResults[group.id] = { error: 'Erro Parse JSON', status: res.status, duration };
             continue;
        }

        const decision = evaluateDecision(group.id, data);
        newResults[group.id] = { status: res.status, data, duration, decision };

      } catch (err) {
        newResults[group.id] = { error: err.message };
      }
    }
    setResults(newResults);
    setLoading(false);
  };

  const getGlobalDecision = () => {
    const vals = Object.values(results).map(r => r?.decision?.status);
    if (vals.includes('NO-GO')) return 'NO-GO';
    if (vals.includes('WARNING')) return 'WARNING';
    if (vals.length === 3 && vals.every(v => v === 'GO')) return 'GO';
    return 'INCOMPLETE';
  };

  const copyCompactMetrics = () => {
    const report = {};
    GROUPS.forEach(g => {
        const d = results[g.id]?.data?.debug_meta;
        if (d) {
            report[g.id] = {
                decision: results[g.id].decision.status,
                qa_metrics: d.qa_metrics,
                counts: { matched: d.matched_count, unverified: d.unverified_count, total: d.total_returned, raw_lines: d.raw_ocr_lines_count },
                route: d.route_hit,
                thresholds: d.thresholds
            };
        }
    });
    navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    alert('JSON Métricas copiadas!');
  };

  const copyFullJSON = () => {
    const full = {};
    GROUPS.forEach(g => { if(results[g.id]?.data) full[g.name] = results[g.id].data; });
    navigator.clipboard.writeText(JSON.stringify(full, null, 2));
    alert('Full JSON copiado!');
  };

  const globalStatus = getGlobalDecision();
  const statusColor = { 'GO':'bg-green-100 text-green-800 border-green-500', 'WARNING':'bg-yellow-100 text-yellow-800 border-yellow-500', 'NO-GO':'bg-red-100 text-red-800 border-red-500', 'INCOMPLETE':'bg-gray-100' }[globalStatus];

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="mb-6 flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
            <div>
                <h1 className="text-2xl font-bold text-slate-800">QA Pack Runner 🤖</h1>
                <p className="text-xs text-slate-500">Pipeline V81.2 High Recall</p>
            </div>
            {Object.keys(results).length > 0 && <div className={`px - 4 py - 2 rounded font - bold text - lg border ${ statusColor } `}>{globalStatus}</div>}
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {GROUPS.map(g => (
                <div key={g.id} className="bg-white rounded-lg shadow-sm border border-slate-200 p-4 flex flex-col">
                    <h3 className="font-bold text-slate-700">{g.name}</h3>
                    <p className="text-[10px] text-slate-400 mb-2 h-4">{g.desc}</p>
                    <input type="file" onChange={(e) => handleFileChange(g.id, e)} className="mb-3 text-xs w-full" />
                    
                    {results[g.id] && (
                        <div className={`p - 2 rounded text - xs border flex - 1 font - mono ${ results[g.id].error ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200' } `}>
                            {results[g.id].error ? (
                                <span className="text-red-600 font-bold">{results[g.id].error}</span>
                            ) : (
                                <>
                                    <div className="flex justify-between font-bold mb-1 pb-1 border-b border-slate-200">
                                        <span className={results[g.id].decision.status==='NO-GO'?'text-red-600':results[g.id].decision.status==='WARNING'?'text-yellow-600':'text-green-600'}>
                                            {results[g.id].decision.status}
                                        </span>
                                        <span className="text-slate-400">{results[g.id].duration}ms</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                                        <span>Cov: {String(results[g.id].data.debug_meta.qa_metrics.coverage)}</span>
                                        <span>Ver: {results[g.id].data.debug_meta.qa_metrics.verified_ratio}</span>
                                        <span>Fbk: {String(results[g.id].data.debug_meta.qa_metrics.fallback_rate_flag)}</span>
                                        <span>Match: {results[g.id].data.debug_meta.matched_count}</span>
                                        <span>Unver: {results[g.id].data.debug_meta.unverified_count}</span>
                                        <span>Total: {results[g.id].data.debug_meta.total_returned}</span>
                                        <span className='col-span-2 text-slate-500'>Lines: {results[g.id].data.debug_meta.raw_ocr_lines_count}</span>
                                        <span className='col-span-2 text-[9px] text-slate-500 truncate' title={results[g.id].data.debug_meta.route_hit}>
                                            Route: {results[g.id].data.debug_meta.route_hit}
                                        </span>
                                    </div>
                                     <div className="mt-1 pt-1 border-t border-slate-200 text-[10px] italic text-slate-500">
                                        {results[g.id].decision.reason}
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            ))}
        </div>

        <button onClick={executeQA} disabled={loading} className={`w - full py - 3 mb - 6 rounded - lg font - bold text - white shadow transition - all ${ loading ? 'bg-slate-400' : 'bg-indigo-600 hover:bg-indigo-700' } `}>
            {loading ? 'EXECUTANDO...' : 'RODAR QA PACK AGORA'}
        </button>

        {Object.keys(results).length > 0 && (
            <div className="bg-white rounded-lg shadow p-4 border border-slate-200 flex justify-between items-center">
                <span className="font-bold text-slate-700 text-sm">Exportar Resultados</span>
                <div className="flex gap-2">
                    <button onClick={copyCompactMetrics} className="px-3 py-1.5 text-xs font-bold text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100 border border-indigo-200">
                        Copy Metrics (Compact JSON)
                    </button>
                    <button onClick={copyFullJSON} className="px-3 py-1.5 text-xs font-bold text-slate-700 bg-slate-50 rounded hover:bg-slate-100 border border-slate-200">
                        Copy Full JSON
                    </button>
                    <button onClick={() => setShowDebug(!showDebug)} className="px-3 py-1.5 text-xs text-slate-500 underline">
                        {showDebug ? 'Ocultar JSON' : 'Ver JSON'}
                    </button>
                </div>
            </div>
        )}
        
        {showDebug && Object.keys(results).length > 0 && (
             <pre className="mt-4 p-4 bg-slate-900 text-green-400 text-xs rounded overflow-auto max-h-96">
                {JSON.stringify(results, null, 2)}
             </pre>
        )}
      </div>
    </div>
  );
}
```
