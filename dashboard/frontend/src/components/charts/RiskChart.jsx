import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer
} from "recharts";

const COLORS = [
  "#da3633",
  "#e3b341",
  "#1f6feb",
  "#2ea043",
  "#8957e5"
];

export default function RiskChart({ findings = [] }) {

  const counts = {
    Authentication: 0,
    API: 0,
    Database: 0,
    Security: 0,
    AI: 0
  };

  findings.forEach(f => {

    const file = (f.file || "").toLowerCase();

    if (file.includes("auth")) counts.Authentication++;
    else if (file.includes("api")) counts.API++;
    else if (file.includes("db")) counts.Database++;
    else if (file.includes("security")) counts.Security++;
    else counts.AI++;

  });

  const data = Object.entries(counts).map(([name, value]) => ({
    name,
    value
  }));

  return (
    <div style={{
      width: "100%",
      height: "320px"
    }}>

      <ResponsiveContainer>

        <PieChart>

          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            outerRadius={100}
            label
          >
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>

          <Tooltip />

        </PieChart>

      </ResponsiveContainer>

    </div>
  );
}