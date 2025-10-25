import React from "react"
import { createRoot } from "react-dom/client"
import App from "./App"

const rootElement = document.getElementById("root")

if (!rootElement) {
  throw new Error(
    'Root element with id="root" not found in index.html. Make sure the HTML file contains <div id="root"></div>',
  )
}

const root = createRoot(rootElement)

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
