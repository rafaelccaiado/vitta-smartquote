import { useState, useEffect } from 'react'

export default function OCRProcessing({ imageFile, selectedUnit, onComplete, onBack }) {
    const [status, setStatus] = useState('processing') // processing, success, error
    const [progress, setProgress] = useState(0)
    const [extractedText, setExtractedText] = useState('')
    const [modelUsed, setModelUsed] = useState('')
    const [confidence, setConfidence] = useState(0)
    const [ocrStats, setOcrStats] = useState(null)
    const [linesData, setLinesData] = useState([])
    const [isEditing, setIsEditing] = useState(false)

    useEffect(() => {
        processOCR()
    }, [])

    const processOCR = async () => {
        try {
            setProgress(10)
            setStatus('processing')

            const formData = new FormData()
            formData.append('file', imageFile)
            formData.append('unit', selectedUnit)

            setProgress(30)

            let API_URL = import.meta.env.VITE_API_URL || ''
            // Se estivermos em produção (não localhost) mas VITE_API_URL for localhost, limpar
            if (window.location.hostname !== 'localhost' && API_URL.includes('localhost')) {
                API_URL = ''
            }

            const response = await fetch(`${API_URL}/api/ocr`, {
                method: 'POST',
                body: formData,
            })

            setProgress(60)

            if (!response.ok) {
                const errorBody = await response.text()
                throw new Error(`HTTP ${response.status}: ${errorBody.slice(0, 100)}`)
            }

            const data = await response.json()

            if (data.error) {
                throw new Error(`SERVER: ${data.error}`)
            }

            setProgress(90)

            setExtractedText(data.text)
            setLinesData(data.lines || [])
            setConfidence(Math.round((data.confidence || 0.85) * 100))
            setOcrStats(data.stats)
            setModelUsed(data.model_used || 'huggingface-ocr')

            setProgress(100)
            setStatus('success')

        } catch (error) {
            console.error('Erro no OCR:', error)
            setExtractedText(`Erro: ${error.message}`) // Guardar erro no texto para debug
            setStatus('error')
        }
    }

    const handleReprocess = () => {
        setProgress(0)
        setExtractedText('')
        processOCR()
    }

    const handleContinue = () => {
        onComplete({
            text: extractedText,
            lines: linesData, // Passando dados estruturados e editados
            confidence,
            modelUsed
        })
    }

    return (
        <div className="card max-w-2xl mx-auto">
            <div className="text-center mb-6">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    🔍 Processando Pedido Médico
                </h2>
                <p className="text-gray-600">
                    Extraindo texto da imagem com OCR inteligente
                </p>
            </div>

            {/* Preview da Imagem */}
            <div className="mb-6">
                <img
                    src={URL.createObjectURL(imageFile)}
                    alt="Pedido médico"
                    className="max-h-64 mx-auto rounded-lg shadow-md"
                />
                <p className="text-center text-sm text-gray-500 mt-2">
                    Unidade: <span className="font-semibold">{selectedUnit}</span>
                </p>
            </div>

            {/* Barra de Progresso */}
            {status === 'processing' && (
                <div className="mb-6">
                    <div className="flex justify-between text-sm text-gray-600 mb-2">
                        <span>Processando...</span>
                        <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                            className="bg-primary h-3 rounded-full transition-all duration-500"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <p className="text-xs text-gray-500 mt-2 text-center">
                        Modelo: {modelUsed || 'Selecionando melhor modelo...'}
                    </p>
                </div>
            )}

            {/* Texto Extraído */}
            {status === 'success' && (
                <div className="space-y-4">
                    {/* Indicador de Score Real (Híbrido) */}
                    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                        <div className="bg-gray-50 border-b border-gray-200 p-4">
                            <h3 className="font-bold text-gray-800 flex items-center gap-2">
                                <span className="text-xl">📊</span> Score de Acurácia Real
                            </h3>
                        </div>
                        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Confiança Técnica */}
                            <div className="space-y-1">
                                <div className="flex justify-between text-xs text-gray-500 font-bold uppercase">
                                    <span>Leitura Automática</span>
                                    <span>{confidence}%</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-2">
                                    <div
                                        className={`h-2 rounded-full transition-all duration-1000 ${confidence >= 80 ? 'bg-green-500' : confidence >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                            }`}
                                        style={{ width: `${confidence}%` }}
                                    />
                                </div>
                            </div>

                            {/* Eficiência por Heurísticas */}
                            <div className="flex items-center gap-3">
                                <div className="bg-blue-100 text-blue-700 w-10 h-10 rounded-lg flex items-center justify-center font-bold">
                                    {ocrStats?.auto_confirmed || 0}
                                </div>
                                <div className="text-xs">
                                    <div className="font-bold text-gray-700">Siglas Mapeadas</div>
                                    <div className="text-gray-500">Regras determinísticas</div>
                                </div>
                            </div>
                        </div>

                        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex flex-wrap gap-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                            <div className="flex items-center gap-1">
                                <span className={ocrStats?.llm_applied ? 'text-purple-600' : 'text-gray-400'}>
                                    {ocrStats?.llm_applied ? '●' : '○'} LLM CORRECTION
                                </span>
                            </div>
                            <div className="flex items-center gap-1">
                                <span className="text-blue-600">● PRE-PROCESSING</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <span className="text-green-600">● FUZZY MATCH READY</span>
                            </div>
                        </div>
                    </div>

                    {/* Alerta de Baixa Confiança (Condicional) */}
                    {confidence < 70 && (
                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-4">
                            <div className="text-2xl">⚠️</div>
                            <div>
                                <h4 className="font-bold text-amber-900 text-sm">Imagem complexa detectada</h4>
                                <p className="text-xs text-amber-800">Sugerimos revisar os termos extraídos antes de prosseguir.</p>
                            </div>
                        </div>
                    )}

                    {/* Texto Extraído */}
                    {/* Tabela de Correções Detalhada */}
                    <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-gray-50 text-gray-700 font-semibold uppercase text-xs border-b">
                                <tr>
                                    <th className="px-4 py-3 w-1/3">OCR Leu</th>
                                    <th className="px-4 py-3 w-1/3">Corrigido Para</th>
                                    <th className="px-4 py-3 text-right">Confiança</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {(linesData || []).map((line, idx) => (
                                    <tr key={idx} className="hover:bg-blue-50 transition-colors group">
                                        <td className="px-4 py-3 text-gray-500 font-mono text-xs truncate max-w-[150px]" title={line.original}>
                                            {line.original}
                                        </td>
                                        <td className="px-4 py-3 font-medium text-gray-900">
                                            {isEditing ? (
                                                <input
                                                    type="text"
                                                    value={line.corrected}
                                                    onChange={(e) => {
                                                        const newLines = [...linesData];
                                                        newLines[idx].corrected = e.target.value;
                                                        setLinesData(newLines);
                                                        setExtractedText(newLines.map(l => l.corrected).join('\n'));
                                                    }}
                                                    className="w-full px-2 py-1 border rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                                />
                                            ) : (
                                                <span className={line.original !== line.corrected ? "text-blue-700 font-bold" : ""}>
                                                    {line.corrected}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                {line.method === 'deterministic_rule' && (
                                                    <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-bold" title="Regra Sigla">
                                                        SIGLA
                                                    </span>
                                                )}
                                                {line.method === 'context_rule' && (
                                                    <span className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-bold" title="Contexto">
                                                        CTX
                                                    </span>
                                                )}
                                                {line.method === 'llm_correction' && (
                                                    <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-bold" title="LLM">
                                                        AI
                                                    </span>
                                                )}
                                                <span
                                                    className={`px-2 py-1 rounded-md font-bold text-xs ${line.confidence >= 0.9 ? 'bg-green-100 text-green-700' :
                                                        line.confidence >= 0.7 ? 'bg-yellow-100 text-yellow-700' :
                                                            'bg-red-100 text-red-700'
                                                        }`}
                                                >
                                                    {Math.round(line.confidence * 100)}%
                                                </span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {(!linesData || linesData.length === 0) && (
                                    <tr>
                                        <td colSpan="3" className="px-4 py-8 text-center text-gray-400 italic">
                                            Nenhum texto detectado.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex justify-end">
                        <button
                            onClick={() => setIsEditing(!isEditing)}
                            className="text-sm text-primary hover:text-blue-700 font-medium flex items-center gap-1"
                        >
                            {isEditing ? '✓ Salvar Edições' : '✏️ Editar Correções'}
                        </button>
                    </div>

                    {/* Botões de Ação */}
                    <div className="flex gap-3 pt-4">
                        <button
                            onClick={onBack}
                            className="btn-secondary flex-1"
                        >
                            ← Voltar
                        </button>
                        <button
                            onClick={handleReprocess}
                            className="btn-secondary flex-1"
                        >
                            🔄 Reprocessar
                        </button>
                        <button
                            onClick={handleContinue}
                            className="btn-primary flex-1"
                        >
                            Continuar →
                        </button>
                    </div>
                </div>
            )}

            {/* Erro */}
            {status === 'error' && (
                <div className="text-center space-y-4">
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                        <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            Erro no Processamento
                        </h3>
                        <p className="text-gray-600 mb-4">
                            Não foi possível processar a imagem. Tente novamente ou envie outra imagem.
                        </p>
                        {extractedText && (
                            <div className="bg-red-50 text-red-700 p-3 rounded-md text-xs font-mono break-all mb-4">
                                {extractedText}
                            </div>
                        )}
                    </div>
                    <div className="flex gap-3">
                        <button onClick={onBack} className="btn-secondary flex-1">
                            ← Voltar
                        </button>
                        <button onClick={handleReprocess} className="btn-primary flex-1">
                            🔄 Tentar Novamente
                        </button>
                    </div>
                </div>
            )}
            {/* Debug Tag */}
            <div className="text-[8px] text-gray-300 text-right mt-4 uppercase text-green-600 font-bold">
                Build: 2026-01-28-V66 (Validation Logic Fix)
            </div>
        </div>
    )
}
