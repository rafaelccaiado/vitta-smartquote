import { useState } from 'react'
import UploadImage from './components/UploadImage'
import OCRProcessing from './components/OCRProcessing'
import ValidationModal from './components/ValidationModal'
import BudgetDisplay from './components/BudgetDisplay'
import Header from './components/Header'

function App() {
  const [step, setStep] = useState(1) // 1: Upload, 2: OCR, 3: Validation, 4: Budget
  const [imageFile, setImageFile] = useState(null)
  const [selectedUnit, setSelectedUnit] = useState('Goiânia Centro')
  const [ocrResult, setOcrResult] = useState(null)
  const [validatedExams, setValidatedExams] = useState([])
  const [budget, setBudget] = useState(null)

  const handleImageUpload = (file, unit) => {
    setImageFile(file)
    setSelectedUnit(unit)
    setStep(2)
  }

  const handleOCRComplete = (result) => {
    setOcrResult(result)
    setStep(3)
  }

  const handleValidationComplete = (exams) => {
    setValidatedExams(exams)
    setStep(4)
  }

  const handleNewQuote = () => {
    setStep(1)
    setImageFile(null)
    setOcrResult(null)
    setValidatedExams([])
    setBudget(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
      <Header />

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {step === 1 && (
          <UploadImage
            onUpload={handleImageUpload}
            selectedUnit={selectedUnit}
            onUnitChange={setSelectedUnit}
          />
        )}

        {step === 2 && (
          <OCRProcessing
            imageFile={imageFile}
            selectedUnit={selectedUnit}
            onComplete={handleOCRComplete}
            onBack={() => setStep(1)}
          />
        )}

        {step === 3 && (
          <ValidationModal
            ocrResult={ocrResult}
            selectedUnit={selectedUnit}
            onComplete={handleValidationComplete}
            onBack={() => setStep(2)}
          />
        )}

        {step === 4 && (
          <BudgetDisplay
            exams={validatedExams}
            selectedUnit={selectedUnit}
            onNewQuote={handleNewQuote}
            onBack={() => setStep(3)}
          />
        )}
      </main>
    </div>
  )
}

export default App
