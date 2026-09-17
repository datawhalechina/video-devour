import { Loader2, FolderOpen } from "lucide-react";

export function PageHeader({ title, description, actions }) {
  return (
    <header className="vd-page-header">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="vd-page-actions">{actions}</div>}
    </header>
  );
}

export function Workspace({
  title,
  description,
  actions,
  toolbar,
  footer,
  children,
  className = "",
}) {
  return (
    <main className={`vd-page ${className}`}>
      <PageHeader title={title} description={description} actions={actions} />
      {toolbar && <div className="vd-toolbar">{toolbar}</div>}
      <div className="vd-page-body" tabIndex={0} aria-label={`${title}内容`}>
        {children}
      </div>
      {footer && <footer className="vd-page-footer">{footer}</footer>}
    </main>
  );
}

export function Button({
  variant = "secondary",
  className = "",
  children,
  ...props
}) {
  return (
    <button
      type="button"
      className={`vd-button vd-button--${variant} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Segmented({
  label,
  value,
  onChange,
  options,
  variant = "light",
}) {
  return (
    <div
      className={`vd-segmented vd-segmented--${variant}`}
      role="group"
      aria-label={label}
    >
      {options.map((option) => (
        <button
          type="button"
          key={option.value}
          aria-pressed={value === option.value}
          aria-label={option.ariaLabel}
          title={option.ariaLabel}
          onClick={() => onChange(option.value)}
        >
          {option.label}
          {option.count !== undefined && <small>{option.count}</small>}
        </button>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  loading,
  action,
  icon: Icon = FolderOpen,
}) {
  return (
    <section className="vd-empty" role="status">
      {loading ? <Loader2 className="animate-spin" /> : <Icon />}
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action}
    </section>
  );
}
