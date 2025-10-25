export default function Page() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      <div className="max-w-4xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-5xl font-bold mb-4">Secure Payment Gateway Prototype</h1>
          <p className="text-xl text-slate-300">
            A cryptography-focused capstone project for secure commercial transactions
          </p>
        </div>

        {/* Project Overview */}
        <section className="mb-12 bg-slate-800 rounded-lg p-8 border border-slate-700">
          <h2 className="text-2xl font-semibold mb-4">Project Overview</h2>
          <p className="text-slate-300 mb-4">This project implements a secure payment gateway with a focus on:</p>
          <ul className="space-y-2 text-slate-300">
            <li className="flex items-start">
              <span className="text-green-400 mr-3">✓</span>
              <span>PCI-DSS scope reduction through client-side tokenization</span>
            </li>
            <li className="flex items-start">
              <span className="text-green-400 mr-3">✓</span>
              <span>HSM/KMS integration for cryptographic key management</span>
            </li>
            <li className="flex items-start">
              <span className="text-green-400 mr-3">✓</span>
              <span>Non-repudiation via signed receipts (JWS/JWE)</span>
            </li>
            <li className="flex items-start">
              <span className="text-green-400 mr-3">✓</span>
              <span>Fraud detection with rule-based and ML scoring</span>
            </li>
            <li className="flex items-start">
              <span className="text-green-400 mr-3">✓</span>
              <span>Replay attack prevention with per-transaction nonces</span>
            </li>
          </ul>
        </section>

        {/* Architecture */}
        <section className="mb-12 bg-slate-800 rounded-lg p-8 border border-slate-700">
          <h2 className="text-2xl font-semibold mb-4">System Architecture</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-700 rounded p-4">
              <h3 className="font-semibold text-blue-400 mb-2">Frontend</h3>
              <p className="text-sm text-slate-300">React.js with Vite</p>
            </div>
            <div className="bg-slate-700 rounded p-4">
              <h3 className="font-semibold text-blue-400 mb-2">API Gateway</h3>
              <p className="text-sm text-slate-300">FastAPI with rate limiting & auth</p>
            </div>
            <div className="bg-slate-700 rounded p-4">
              <h3 className="font-semibold text-blue-400 mb-2">Order Service</h3>
              <p className="text-sm text-slate-300">FastAPI + PostgreSQL</p>
            </div>
            <div className="bg-slate-700 rounded p-4">
              <h3 className="font-semibold text-blue-400 mb-2">Payment Orchestrator</h3>
              <p className="text-sm text-slate-300">FastAPI + HSM/KMS integration</p>
            </div>
            <div className="bg-slate-700 rounded p-4">
              <h3 className="font-semibold text-blue-400 mb-2">Fraud Engine</h3>
              <p className="text-sm text-slate-300">FastAPI + ML/Rules</p>
            </div>
            <div className="bg-slate-700 rounded p-4">
              <h3 className="font-semibold text-blue-400 mb-2">Reconciliation</h3>
              <p className="text-sm text-slate-300">Batch settlement & verification</p>
            </div>
          </div>
        </section>

        {/* Tech Stack */}
        <section className="mb-12 bg-slate-800 rounded-lg p-8 border border-slate-700">
          <h2 className="text-2xl font-semibold mb-4">Technology Stack</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="font-semibold text-slate-300">Backend</p>
              <p className="text-sm text-slate-400">Python 3.11, FastAPI</p>
            </div>
            <div>
              <p className="font-semibold text-slate-300">Frontend</p>
              <p className="text-sm text-slate-400">React 18, Vite</p>
            </div>
            <div>
              <p className="font-semibold text-slate-300">Database</p>
              <p className="text-sm text-slate-400">PostgreSQL</p>
            </div>
            <div>
              <p className="font-semibold text-slate-300">Message Queue</p>
              <p className="text-sm text-slate-400">RabbitMQ</p>
            </div>
            <div>
              <p className="font-semibold text-slate-300">HSM</p>
              <p className="text-sm text-slate-400">SoftHSM2 (Lab)</p>
            </div>
            <div>
              <p className="font-semibold text-slate-300">Infrastructure</p>
              <p className="text-sm text-slate-400">Docker Compose</p>
            </div>
          </div>
        </section>

        {/* Getting Started */}
        <section className="bg-slate-800 rounded-lg p-8 border border-slate-700">
          <h2 className="text-2xl font-semibold mb-4">Getting Started</h2>
          <div className="space-y-4">
            <div>
              <p className="font-semibold text-slate-300 mb-2">1. Start Infrastructure</p>
              <code className="bg-slate-900 text-green-400 p-3 rounded block text-sm">docker-compose up -d</code>
            </div>
            <div>
              <p className="font-semibold text-slate-300 mb-2">2. Check Service Health</p>
              <code className="bg-slate-900 text-green-400 p-3 rounded block text-sm">
                curl http://localhost:8001/health
              </code>
            </div>
            <div>
              <p className="font-semibold text-slate-300 mb-2">3. Access Frontend</p>
              <code className="bg-slate-900 text-green-400 p-3 rounded block text-sm">http://localhost:3000</code>
            </div>
          </div>
        </section>

        {/* Footer */}
        <div className="mt-12 pt-8 border-t border-slate-700 text-center text-slate-400">
          <p>NT219 Capstone Project - Secure Commercial Transactions</p>
        </div>
      </div>
    </main>
  )
}
