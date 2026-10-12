import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowUpRight, BarChart3, Building2, CalendarDays, ChevronDown, Download, Filter, SlidersHorizontal } from 'lucide-react'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, LineElement, BarElement, ArcElement, PointElement, Tooltip, Legend, Filler)

const trendData = {
  labels: ['Sep 13', 'Sep 17', 'Sep 21', 'Sep 25', 'Sep 29', 'Oct 3', 'Oct 7', 'Oct 12'],
  datasets: [{ label: 'Complaints', data: [9, 13, 11, 18, 15, 22, 19, 27], borderColor: '#2b8a68', backgroundColor: 'rgba(67, 153, 114, .12)', fill: true, tension: .4, pointRadius: 3, pointBackgroundColor: '#2b8a68' }],
}
const categoryData = {
  labels: ['Wi-Fi', 'Cleanliness', 'Classrooms', 'Water', 'Electricity', 'Other'],
  datasets: [{ data: [34, 22, 18, 12, 8, 6], backgroundColor: ['#3987bf', '#63ad82', '#c29a50', '#6f77b6', '#cf7650', '#b8c1bd'], borderWidth: 0 }],
}
const locations = [{ name: 'Engineering Block', count: 28, breach: true }, { name: 'Science Block', count: 19, breach: true }, { name: 'Student Centre', count: 12, breach: false }, { name: 'Main Building', count: 9, breach: false }]
const departments = [{ name: 'IT Infrastructure', open: 12, resolved: 91, tone: 'blue' }, { name: 'Facilities Response', open: 8, resolved: 84, tone: 'orange' }, { name: 'Campus Services', open: 4, resolved: 96, tone: 'green' }]

export function AnalyticsView() {
  const [range, setRange] = useState('Last 30 days')
  const [summary, setSummary] = useState({ total: 184, open: 24, critical: 5, resolved: 160, resolved_rate: 87, avg_resolution_days: 2.4 })

  useEffect(() => {
    fetch('/api/analytics', { headers: { 'X-User-Id': '1' } })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('API unavailable')))
      .then((payload) => setSummary(payload.summary))
      .catch(() => undefined)
  }, [])

  function exportReport() {
    const csv = ['Issue,Category,Priority,Status,Location', 'CF-1048,Wi-Fi & Network,High,In Progress,Engineering Block', 'CF-1045,Water Supply,Critical,Assigned,Science Block'].join('\n')
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    link.download = 'campusfix-analytics.csv'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  return <div className="analytics-view">
    <div className="analytics-heading"><div><p className="eyebrow"><BarChart3 size={13} /> ADMIN ANALYTICS</p><h1>Campus performance</h1><p className="subheading">A clearer view of demand, response, and service health.</p></div><div className="analytics-actions"><label className="date-select"><CalendarDays size={15} /><select value={range} onChange={(event) => setRange(event.target.value)}><option>Last 7 days</option><option>Last 30 days</option><option>Last 90 days</option><option>This academic year</option></select><ChevronDown size={14} /></label><button className="secondary-button" onClick={exportReport}><Download size={15} /> Export CSV</button></div></div>
    <div className="analytics-toolbar"><span><strong>{range}</strong> · Updated just now</span><div><button className="filter-button"><Filter size={14} /> Category</button><button className="filter-button"><Filter size={14} /> Department</button><button className="filter-button"><SlidersHorizontal size={14} /> More filters</button></div></div>
    <section className="analytics-stats"><AnalyticsStat label="Total complaints" value={String(summary.total)} detail="Live API summary" tone="blue" /><AnalyticsStat label="Open complaints" value={String(summary.open)} detail="13% of total volume" tone="orange" /><AnalyticsStat label="Critical complaints" value={String(summary.critical)} detail="2 require admin review" tone="red" /><AnalyticsStat label="Resolved" value={`${summary.resolved_rate}%`} detail={`${summary.resolved} complaints resolved`} tone="green" /><AnalyticsStat label="Avg. resolution" value={`${summary.avg_resolution_days}d`} detail="Live API summary" tone="purple" /></section>
    <section className="analytics-grid"><div className="panel chart-panel trend-panel"><div className="panel-heading"><div><p className="section-kicker">VOLUME TREND</p><h2>Complaint activity</h2></div><div className="chart-legend"><span className="legend-dot" /> Complaints <button className="icon-button subtle"><ArrowUpRight size={15} /></button></div></div><div className="chart-wrap"><Line data={trendData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#edf1ef' }, ticks: { color: '#91a09a', font: { size: 10 } } }, x: { grid: { display: false }, ticks: { color: '#91a09a', font: { size: 10 } } } } }} /></div></div><div className="panel chart-panel category-panel"><div className="panel-heading"><div><p className="section-kicker">DISTRIBUTION</p><h2>By category</h2></div><button className="icon-button subtle"><ArrowUpRight size={15} /></button></div><div className="donut-wrap"><Doughnut data={categoryData} options={{ cutout: '67%', plugins: { legend: { display: false } } }} /><div className="donut-total"><strong>184</strong><span>reports</span></div></div><div className="category-legend">{categoryData.labels.map((label, index) => <span key={label}><i style={{ background: categoryData.datasets[0].backgroundColor[index] }} />{label}<strong>{categoryData.datasets[0].data[index]}%</strong></span>)}</div></div></section>
    <section className="analytics-grid lower-analytics"><div className="panel analytics-table-panel"><div className="panel-heading"><div><p className="section-kicker">HOTSPOTS</p><h2>Unresolved by location</h2></div><button className="text-button">View map <ArrowUpRight size={15} /></button></div><div className="analytics-table">{locations.map((location, index) => <div className="analytics-table-row" key={location.name}><span className="rank">0{index + 1}</span><strong>{location.name}</strong><div className="thin-bar"><span style={{ width: `${(location.count / 28) * 100}%` }} /></div><b>{location.count}</b>{location.breach && <span className="sla-badge">SLA risk</span>}</div>)}</div></div><div className="panel analytics-table-panel"><div className="panel-heading"><div><p className="section-kicker">OPERATIONS</p><h2>Department performance</h2></div><button className="icon-button subtle"><ArrowUpRight size={15} /></button></div><div className="analytics-table">{departments.map((department) => <div className="department-row" key={department.name}><div className={`department-avatar ${department.tone}`}><Building2 size={14} /></div><div className="department-name"><strong>{department.name}</strong><span>{department.open} open</span></div><div className="performance"><strong>{department.resolved}%</strong><span>resolved</span></div></div>)}</div></div></section>
    <section className="panel overdue-panel"><div className="panel-heading"><div><p className="section-kicker">ATTENTION REQUIRED</p><h2>SLA breaches and overdue complaints</h2></div><span className="overdue-count"><AlertTriangle size={14} /> 5 overdue</span></div><div className="overdue-list"><div><span className="priority-badge critical">Critical</span><strong>Water leak outside Lab 204</strong><span>Due 2 hours ago · Facilities Response</span><button className="text-button">Review <ArrowUpRight size={14} /></button></div><div><span className="priority-badge high">High</span><strong>Wi-Fi drops in the north wing</strong><span>Due yesterday · IT Infrastructure</span><button className="text-button">Review <ArrowUpRight size={14} /></button></div></div></section>
  </div>
}

function AnalyticsStat({ label, value, detail, tone }: { label: string, value: string, detail: string, tone: string }) { return <div className={`analytics-stat ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div> }
