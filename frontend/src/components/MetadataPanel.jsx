export default function MetadataPanel({ metadata }) {
  if (!metadata) return null;

  const sections = [
    { key: 'mobile_numbers', label: '📱 Mobile Numbers', icon: '📱' },
    { key: 'emails', label: '📧 Email IDs', icon: '📧' },
    { key: 'upi_ids', label: '💳 UPI / Payment IDs', icon: '💳' },
    { key: 'telegram_links', label: '✈️ Telegram Links', icon: '✈️' },
    { key: 'instagram_links', label: '📷 Instagram Links', icon: '📷' },
    { key: 'whatsapp_links', label: '💬 WhatsApp Links', icon: '💬' },
    { key: 'crypto_addresses', label: '🔐 Crypto Addresses', icon: '🔐' },
  ];

  const hasAny = sections.some(s => metadata[s.key]?.length > 0);
  if (!hasAny) return null;

  return (
    <div className="meta-panel">
      <div className="db-drawer-section">🔍 Extracted identifiers — for legal-process triangulation</div>
      <div className="meta-note">
        These identifiers were found in public content. Mobile numbers from UPI IDs are also surfaced.
        Use these in a Section 91 BNSS production order to obtain subscriber records.
      </div>
      {sections.map(({ key, label }) => {
        const items = metadata[key];
        if (!items?.length) return null;
        return (
          <div key={key} className="meta-section">
            <div className="meta-section-label">{label}</div>
            <div className="meta-items">
              {items.map((item, i) => (
                <span key={i} className="meta-item">{item}</span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
