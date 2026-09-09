import React from 'react'
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7', '#ec4899', '#14b8a6']

/**
 * Renders a chart from a backend visualization spec:
 *   { type:'chart', chart_type, xAxis, yAxis, series, columns }
 * plus the result `rows`.
 */
export default function ChartRenderer({ viz, rows }) {

  if (!viz || viz.type !== 'chart' || !Array.isArray(rows) || rows.length === 0) return null

  const { chart_type = 'bar', xAxis, yAxis, series } = viz
  const ys = (series && series.length ? series : [yAxis]).filter(Boolean)


  // Pie chart needs special horizontal (wide) format support
  let data = rows
  if (chart_type === 'pie') {
    // If single row with many keys/columns, treat headings as labels, row values as values
    const row = rows[0]
    const keys = Object.keys(row || {})
    // Try to infer label column and value columns
    // If more than one y-series, just use the default since it’s ambiguous.
    if (keys.length > 2 && rows.length === 1) {
      // Assume the first/label column is xAxis or the first string column
      let labelKey = xAxis || keys.find(k => typeof row[k] === 'string') || keys[0]
      let valueKeys = keys.filter(k => k !== labelKey)
      // If only numbers otherwise, treat as values
      let isWide = valueKeys.some(k => typeof row[k] === 'number' || (!isNaN(Number(row[k])) && row[k] !== ''))
      if (isWide) {
        // Reshape to [{ label: heading, value: row[heading] }, ...]
        data = valueKeys.map((k) => ({ [labelKey]: k, [ys[0]]: Number(row[k]) }))
      }
    }
    // else, default to standard handling (already correct if data is long)
  }

  // Coerce numeric strings to numbers for the y-series (normal charts)
  if (chart_type !== 'pie') {
    data = rows.map((r) => {
      const out = { ...r }
      ys.forEach((k) => {
        const v = out[k]
        if (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v.replace(/,/g, '')))) {
          out[k] = Number(v.replace(/,/g, ''))
        }
      })
      return out
    })
  }

  const common = { data, margin: { top: 8, right: 16, bottom: 8, left: 0 } }

  return (
    <div className="mt-3 h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        {chart_type === 'line' ? (
          <LineChart {...common}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey={xAxis} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {ys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        ) : chart_type === 'area' ? (
          <AreaChart {...common}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey={xAxis} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {ys.map((k, i) => (
              <Area key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.2} />
            ))}
          </AreaChart>
        ) : chart_type === 'pie' ? (
          <PieChart>
            <Tooltip />
            <Legend />
            <Pie data={data} dataKey={ys[0]} nameKey={xAxis} cx="50%" cy="50%" outerRadius={90} label>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
          </PieChart>
        ) : (
          <BarChart {...common}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey={xAxis} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {ys.map((k, i) => (
              <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
