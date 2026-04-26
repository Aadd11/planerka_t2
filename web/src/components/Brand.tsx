import logoBlack from "../assets/t2-logo-brandbook.png";
import logoWhite from "../assets/t2-logo-brandbook-white.png";

export function T2Logo({ compact = false }: { compact?: boolean }) {
  const src = compact ? logoBlack : logoWhite;

  return (
    <span className={compact ? "brand-logo brand-logo--compact" : "brand-logo"} aria-label="t2" role="img">
      <img src={src} alt="" />
    </span>
  );
}

export function AuthArt() {
  return (
    <div className="auth-art" aria-hidden="true">
      <div className="auth-art__plate" />
      <div className="auth-art__card">
        <div className="auth-art__chip" />
        <T2Logo compact />
      </div>
      <div className="auth-art__beam auth-art__beam--one" />
      <div className="auth-art__beam auth-art__beam--two" />
    </div>
  );
}
