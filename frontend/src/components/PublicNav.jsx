import { Link, NavLink } from "react-router-dom";
import { Menu, X, Sparkles } from "lucide-react";
import { useState } from "react";
export function PublicNav() { const [open, setOpen] = useState(false); return <header className="nav"><Link to="/" className="brand"><span className="brand-mark"><Sparkles size={16}/></span><span>Nowshera <b>Digital</b></span></Link><button className="menu" onClick={() => setOpen(!open)} aria-label="Toggle navigation">{open ? <X/> : <Menu/>}</button><nav className={open ? "nav-links open" : "nav-links"}><NavLink to="/">Home</NavLink><NavLink to="/jobs">Jobs</NavLink><NavLink to="/login">Sign in</NavLink><NavLink className="nav-cta" to="/register">Create account</NavLink></nav></header>; }
