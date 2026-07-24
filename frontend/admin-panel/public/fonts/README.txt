Drop the Dana font files here so the @font-face rules in src/app/globals.css resolve:

  Dana-UltraLight.woff2   Dana-UltraLight.woff   (font-weight: 200)
  Dana-Regular.woff2      Dana-Regular.woff      (font-weight: 400)
  Dana-Bold.woff2         Dana-Bold.woff         (font-weight: 700)

Until these files are present the UI gracefully falls back to system-ui (font-display: swap).
