/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: '#0066CC',
                secondary: '#00A86B',
                accent: '#FF6B35',
                success: '#28A745',
                warning: '#FFC107',
                error: '#DC3545',
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
