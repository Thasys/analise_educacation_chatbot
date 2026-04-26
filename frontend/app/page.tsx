export default function HomePage() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        textAlign: 'center',
      }}
    >
      <h1 style={{ fontSize: '2.25rem', marginBottom: '0.75rem' }}>
        Análise Educacional Comparada
      </h1>
      <p style={{ opacity: 0.75, marginBottom: '2rem' }}>
        Brasil × Internacional · Fase 0 — Bootstrap
      </p>
      <section
        style={{
          background: '#121a2b',
          padding: '1.25rem 1.5rem',
          borderRadius: 12,
          border: '1px solid #1e2a44',
          maxWidth: 560,
        }}
      >
        <p style={{ margin: 0, marginBottom: 8 }}>Serviços esperados:</p>
        <ul style={{ textAlign: 'left', margin: 0, paddingLeft: '1.25rem', lineHeight: 1.8 }}>
          <li>
            Frontend (Next.js 14) — <code>http://localhost:3000</code>
          </li>
          <li>
            API (FastAPI) — <code>{apiBase}/docs</code>
          </li>
          <li>
            Prefect UI — <code>http://localhost:4200</code>
          </li>
          <li>
            Adminer (Postgres) — <code>http://localhost:8080</code>
          </li>
        </ul>
      </section>
    </main>
  );
}
