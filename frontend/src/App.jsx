import { useEffect, useState } from "react";

function App() {
  const [apiStatus, setApiStatus] = useState("checking...");

  useEffect(() => {
    const controller = new AbortController();

    fetch(
      import.meta.env.VITE_API_URL ??
        "http://localhost:10000/api/payment/health",
      {
        signal: controller.signal,
      }
    )
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`status ${response.status}`);
        }
        const data = await response.json();
        setApiStatus(data.status ?? "ok");
      })
      .catch((error) => {
        setApiStatus(`unreachable (${error.message})`);
      });

    return () => controller.abort();
  }, []);

  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>Secure Payment Gateway Prototype</h1>
      <p>API health status: {apiStatus}</p>
      <p>
        Ready to integrate checkout UI, 3DS flows, and tokenization widgets once
        backend services are implemented.
      </p>
    </main>
  );
}

export default App;
