export default function ExecutiveSummary({ data }) {

  const cards = [
    {
      title: "Estimated Monthly Loss",
      value: data.estimated_loss,
      color: "#da3633"
    },
    {
      title: "Risk Reduction",
      value: data.risk_reduction,
      color: "#2ea043"
    },
    {
      title: "Compliance Score",
      value: `${data.compliance_score}%`,
      color: "#1f6feb"
    },
    {
      title: "Mean Detection Time",
      value: data.mean_detection_time,
      color: "#d29922"
    }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

      <div style={{
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: "10px",
        padding: "18px"
      }}>

        <div style={{
          color: "#da3633",
          fontWeight: 700,
          marginBottom: "8px"
        }}>
          ⚠️ Executive Security Summary
        </div>

        <div style={{
          color: "#c9d1d9",
          lineHeight: "1.6",
          fontSize: "14px"
        }}>
          {data.summary}
        </div>

      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: "12px"
         }}>

        {cards.map((card, idx) => (
          <div key={idx} style={{
            background: "#161b22",
            border: "1px solid #30363d",
            borderRadius: "10px",
            padding: "16px"
          }}>

            <div style={{
              color: "#8b949e",
              fontSize: "12px",
              marginBottom: "8px"
            }}>
              {card.title}
            </div>

            <div style={{
              color: card.color,
              fontSize: "26px",
              fontWeight: 700
            }}>
              {card.value}
            </div>

          </div>
        ))}

      </div>

    </div>
  );
}