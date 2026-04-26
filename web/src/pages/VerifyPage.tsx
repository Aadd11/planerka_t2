import { FormEvent, useState } from "react";
import { api, apiErrorMessage, type User } from "../lib/api";
import { AuthArt } from "../components/Brand";
import { ErrorBanner } from "../components/Ui";

export function VerifyPage({ onVerified }: { onVerified: (user: User) => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      onVerified(await api.verify(token));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <AuthArt />
        <form className="auth-form" onSubmit={submit}>
          <h1>Подтверждение</h1>
          <p>Введите код из письма или токен подтверждения.</p>
          <ErrorBanner message={error} />
          <input required placeholder="Код" value={token} onChange={(event) => setToken(event.target.value)} />
          <button className="button button--primary" disabled={loading} type="submit">
            {loading ? "Проверяем..." : "Подтвердить"}
          </button>
        </form>
      </section>
    </main>
  );
}
