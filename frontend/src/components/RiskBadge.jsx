export default function RiskBadge({ band }) {
  return <span className={`risk-badge ${String(band).toLowerCase()}`}>{band}</span>;
}
