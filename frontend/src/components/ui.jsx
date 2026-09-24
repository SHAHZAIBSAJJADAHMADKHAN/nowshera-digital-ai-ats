export function Button({ children, variant = "primary", className = "", ...props }) { return <button className={`button button--${variant} ${className}`} {...props}>{children}</button>; }
export function Spinner({ page = false }) { return <div className={page ? "spinner-page" : "spinner"} role="status"><i /> <span className="sr-only">Loading</span></div>; }
export function Badge({ children, tone = "blue" }) { return <span className={`badge badge--${tone}`}>{children}</span>; }
export function Notice({ children, tone = "error" }) { return <p className={`notice notice--${tone}`} role="alert">{children}</p>; }
