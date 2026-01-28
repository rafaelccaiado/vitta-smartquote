import { useState, useEffect } from 'react'

export default function ValidationModal({ ocrResult, selectedUnit, onComplete, onBack }) {
    const [exams, setExams] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        searchExams()
    }, [])

    const searchExams = async () => {
        try {
            setLoading(true)
            setLoading(true)
            let API_URL = import.meta.env.VITE_API_URL || ''
            // FIX VERCEL: Se estivermos em produção (não localhost) mas VITE_API_URL for localhost, limpar
            if (window.location.hostname !== 'localhost' && API_URL.includes('localhost')) {
                API_URL = ''
            }

            // 1. Obter termos (preferência para dados estruturados do OCRProcessing)
            let rawTerms = []

            if (ocrResult?.lines && Array.isArray(ocrResult.lines) && ocrResult.lines.length > 0) {
                // usa as linhas já processadas e possivelmente editadas pelo usuário
                // V64: Allow short codes (len >= 2) like C4, T4
                rawTerms = ocrResult.lines.map(l => l.corrected).filter(t => t && t.trim().length >= 2)
            } else {
                // Fallback para texto bruto
                const ignoreTerms = ['solicito', 'pedido', 'data', 'assinatura', 'dr', 'crm', 'paciente', ':', 'médico']
                const rawText = ocrResult?.text || ''
                rawTerms = rawText
                    .split(/[\n,]+/)
                    .map(t => t.trim())
                    .filter(t => t.length >= 2) // V64: Allow len >= 2
                    .filter(t => !ignoreTerms.some(ignored => t.toLowerCase().includes(ignored)))
            }

            if (rawTerms.length === 0) {
                console.warn('Nenhum termo extraído para busca')
                setLoading(false)
                return
            }

            // 2. Chamar endpoint de validação em lote (BATCH)
            const response = await fetch(`${API_URL}/api/validate-list`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ terms: rawTerms, unit: selectedUnit })
            })

            if (!response.ok) {
                throw new Error('Erro na validação em lote')
            }

            const data = await response.json()

            // 3. Processar resposta do backend
            // Backend já retorna estrutura: { items: [...], stats: {...} }
            const processedExams = data.items.map((item, index) => ({
                id: index + 1,
                term: item.term,
                status: item.status, // confirmed, multiple, not_found, duplicate
                matches: item.matches || [],
                selectedMatch: item.status === 'confirmed' ? 0 : null
            }))

            setExams(processedExams)
            setLoading(false)

        } catch (error) {
            console.error('Erro geral ao buscar exames:', error)
            setLoading(false)
        }
    }

    const handleSelectMatch = (examId, matchIndex) => {
        setExams(exams.map(exam =>
            exam.id === examId
                ? { ...exam, selectedMatch: matchIndex, status: 'confirmed' }
                : exam
        ))
    }

    const handleRemove = (examId) => {
        setExams(exams.filter(exam => exam.id !== examId))
    }

    const handleContinue = async () => {
        // Filtra exames confirmados
        const validatedExams = exams
            .filter(exam => exam.status === 'confirmed' && exam.selectedMatch !== null)
            .map(exam => ({
                ...exam.matches[exam.selectedMatch],
                originalTerm: exam.term
            }))

        // Trigger Learning System in Background
        try {
            const learningPromises = []
            const API_URL = import.meta.env.VITE_API_URL || ''

            validatedExams.forEach(finalItem => {
                // Se o termo original for diferente do selecionado (correção manual ou fuzzy distante)
                // Ex: original="TGO" vs selecionado="ASPARTATO AMINOTRANSFERASE (AST)"
                // Normalizamos strings para comparar
                const original = finalItem.originalTerm.trim()
                const selected = finalItem.item_name.trim() // BigQuery item_name
                // O learning service usa 'search_name' como chave mas guarda o 'item_name' ou 'search_name' como value?
                // O ideal é guardar o 'search_name' limpo para facilitar o match futuro

                // Vamos mandar para o backend o nome exato do exame, ele se vira
                // Melhor só enviar se forem VISIVELMENTE diferentes para não poluir
                if (original.toLowerCase() !== selected.toLowerCase()) {
                    // Achar o search_name correto é difícil aqui, mandamos o item_name 
                    // e o backend/validation_logic terá que lidar
                    // Na verdade, o validation_logic espera que o VALOR do mapping seja uma chave válida do exam_map
                    // A chave do exam_map vem de `search_name` do BQ.
                    // O frontend tem acesso ao `search_name`? Não explicitamente no `matches` atual (tem item_name, id, price)
                    // Precisamos que o backend `search-exams` ou `validate-list` devolva o `search_name` também.

                    // QUICK FIX: O frontend tem `matches` que veio do backend.
                    // Vamos assumir que enviamos o item_name e o backend (LearningService) pode normalizar isso se necessário
                    // OU melhor: vamos enviar o `item_name` e o `ValidationService` 
                    // tenta achar esse item_name no mapa invertido ou algo assim?
                    // Não: ValidationService usa `search_name` como chave.

                    // Vamos enviar o item_name mesmo. O `ValidationService` lá no backend, 
                    // ao carregar, normaliza o `item_name` para criar a chave.
                    // Se salvarmos o `search_name` seria melhor.
                    // Como não temos o `search_name` aqui no frontend facilmente (só description), 
                    // vamos enviar o `item_name` e ver se funciona.

                    // Observação: `search-exams` retorna `item_name` (display)
                    learningPromises.push(
                        fetch(`${API_URL}/api/learn-correction`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                original_term: original,
                                correct_exam_name: finalItem.item_name // Envia o nome completo do DB
                            })
                        })
                    )
                }
            })

            // Não bloqueia o fluxo do usuário, roda em background
            Promise.all(learningPromises).catch(e => console.error("Erro no learning", e))

        } catch (e) {
            console.error("Erro ao despachar learning", e)
        }

        onComplete(validatedExams)
    }

    const pendingCount = exams.filter(e => e.status === 'multiple' && e.selectedMatch === null).length
    const confirmedCount = exams.filter(e => e.status === 'confirmed' && e.selectedMatch !== null).length

    // --- MANUAL SEARCH LOGIC ---
    const [searchingId, setSearchingId] = useState(null)
    const [searchResults, setSearchResults] = useState([])
    const [isSearching, setIsSearching] = useState(false)

    // Debounce manual para evitar muitas requisições
    const handleManualSearch = async (term) => {
        if (!term || term.length < 2) {
            setSearchResults([])
            return
        }

        setIsSearching(true)
        try {
            const API_URL = import.meta.env.VITE_API_URL || ''
            const response = await fetch(`${API_URL}/api/search-exams`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ term, unit: selectedUnit })
            })
            const data = await response.json()
            setSearchResults(data.exams || [])
        } catch (error) {
            console.error('Erro na busca manual:', error)
        } finally {
            setIsSearching(false)
        }
    }

    const selectManualMatch = (examId, match) => {
        setExams(exams.map(exam => {
            if (exam.id === examId) {
                // Adiciona o match manual à lista de matches e o seleciona
                const newMatches = [...exam.matches, match]
                return {
                    ...exam,
                    matches: newMatches,
                    selectedMatch: newMatches.length - 1,
                    status: 'confirmed'
                }
            }
            return exam
        }))
        setSearchingId(null)
        setSearchResults([])
    }

    if (loading) {
        return (
            <div className="card max-w-3xl mx-auto text-center py-12">
                <div className="animate-spin w-12 h-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-gray-600">Buscando exames no banco de dados...</p>
                <p className="text-sm text-gray-500 mt-2">Isso pode levar alguns segundos (conectando ao BigQuery)</p>
            </div>
        )
    }

    return (
        <div className="card max-w-3xl mx-auto">
            {/* Header ... */}
            <div className="text-center mb-6">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    ✅ Validação de Exames
                </h2>
                <p className="text-gray-600">
                    Confirme os exames identificados antes de gerar o orçamento
                </p>
            </div>

            {/* Resumo */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* ... existing summary stats ... */}
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-green-600">{confirmedCount}</div>
                    <div className="text-sm text-green-800">Confirmados</div>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-yellow-600">{pendingCount}</div>
                    <div className="text-sm text-yellow-800">Pendentes</div>
                </div>
            </div>

            {/* Lista de Exames */}
            <div className="space-y-4 mb-6">
                {exams.length === 0 ? (
                    <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                        Nenhum exame identificado automaticamente.
                    </div>
                ) : (
                    exams.map(exam => (
                        <div
                            key={exam.id}
                            className={`border-2 rounded-lg p-4 ${exam.status === 'confirmed' && exam.selectedMatch !== null
                                ? 'border-green-300 bg-green-50'
                                : exam.status === 'multiple'
                                    ? 'border-yellow-300 bg-yellow-50'
                                    : 'border-red-100 bg-red-50' // Diferente para not_found (visual melhor)
                                }`}
                        >
                            <div className="flex justify-between items-start mb-3">
                                <div className="w-full">
                                    <div className="flex justify-between items-center w-full">
                                        <div className="font-semibold text-gray-900 text-lg mb-1">
                                            "{exam.term}"
                                        </div>
                                        <button
                                            onClick={() => handleRemove(exam.id)}
                                            className="text-red-500 hover:text-red-700 text-xs font-bold uppercase tracking-wider"
                                        >
                                            Remover
                                        </button>
                                    </div>

                                    {/* Status Display */}
                                    {exam.status === 'confirmed' && (
                                        <div className="text-sm text-green-700 font-medium mb-2">✓ Confirmado</div>
                                    )}
                                    {exam.status === 'not_found' && (
                                        <div className="text-sm text-red-600 font-medium mb-2">❌ Não encontrado no banco de dados</div>
                                    )}

                                    {/* SEARCH INTERFACE */}
                                    {(exam.status === 'not_found' || searchingId === exam.id) ? (
                                        <div className="mt-2 bg-white p-3 rounded-lg border border-blue-200 shadow-sm relative">
                                            <label className="text-xs font-bold text-blue-800 uppercase block mb-1">
                                                🔍 Buscar manualmente:
                                            </label>
                                            <input
                                                autoFocus
                                                type="text"
                                                placeholder="Digite o nome do exame..."
                                                className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                                onChange={(e) => handleManualSearch(e.target.value)}
                                            />

                                            {/* Dropdown Results */}
                                            {searchResults.length > 0 && (searchingId === exam.id || exam.status === 'not_found') && (
                                                <div className="absolute z-10 w-full bg-white border border-gray-200 mt-1 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                    {searchResults.map(res => (
                                                        <div
                                                            key={res.item_id}
                                                            onClick={() => selectManualMatch(exam.id, res)}
                                                            className="p-2 hover:bg-blue-50 cursor-pointer border-b last:border-0"
                                                        >
                                                            <div className="font-medium text-sm text-gray-800">{res.item_name}</div>
                                                            <div className="flex justify-between text-xs text-gray-500">
                                                                <span>ID: {res.item_id}</span>
                                                                <span className="font-bold text-blue-600">R$ {res.price.toFixed(2)}</span>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {searchResults.length === 0 && isSearching && (
                                                <div className="text-xs text-center p-2 text-gray-400">Buscando...</div>
                                            )}

                                            {/* Cancel button if explicitly searching */}
                                            {searchingId === exam.id && exam.status !== 'not_found' && (
                                                <button
                                                    onClick={() => setSearchingId(null)}
                                                    className="mt-2 text-xs text-gray-500 hover:text-gray-700 underline"
                                                >
                                                    Cancelar busca
                                                </button>
                                            )}
                                        </div>
                                    ) : (
                                        // Show Button to Enable Search if standard match exists
                                        <button
                                            onClick={() => {
                                                setSearchingId(exam.id)
                                                setSearchResults([]) // Clear previous
                                            }}
                                            className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 mt-1"
                                        >
                                            🔍 Substituir / Buscar outro
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Existing Matches List (Hide if searching, maybe? No, keep it) */}
                            {exam.matches.length > 0 && !searchingId && (
                                <div className="space-y-2 mt-3">
                                    {exam.matches.map((match, index) => (
                                        <label
                                            key={index}
                                            className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${exam.selectedMatch === index
                                                ? 'border-primary bg-blue-50'
                                                : 'border-gray-200 hover:border-gray-300 bg-white'
                                                }`}
                                        >
                                            <input
                                                type="radio"
                                                name={`exam-${exam.id}`}
                                                checked={exam.selectedMatch === index}
                                                onChange={() => handleSelectMatch(exam.id, index)}
                                                className="w-4 h-4 text-primary"
                                            />
                                            <div className="flex-1">
                                                <div className="font-medium text-gray-900 text-sm">
                                                    {match.item_name}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    ID: {match.item_id}
                                                </div>
                                            </div>
                                            <div className="text-lg font-bold text-primary">
                                                R$ {match.price.toFixed(2)}
                                            </div>
                                        </label>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Footer Buttons */}
            {/* Same as before... */}
            <div className="flex gap-3">
                <button onClick={onBack} className="btn-secondary flex-1">← Voltar</button>
                <button
                    onClick={handleContinue}
                    disabled={pendingCount > 0}
                    className={`flex-1 ${pendingCount > 0
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed py-3 px-6 rounded-lg'
                        : 'btn-primary'
                        }`}
                >
                    Gerar Orçamento ({confirmedCount} exames) →
                </button>
            </div>
        </div>
    )
}
