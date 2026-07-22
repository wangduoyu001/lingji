import type { ReactNode } from "react";
import type { NavigationIcon } from "../types";

type Props = { name: NavigationIcon; size?: number };

const paths: Record<NavigationIcon, ReactNode> = {
  home: <><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/><path d="M9.5 20v-6h5v6"/></>,
  pulse: <><path d="M3 12h4l2-6 4 12 2-6h6"/></>,
  project: <><path d="M4 5h6l2 2h8v12H4z"/><path d="M4 9h16"/></>,
  review: <><path d="M5 4h14v16H5z"/><path d="m8 12 2.5 2.5L16 9"/></>,
  shield: <><path d="M12 3 5 6v5c0 4.5 2.8 7.6 7 10 4.2-2.4 7-5.5 7-10V6z"/><path d="M9 12h6"/></>,
  inspect: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></>,
  vault: <><path d="M4 6h16v14H4z"/><path d="M8 6V4h8v2"/><circle cx="12" cy="13" r="3"/><path d="M12 10v6"/></>,
  capture: <><path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/><circle cx="12" cy="12" r="3"/></>,
  feed: <><path d="M4 4v16h16"/><path d="M7 15c4 0 7-3 7-7"/><path d="M7 10c1.8 0 3-1.2 3-3"/></>,
  media: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/></>,
  queue: <><path d="M6 6h12M6 12h12M6 18h12"/><circle cx="3" cy="6" r=".8"/><circle cx="3" cy="12" r=".8"/><circle cx="3" cy="18" r=".8"/></>,
  vector: <><circle cx="6" cy="7" r="2"/><circle cx="18" cy="7" r="2"/><circle cx="12" cy="18" r="2"/><path d="m7.7 8.1 3.1 7.8M16.3 8.1l-3.1 7.8M8 7h8"/></>,
  compute: <><rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M19 9h3M2 15h3M19 15h3"/></>,
  model: <><path d="M12 3 4 7l8 4 8-4z"/><path d="m4 12 8 4 8-4M4 17l8 4 8-4"/></>,
  storage: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/></>,
  backup: <><path d="M6 8a7 7 0 1 1-1 8"/><path d="M6 3v5H1"/><path d="M12 8v5l3 2"/></>,
  acceptance: <><path d="M4 4h16v16H4z"/><path d="m8 12 2.5 2.5L16 9"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/></>,
  logs: <><path d="M5 3h14v18H5z"/><path d="M8 8h8M8 12h8M8 16h5"/></>,
};

export default function NavIcon({ name, size = 18 }: Props) {
  return <svg className="nav-icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
