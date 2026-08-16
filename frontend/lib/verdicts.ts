export const VERDICTS = ['Safe', 'Likely Safe', 'Caution', 'Suspicious', 'High Risk', 'Insufficient Data'] as const
export type Verdict = (typeof VERDICTS)[number]

export interface VerdictStyle {
  text: string
  chip: string
  gauge: string
  ring: string
}

export function verdictStyle(verdict: string): VerdictStyle {
  switch (verdict) {
    case 'Safe':
      return {
        text: 'text-emerald-400',
        chip: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
        gauge: 'text-emerald-400',
        ring: '#34d399',
      }
    case 'Likely Safe':
      return {
        text: 'text-lime-400',
        chip: 'bg-lime-500/15 text-lime-300 border-lime-500/40',
        gauge: 'text-lime-400',
        ring: '#a3e635',
      }
    case 'Caution':
      return {
        text: 'text-amber-400',
        chip: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
        gauge: 'text-amber-400',
        ring: '#fbbf24',
      }
    case 'Suspicious':
      return {
        text: 'text-orange-400',
        chip: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
        gauge: 'text-orange-400',
        ring: '#fb923c',
      }
    case 'High Risk':
      return {
        text: 'text-red-400',
        chip: 'bg-red-500/15 text-red-300 border-red-500/40',
        gauge: 'text-red-400',
        ring: '#f87171',
      }
    default:
      return {
        text: 'text-slate-400',
        chip: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
        gauge: 'text-slate-400',
        ring: '#94a3b8',
      }
  }
}

export function signalTone(available: boolean, passed: boolean): string {
  if (!available) return 'bg-slate-800/80 border-slate-700'
  if (passed) return 'bg-emerald-950/40 border-emerald-800/50'
  return 'bg-red-950/40 border-red-800/50'
}

export const CATEGORY_LABELS: Record<string, string> = {
  ssl: 'SSL/TLS',
  domain_trust: 'Domain Trust',
  hosting: 'Hosting',
  reputation: 'Reputation',
  content: 'Content',
  brand: 'Brand Impersonation',
  ml: 'ML Classifier',
  test: 'Check',
}

export const SIGNAL_LABELS: Record<string, string> = {
  ssl_check: 'SSL Certificate',
  whois_check: 'Domain Age & WHOIS',
  dns_hosting: 'DNS & Hosting',
  safe_browsing: 'Google Safe Browsing',
  virustotal: 'VirusTotal',
  urlhaus: 'URLhaus Blocklist',
  openphish: 'OpenPhish Feed',
  local_ml: 'Local ML Classifier',
  domain_lexical: 'URL Structure',
  content_heuristics: 'Page Content',
  typosquat: 'Brand Impersonation',
}