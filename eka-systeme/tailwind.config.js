/** Charte EKA : bleu marine institutionnel, gris ardoise, accent or sobre. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        marine: { 50: '#F2F6FB', 100: '#E3EBF5', 200: '#C4D5E8', 300: '#95B2D1', 400: '#5C83AE', 500: '#35608F', 600: '#234B74', 700: '#1A3A5C', 800: '#132C46', 900: '#0D2033', 950: '#081520' },
        ardoise: { 50: '#F7F8FA', 100: '#EEF0F4', 200: '#DCE0E8', 300: '#BCC4D1', 400: '#8D98AA', 500: '#6B7687', 600: '#525C6B', 700: '#414957', 800: '#2D3340', 900: '#1E222B' },
        or: { 50: '#FBF8F1', 100: '#F5EDD9', 200: '#E9D9AE', 300: '#DBC07C', 400: '#CBA451', 500: '#B98B2E', 600: '#9C7124', 700: '#7A581F', 800: '#5C421C', 900: '#453219' },
        // Palette d'état réservée : jamais utilisée comme couleur de série
        etat: { bon: '#0CA30C', attention: '#FAB219', serieux: '#EC835A', critique: '#D03B3B' },
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif'] },
      boxShadow: {
        card: '0 1px 2px rgba(13,32,51,.04), 0 8px 24px -12px rgba(13,32,51,.16)',
        'card-hover': '0 2px 4px rgba(13,32,51,.06), 0 24px 48px -20px rgba(13,32,51,.28)',
        float: '0 12px 32px -8px rgba(13,32,51,.35)',
      },
    },
  },
  plugins: [],
}
