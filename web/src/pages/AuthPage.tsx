import { FormEvent, useState } from "react";
import { api, apiErrorMessage, type User } from "../lib/api";
import { AuthArt, T2Logo } from "../components/Brand";
import { ErrorBanner } from "../components/Ui";

export function AuthPage({ onAuth }: { onAuth: (user: User) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [alliance, setAlliance] = useState("Альянс Центр");
  const [category, setCategory] = useState<User["employeeCategory"]>("adult");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registered, setRegistered] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await api.register({
          full_name: name,
          email,
          password,
          alliance,
          employeeCategory: category,
        });
        setRegistered(true);
        setMode("login");
      } else {
        await api.login(email, password);
        onAuth(await api.me());
      }
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
          <T2Logo compact />
          <h1>{mode === "login" ? "Вход" : "Регистрация"}</h1>
          <ErrorBanner message={error} />
          {registered ? (
            <div className="success-banner">Аккаунт создан. После подтверждения можно войти.</div>
          ) : null}

          {mode === "register" ? (
            <input required placeholder="ФИО" value={name} onChange={(event) => setName(event.target.value)} />
          ) : null}
          <input required type="email" placeholder="Почта" value={email} onChange={(event) => setEmail(event.target.value)} />
          <input
            required
            minLength={8}
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {mode === "register" ? (
            <>
              <input required placeholder="Группа" value={alliance} onChange={(event) => setAlliance(event.target.value)} />
              <select value={category} onChange={(event) => setCategory(event.target.value as User["employeeCategory"])}>
                <option value="adult">Взрослый сотрудник</option>
                <option value="minor_student">16-18 лет, учащийся</option>
                <option value="minor_not_student">16-18 лет, не учащийся</option>
              </select>
            </>
          ) : null}

          <button className="button button--primary" disabled={loading} type="submit">
            {loading ? "Подождите..." : mode === "login" ? "Войти" : "Зарегистрироваться"}
          </button>
          <button className="link-button" type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
          </button>
        </form>
      </section>
    </main>
  );
}
