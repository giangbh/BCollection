import React from "react";

/**
 * Donut Chart for Debt Structure
 */
export function DonutChart({
  totalLabel = "15,2 tỷ VND",
  items = [
    { label: "Trong hạn", amount: "14,69 tỷ", percent: 96.7, color: "#10B981" },
    { label: "Quá hạn", amount: "12,5 triệu", percent: 0.1, color: "#EF4444" },
    { label: "Khác", amount: "0,51 tỷ", percent: 3.2, color: "#94A3B8" },
  ],
}: {
  totalLabel?: string;
  items?: { label: string; amount: string; percent: number; color: string }[];
}) {
  const size = 160;
  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let cumulativePercent = 0;

  return (
    <div className="bc-donut-card">
      <div className="bc-donut-wrap">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="bc-donut-svg"
          aria-label={`Biểu đồ cấu trúc dư nợ, tổng ${totalLabel}`}
        >
          {items.map((item, idx) => {
            const strokeDasharray = `${(item.percent / 100) * circumference} ${circumference}`;
            const strokeDashoffset = -((cumulativePercent / 100) * circumference);
            cumulativePercent += item.percent;

            return (
              <circle
                key={idx}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke={item.color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
              />
            );
          })}
        </svg>
        <div className="bc-donut-center">
          <div className="bc-donut-value">{totalLabel}</div>
        </div>
      </div>
      <div className="bc-donut-legend">
        {items.map((item, idx) => (
          <div key={idx} className="bc-donut-legend-row">
            <span
              className="bc-donut-dot"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            <span className="bc-donut-legend-name">{item.label}</span>
            <span className="bc-donut-legend-val">
              {item.amount} ({item.percent.toFixed(1).replace(".", ",")}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * 12-Month DPD Bar Chart
 */
export function BarChartDpd({
  data = [
    { month: "T10", year: 2024, maxDpd: 0, avgDpd: 0 },
    { month: "T11", year: 2024, maxDpd: 0, avgDpd: 0 },
    { month: "T12", year: 2024, maxDpd: 2, avgDpd: 1 },
    { month: "T01", year: 2025, maxDpd: 0, avgDpd: 0 },
    { month: "T02", year: 2025, maxDpd: 4, avgDpd: 2 },
    { month: "T03", year: 2025, maxDpd: 0, avgDpd: 0 },
    { month: "T04", year: 2025, maxDpd: 8, avgDpd: 3 },
    { month: "T05", year: 2025, maxDpd: 10, avgDpd: 4 },
    { month: "T06", year: 2025, maxDpd: 15, avgDpd: 6 },
    { month: "T07", year: 2025, maxDpd: 12, avgDpd: 5 },
    { month: "T08", year: 2025, maxDpd: 20, avgDpd: 8 },
    { month: "T09", year: 2025, maxDpd: 28, avgDpd: 14 },
  ],
}: {
  data?: { month: string; year: number; maxDpd: number; avgDpd: number }[];
}) {
  const width = 340;
  const height = 140;
  const padLeft = 28;
  const padBottom = 32;
  const padTop = 10;
  const padRight = 10;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;
  const maxVal = 60;
  const stepX = plotWidth / data.length;

  return (
    <div className="bc-barchart-card">
      <div className="bc-barchart-legend">
        <span>
          <span className="bc-bar-dot red" /> DPD cao nhất
        </span>
        <span>
          <span className="bc-bar-dot blue" /> DPD trung bình
        </span>
      </div>
      <div className="bc-barchart-svg-wrap">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="bc-barchart-svg"
          preserveAspectRatio="none"
          aria-label="Biểu đồ biến động DPD 12 tháng"
        >
          {/* Y Axis Grid lines */}
          {[0, 15, 30, 45, 60].map((v) => {
            const y = padTop + plotHeight - (v / maxVal) * plotHeight;
            return (
              <g key={v}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="var(--bc-border, #E2E8F0)"
                  strokeDasharray="2 2"
                />
                <text
                  x={padLeft - 4}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="9"
                  fill="var(--bc-text-dim, #64748B)"
                >
                  {v}
                </text>
              </g>
            );
          })}

          {/* Bars */}
          {data.map((d, i) => {
            const xCenter = padLeft + i * stepX + stepX / 2;
            const barW = 8;
            const barH = Math.max(2, (d.maxDpd / maxVal) * plotHeight);
            const y = padTop + plotHeight - barH;

            const avgH = Math.max(2, (d.avgDpd / maxVal) * plotHeight);
            const avgY = padTop + plotHeight - avgH;

            return (
              <g key={i} className="bc-bar-group">
                <rect
                  x={xCenter - barW / 2}
                  y={y}
                  width={barW}
                  height={barH}
                  rx={2}
                  fill={d.maxDpd > 15 ? "#EF4444" : "#F97316"}
                  opacity={0.85}
                >
                  <title>{`${d.month}/${d.year}: DPD cao nhất ${d.maxDpd} ngày`}</title>
                </rect>

                {d.avgDpd > 0 && (
                  <circle
                    cx={xCenter}
                    cy={avgY}
                    r={3}
                    fill="#3B82F6"
                  >
                    <title>{`${d.month}/${d.year}: DPD trung bình ${d.avgDpd} ngày`}</title>
                  </circle>
                )}

                {/* X labels */}
                <text
                  x={xCenter}
                  y={height - padBottom + 12}
                  textAnchor="middle"
                  fontSize="9"
                  fill="var(--bc-text-dim, #64748B)"
                >
                  {d.month}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="bc-barchart-years">
        <span>2024</span>
        <span>2025</span>
      </div>
    </div>
  );
}

/**
 * Quick Risk Score Circular Gauge
 */
export function GaugeRisk({
  score = 70,
  maxScore = 100,
  riskLabel = "Trung bình cao",
  trend = "Tăng",
  repayAbility = "75 (Cao)",
  coopLevel = "60 (Trung bình)",
  ptpRisk = "30% (Trung bình thấp)",
}: {
  score?: number;
  maxScore?: number;
  riskLabel?: string;
  trend?: string;
  repayAbility?: string;
  coopLevel?: string;
  ptpRisk?: string;
}) {
  const size = 96;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percent = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const strokeDasharray = `${(percent / 100) * circumference} ${circumference}`;

  const strokeColor = score >= 80 ? "#10B981" : score >= 60 ? "#007A80" : "#EF4444";

  return (
    <div className="bc-gauge-card">
      <div className="bc-gauge-left">
        <div className="bc-gauge-circle-wrap">
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            className="bc-gauge-svg"
          >
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke="var(--bc-border, #E2E8F0)"
              strokeWidth={strokeWidth}
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray={strokeDasharray}
              strokeDashoffset={0}
              strokeLinecap="round"
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          </svg>
          <div className="bc-gauge-center">
            <span className="bc-gauge-score">{score}</span>
            <span className="bc-gauge-max">/{maxScore}</span>
          </div>
        </div>
        <div className="bc-gauge-status">
          <span className="bc-gauge-label">Mức độ rủi ro</span>
          <strong className="bc-gauge-risk-val">{riskLabel}</strong>
        </div>
      </div>

      <div className="bc-gauge-metrics">
        <div className="bc-gauge-metric-item">
          <span>Xu hướng</span>
          <strong className="bc-gauge-trend-up">▲ {trend}</strong>
        </div>
        <div className="bc-gauge-metric-item">
          <span>Khả năng trả nợ</span>
          <strong className="bc-gauge-val-high">{repayAbility}</strong>
        </div>
        <div className="bc-gauge-metric-item">
          <span>Mức độ hợp tác</span>
          <strong className="bc-gauge-val-mid">{coopLevel}</strong>
        </div>
        <div className="bc-gauge-metric-item">
          <span>Rủi ro phá PTP</span>
          <strong className="bc-gauge-val-good">{ptpRisk}</strong>
        </div>
      </div>
    </div>
  );
}
