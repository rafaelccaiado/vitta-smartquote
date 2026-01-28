export default function Header() {
    return (
        <header className="bg-white shadow-sm border-b border-gray-200">
            <div className="container mx-auto px-4 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                            <span className="text-white font-bold text-xl">V</span>
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Vittá SmartQuote</h1>
                            <p className="text-sm text-gray-600">Cotação Inteligente de Exames</p>
                        </div>
                    </div>

                    <div className="hidden md:flex items-center space-x-2 text-sm text-gray-600">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>10 unidades | 500k+ pacientes</span>
                    </div>
                </div>
            </div>
        </header>
    )
}
