import { useState, useRef, useEffect } from 'react'

export default function UploadImage({ onUpload, selectedUnit, onUnitChange }) {
    const [preview, setPreview] = useState(null)
    const [dragActive, setDragActive] = useState(false)
    const [units, setUnits] = useState([
        'Goiânia Centro',
        'Anápolis',
        'Ap. Goiânia Buriti Shopping',
        'Goiânia Garavelo',
        'Goiânia Portal Shopping',
        'Goiânia Sudoeste T. Bandeiras',
        'Odontologia',
        'Oftalmologia Vitta Olho',
        'Particular',
        'Trindade'
    ])
    const fileInputRef = useRef(null)

    useEffect(() => {
        const fetchUnits = async () => {
            try {
                const API_URL = import.meta.env.VITE_API_URL || ''
                const response = await fetch(`${API_URL}/api/units`)
                if (response.ok) {
                    const data = await response.json()
                    if (data.units && data.units.length > 0) {
                        setUnits(data.units)
                    }
                }
            } catch (error) {
                console.error("Erro ao carregar unidades:", error)
            }
        }
        fetchUnits()
    }, [])

    const handleDrag = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true)
        } else if (e.type === "dragleave") {
            setDragActive(false)
        }
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0])
        }
    }

    const handleChange = (e) => {
        e.preventDefault()
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0])
        }
    }

    const handleFile = (file) => {
        // Validar tipo de arquivo
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
        if (!validTypes.includes(file.type)) {
            alert('Por favor, envie apenas imagens (JPG, PNG) ou PDF')
            return
        }

        // Validar tamanho (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('Arquivo muito grande. Tamanho máximo: 10MB')
            return
        }

        // Criar preview
        const reader = new FileReader()
        reader.onloadend = () => {
            setPreview(reader.result)
        }
        reader.readAsDataURL(file)
    }

    const handleSubmit = () => {
        if (!preview) {
            alert('Por favor, selecione uma imagem primeiro')
            return
        }

        // Converter preview para File object
        fetch(preview)
            .then(res => res.blob())
            .then(blob => {
                const file = new File([blob], "pedido_medico.jpg", { type: "image/jpeg" })
                onUpload(file, selectedUnit)
            })
    }

    return (
        <div className="card max-w-2xl mx-auto">
            <div className="text-center mb-6">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    📸 Upload do Pedido Médico
                </h2>
                <p className="text-gray-600">
                    Envie uma foto do pedido médico para gerar o orçamento automaticamente
                </p>
            </div>

            {/* Seletor de Unidade */}
            <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Selecione a Unidade
                </label>
                <select
                    value={selectedUnit}
                    onChange={(e) => onUnitChange(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                >
                    {units.map(unit => (
                        <option key={unit} value={unit}>
                            {unit}
                        </option>
                    ))}
                </select>
            </div>

            {/* Área de Upload */}
            <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${dragActive
                    ? 'border-primary bg-blue-50'
                    : 'border-gray-300 hover:border-primary'
                    }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept="image/*,.pdf"
                    onChange={handleChange}
                />

                {!preview ? (
                    <div className="space-y-6">
                        {/* Overlay de Orientação */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                            {[
                                { icon: '☀️', label: 'Luz Frontal', desc: 'Evite sombras' },
                                { icon: '📄', label: 'Papel Plano', desc: 'Sem dobras' },
                                { icon: '🎯', label: 'Centralizado', desc: 'Foque o texto' },
                                { icon: '📱', label: 'Lente Limpa', desc: 'Foto nítida' }
                            ].map((item, i) => (
                                <div key={i} className="bg-white/50 p-3 rounded-lg border border-gray-100 shadow-sm">
                                    <div className="text-2xl mb-1">{item.icon}</div>
                                    <div className="text-xs font-bold text-gray-800">{item.label}</div>
                                    <div className="text-[10px] text-gray-500">{item.desc}</div>
                                </div>
                            ))}
                        </div>

                        <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                            <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                        </div>

                        <div>
                            <p className="text-lg font-semibold text-gray-700 mb-1">
                                Arraste a imagem aqui
                            </p>
                            <p className="text-sm text-gray-500 mb-4">
                                ou clique para selecionar
                            </p>
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className="btn-primary"
                            >
                                Selecionar Arquivo
                            </button>
                        </div>

                        <p className="text-xs text-gray-400">
                            Formatos aceitos: JPG, PNG, PDF (máx. 10MB)
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <img
                            src={preview}
                            alt="Preview"
                            className="max-h-96 mx-auto rounded-lg shadow-md"
                        />

                        <div className="flex gap-3 justify-center">
                            <button
                                onClick={() => {
                                    setPreview(null)
                                    fileInputRef.current.value = ''
                                }}
                                className="btn-secondary"
                            >
                                Trocar Imagem
                            </button>
                            <button
                                onClick={handleSubmit}
                                className="btn-primary"
                            >
                                Processar Pedido →
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Dicas */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    Dicas para melhor resultado
                </h3>
                <ul className="text-sm text-blue-800 space-y-1">
                    <li>✓ Tire a foto com boa iluminação</li>
                    <li>✓ Certifique-se de que o texto está legível</li>
                    <li>✓ Evite sombras e reflexos</li>
                    <li>✓ Enquadre todo o pedido médico</li>
                </ul>

            </div>

            <div className="text-center mt-4">
                <span className="text-[10px] text-gray-400 font-mono">
                    System Version: V70.5 (Base-Build Debug)
                </span>
            </div>
        </div >
    );
}
