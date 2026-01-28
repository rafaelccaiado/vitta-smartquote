import { useState, useEffect } from 'react'

export default function BudgetDisplay({ exams, selectedUnit, onNewQuote, onBack }) {
    const total = exams.reduce((sum, exam) => sum + exam.price, 0)

    // Cálculo dos descontos
    // Safira: 20% desconto em exames laboratoriais
    const safiraTotal = total * (1 - 0.20)
    const safiraEconomia = total - safiraTotal

    // Diamante: 30% desconto em exames laboratoriais
    const diamanteTotal = total * (1 - 0.30)
    const diamanteEconomia = total - diamanteTotal

    // Estado para incluir preços na mensagem (padrão desligado)
    const [includePrices, setIncludePrices] = useState(false)
    const [salesScript, setSalesScript] = useState('')

    useEffect(() => {
        const examsList = exams.map(e => {
            return includePrices
                ? `• ${e.item_name} (R$ ${e.price.toFixed(2).replace('.', ',')})`
                : `• ${e.item_name}`
        }).join('\n')

        const script = `Olá! 😊\n` +
            `Preparei seu orçamento aqui na Clínica Vittá – Unidade ${selectedUnit}.\n\n` +

            `🔬 *Exames Orçados:*\n` +
            `${examsList}\n\n` +

            `💰 *Valor dos exames sem assinatura:*\n` +
            `Total: R$ ${total.toFixed(2).replace('.', ',')}\n\n` +

            `💎 *Com a assinatura Vittá+, você teria desconto imediato nos exames:*\n\n` +

            `• *Vittá+ Safira*\n` +
            `Valor dos exames com desconto: R$ ${safiraTotal.toFixed(2).replace('.', ',')}\n` +
            `Economia agora: R$ ${safiraEconomia.toFixed(2).replace('.', ',')}\n\n` +

            `• *Vittá+ Diamante*\n` +
            `Valor dos exames com desconto: R$ ${diamanteTotal.toFixed(2).replace('.', ',')}\n` +
            `Economia agora: R$ ${diamanteEconomia.toFixed(2).replace('.', ',')}\n\n` +

            `Além da economia nesses exames, a assinatura continua gerando desconto em consultas, exames futuros e outros serviços de saúde.\n\n` +

            `Se quiser, posso te explicar rapidamente qual opção faz mais sentido para você 🙂`

        setSalesScript(script)
    }, [exams, selectedUnit, includePrices]) // Regenera quando checkbox muda

    const generateWhatsAppLink = () => {
        return `https://wa.me/?text=${encodeURIComponent(salesScript)}`
    }

    const copyToClipboard = () => {
        navigator.clipboard.writeText(salesScript)
        alert('Orçamento copiado para a área de transferência!')
    }

    return (
        <div className="card max-w-6xl mx-auto">
            <div className="text-center mb-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    💰 Orçamento Final
                </h2>
                <p className="text-gray-600">
                    Confira os valores e personalize a mensagem de envio
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
                {/* COLUNA 1: EDITOR DE SCRIPT */}
                <div className="flex flex-col h-full bg-white rounded-xl">
                    <div className="flex justify-between items-center mb-3 px-1">
                        <h3 className="font-bold text-gray-700 flex items-center gap-2">
                            📱 Mensagem para o Paciente
                            <span className="text-xs font-normal text-gray-500 bg-gray-100 px-2 py-1 rounded">Editável</span>
                        </h3>

                        {/* Checkbox p/ Incluir Valores */}
                        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer hover:text-green-600 transition-colors select-none">
                            <input
                                type="checkbox"
                                checked={includePrices}
                                onChange={(e) => setIncludePrices(e.target.checked)}
                                className="w-4 h-4 rounded text-green-600 focus:ring-green-500 border-gray-300"
                            />
                            Incluir valores por item
                        </label>
                    </div>

                    <div className="flex-grow flex flex-col">
                        <textarea
                            value={salesScript}
                            onChange={(e) => setSalesScript(e.target.value)}
                            className="w-full flex-grow min-h-[400px] lg:min-h-[500px] p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent font-sans text-sm leading-relaxed resize-none shadow-sm mb-4"
                        />

                        <button
                            onClick={copyToClipboard}
                            className="w-full bg-gray-800 text-white py-4 rounded-xl font-bold hover:bg-gray-900 transition-all flex items-center justify-center gap-2 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                            </svg>
                            Copiar Texto do Script
                        </button>
                    </div>
                </div>

                {/* COLUNA 2: RESUMO E AÇÕES */}
                <div className="space-y-6 flex flex-col h-full">

                    {/* INFO UNIDADE */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900 flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        <span className="font-semibold">Unidade: {selectedUnit}</span>
                    </div>

                    {/* CARD DE VALORES */}
                    <div className="bg-white border-2 border-gray-100 rounded-xl overflow-hidden shadow-sm flex-grow">
                        <div className="bg-gray-50 px-6 py-3 border-b border-gray-100">
                            <h3 className="font-bold text-gray-700 text-sm uppercase tracking-wide">Detalhamento dos Exames</h3>
                        </div>

                        <div className="max-h-[350px] overflow-y-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-white sticky top-0">
                                    <tr className="border-b border-gray-100">
                                        <th className="px-6 py-3 text-left font-medium text-gray-500 bg-gray-50/50">Exame</th>
                                        <th className="px-6 py-3 text-right font-medium text-gray-500 bg-gray-50/50">Valor</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-50">
                                    {exams.map((exam, i) => (
                                        <tr key={i} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-3 text-gray-800 align-middle">{exam.item_name}</td>
                                            <td className="px-6 py-3 text-right font-mono font-medium text-gray-600 align-middle whitespace-nowrap">
                                                R$ {exam.price.toFixed(2)}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* TOTALIZADORES */}
                        <div className="bg-gray-50 p-6 space-y-4 border-t border-gray-100">
                            <div className="flex justify-between items-end">
                                <span className="text-gray-600 font-medium">Total Particular</span>
                                <span className="text-3xl font-bold text-gray-900">R$ {total.toFixed(2)}</span>
                            </div>

                            <div className="border-t border-gray-200 pt-4 space-y-3">
                                <div className="flex justify-between text-sm items-center p-2 rounded hover:bg-white transition-colors">
                                    <span className="text-blue-800 font-medium flex items-center gap-1">
                                        💎 Com Vittá+ Safira
                                    </span>
                                    <div className="text-right">
                                        <span className="block font-bold text-green-600 text-xl">R$ {safiraTotal.toFixed(2)}</span>
                                        <span className="text-[10px] text-green-700 font-bold bg-green-100 px-2 py-0.5 rounded-full inline-block mt-1">Economia: R$ {safiraEconomia.toFixed(2)}</span>
                                    </div>
                                </div>
                                <div className="flex justify-between text-sm items-center p-2 rounded hover:bg-white transition-colors">
                                    <span className="text-blue-800 font-medium flex items-center gap-1">
                                        💎 Com Vittá+ Diamante
                                    </span>
                                    <div className="text-right">
                                        <span className="block font-bold text-green-600 text-xl">R$ {diamanteTotal.toFixed(2)}</span>
                                        <span className="text-[10px] text-green-700 font-bold bg-green-100 px-2 py-0.5 rounded-full inline-block mt-1">Economia: R$ {diamanteEconomia.toFixed(2)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* BOTÕES DE AÇÃO */}
                    <div className="space-y-3 pt-2">
                        <a
                            href={generateWhatsAppLink()}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full btn-primary bg-green-600 hover:bg-green-700 text-white py-4 flex items-center justify-center gap-2 text-lg shadow-green-200 shadow-xl rounded-xl transition-all hover:scale-[1.02] hover:-translate-y-1"
                        >
                            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.890-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z" />
                            </svg>
                            Enviar no WhatsApp
                        </a>

                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={onBack}
                                className="px-4 py-3 border-2 border-gray-200 text-gray-600 rounded-xl font-bold hover:bg-gray-50 hover:border-gray-300 transition-colors"
                            >
                                ← Corrigir
                            </button>
                            <button
                                onClick={onNewQuote}
                                className="px-4 py-3 border-2 border-blue-100 text-blue-600 rounded-xl font-bold hover:bg-blue-50 transition-colors"
                            >
                                + Nova Cotação
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
