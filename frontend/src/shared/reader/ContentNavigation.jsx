import { CONTENT_OPTIONS } from "./contentOptions";

export default function ContentNavigation({ value, onChange, disabledKeys = [] }) {
  return (
    <nav className="vd-content-navigation" aria-label="报告与学习内容">
      <div className="vd-content-navigation-row">
        {CONTENT_OPTIONS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={value === key}
            disabled={disabledKeys.includes(key)}
            onClick={() => onChange(key)}
          >
            {label}
          </button>
        ))}
      </div>
    </nav>
  );
}
