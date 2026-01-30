import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import QAPackRunner from './components/QAPackRunner'

createRoot(document.getElementById('root')).render(
    <StrictMode>
        <QAPackRunner />
    </StrictMode>,
)
