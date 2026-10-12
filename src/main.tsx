import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Bell,
  BrainCircuit,
  Building2,
  Check,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  Clock3,
  Download,
  FileText,
  Filter,
  Layers3,
  CalendarDays,
  MapPin,
  MessageSquareText,
  Search,
  Send,
  SlidersHorizontal,
  Settings2,
  ShieldCheck,
  Sparkles,
  ThumbsUp,
  Users,
  X,
} from 'lucide-react'
import './styles.css'
import { AnalyticsView } from './AnalyticsView'
import { WorkspacePage } from './WorkspacePage'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import { CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, BarElement, ArcElement, PointElement, Tooltip } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, LineElement, BarElement, ArcElement, PointElement, Tooltip, Legend, Filler)

type Status = 'Pending' | 'Acknowledged' | 'Assigned' | 'In Progress' | 'Resolved' | 'Reopened'
type Priority = 'Low' | 'Medium' | 'High' | 'Critical'

type Complaint = {
  id: string
  title: string
  description: string
  location: string
  category: string
  status: Status
  priority: Priority
  time: string
  reporter: string
  reports: number
  assignee: string
  confidence: number
  cluster: string
  affected: string
}

const initialComplaints: Complaint[] = [
  { id: 'CF-1048', title: 'Wi-Fi drops in the north wing', description: 'Connection drops every few minutes during afternoon classes. Multiple floors are affected.', location: 'Engineering Block · Floor 2', category: 'Wi-Fi & Network', status: 'In Progress', priority: 'High', time: '12 min ago', reporter: 'Aarav Sharma', reports: 14, assignee: 'IT Infrastructure', confidence: 96, cluster: 'NET-22', affected: 'North wing' },
  { id: 'CF-1045', title: 'Water leak outside Lab 204', description: 'Water is pooling near the lab entrance and creating a slip risk for students.', location: 'Science Block · Lab 204', category: 'Water Supply', status: 'Assigned', priority: 'Critical', time: '38 min ago', reporter: 'Ishita Rao', reports: 3, assignee: 'Facilities Response', confidence: 91, cluster: 'FAC-08', affected: 'Lab 204' },
  { id: 'CF-1041', title: 'Projector not working in Room 3A', description: 'The projector powers on but does not display the lecture laptop input.', location: 'Main Building · Room 3A', category: 'Classrooms', status: 'Acknowledged', priority: 'Medium', time: '1 hr ago', reporter: 'Kabir Mehta', reports: 6, assignee: 'AV Support', confidence: 88, cluster: 'AV-14', affected: 'Room 3A' },
  { id: 'CF-1037', title: 'Washroom supplies need restocking', description: 'The second-floor washroom is out of soap and paper towels.', location: 'Student Centre · Floor 2', category: 'Cleanliness', status: 'Pending', priority: 'Low', time: '2 hrs ago', reporter: 'Meera Joshi', reports: 2, assignee: 'Campus Services', confidence: 98, cluster: 'OPS-31', affected: 'Student Centre' },
]

const navItems = [
  { label: 'Overview', icon: Activity },
  { label: 'Complaints', icon: ClipboardList, count: '24' },
  { label: 'Analytics', icon: BarChart3 },
  { label: 'Issue clusters', icon: Layers3, count: '8' },
  { label: 'Teams', icon: Users },
]

function App() {
  const [activeNav, setActiveNav] = useState('Overview')
  const [complaints, setComplaints] = useState(initialComplaints)
  const [selectedId, setSelectedId] = useState('CF-1048')
  const [showReport, setShowReport] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [filter, setFilter] = useState<'All' | Priority>('All')
  const [query, setQuery] = useState('')
  const [feedback, setFeedback] = useState(0)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  useEffect(() => {
    if (!showReport) return
    const browseButton = document.querySelector('.upload-zone .secondary-button')
    const fileInput = document.querySelector<HTMLInputElement>('#complaint-image-input')
    if (!browseButton || !fileInput) return
    const openFilePicker = () => fileInput.click()
    browseButton.addEventListener('click', openFilePicker)
    return () => browseButton.removeEventListener('click', openFilePicker)
  }, [showReport])

  useEffect(() => {
    const helperText = document.querySelector('.upload-zone span')
    if (helperText) helperText.textContent = selectedFile ? selectedFile.name : 'Optional · JPG or PNG up to 10MB'
  }, [selectedFile])

  const selectedComplaint = complaints.find((complaint) => complaint.id === selectedId) ?? complaints[0]
  const visibleComplaints = useMemo(() => complaints.filter((complaint) => {
    const matchesFilter = filter === 'All' || complaint.priority === filter
    const haystack = `${complaint.title} ${complaint.category} ${complaint.location}`.toLowerCase()
    return matchesFilter && haystack.includes(query.toLowerCase())
  }), [complaints, filter, query])

  function updateStatus(status: Status) {
    setComplaints((items) => items.map((item) => item.id === selectedComplaint.id ? { ...item, status } : item))
  }

  function createComplaint(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const title = String(form.get('title') || 'New campus issue')
    const next: Complaint = {
      id: `CF-${1050 + complaints.length}`,
      title,
      description: String(form.get('description') || 'Submitted from the student portal.'),
      location: String(form.get('location') || 'Campus location'),
      category: 'Other Facilities', status: 'Pending', priority: 'Medium', time: 'Just now',
      reporter: 'You', reports: 1, assignee: 'Campus triage', confidence: 74, cluster: 'NEW', affected: 'To be reviewed',
    }
    setComplaints((items) => [next, ...items])
    setSelectedId(next.id)
    setShowReport(false)
  }

  function handleImageChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      event.target.value = ''
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      event.target.value = ''
      return
    }
    setSelectedFile(file)
  }

  return (
    <div className={`app-shell ${activeNav !== 'Overview' ? 'workspace-mode' : ''}`}>
      <input id="complaint-image-input" className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleImageChange} />
      <aside className="sidebar">
        <div className="brand-mark"><span>CF</span></div>
        <div className="brand-copy"><strong>CampusFix</strong><small>AI OPERATIONS</small></div>
        <div className="workspace-switcher"><div className="campus-avatar">UC</div><div><strong>Universal College Of Engineering</strong><small>Operations workspace</small></div><ChevronDown size={16} /></div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <div className="nav-label">WORKSPACE</div>
          {navItems.map(({ label, icon: Icon, count }) => <button className={`nav-item ${activeNav === label ? 'active' : ''}`} onClick={() => setActiveNav(label)} key={label}><Icon size={18} /><span>{label}</span>{count && <em>{count}</em>}</button>)}
          <div className="nav-label nav-label-spaced">SYSTEM</div>
          <button className={`nav-item ${activeNav === 'AI insights' ? 'active' : ''}`} onClick={() => setActiveNav('AI insights')}><BrainCircuit size={18} /><span>AI insights</span><span className="beta">BETA</span></button>
          <button className={`nav-item ${activeNav === 'Settings' ? 'active' : ''}`} onClick={() => setActiveNav('Settings')}><Settings2 size={18} /><span>Settings</span></button>
        </nav>
        <div className="sidebar-footer"><div className="status-dot" /> <span>All systems operational</span><ArrowUpRight size={14} /></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumbs"><span>Universal College Of Engineering</span><span>/</span><strong>{activeNav}</strong></div><div className="topbar-actions"><div className="search-wrap"><Search size={16} /><input aria-label="Search complaints" placeholder="Search issues..." value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>⌘ K</kbd></div><button className="icon-button" aria-label="Notifications" onClick={() => setShowNotifications(!showNotifications)}><Bell size={18} /><span className="notification-dot" /></button><div className="user-menu"><div className="user-avatar">DT</div><div><strong>Divyanshi Tripathi</strong><small>Administrator</small></div><ChevronDown size={15} /></div></div></header>
        {showNotifications && <div className="notification-popover"><div className="popover-header"><strong>Notifications</strong><span>3 new</span></div><div className="notification-item"><div className="notification-icon orange"><AlertTriangle size={15} /></div><div><strong>Critical issue needs review</strong><p>Water leak at Science Block · 38 min ago</p></div></div><div className="notification-item"><div className="notification-icon green"><Check size={15} /></div><div><strong>Issue resolved</strong><p>Lighting outage in Library · yesterday</p></div></div></div>}

        <section className="content-wrap">
          {activeNav === 'Overview' ? <>
          <div className="page-heading"><div><p className="eyebrow"><span className="pulse" /> MONDAY, 12 OCTOBER 2026</p><h1>Good morning, Divyanshi <span>✦</span></h1><p className="subheading">Here is what needs your attention across campus today.</p></div><button className="primary-button" onClick={() => setShowReport(true)}>Report an issue</button></div>

          <section className="stat-grid"><StatCard icon={<ClipboardList size={19} />} label="Open complaints" value="24" detail="12% from last week" trend="up" color="blue" /><StatCard icon={<Clock3 size={19} />} label="Avg. resolution time" value="2.4d" detail="0.6d faster this month" trend="down" color="mint" /><StatCard icon={<ShieldCheck size={19} />} label="Resolved this month" value="87%" detail="Above 80% target" trend="up" color="lavender" /><StatCard icon={<CircleHelp size={19} />} label="Needs review" value="5" detail="2 critical priority" trend="alert" color="yellow" /></section>

          <div className="dashboard-grid">
            <section className="panel queue-panel"><div className="panel-heading"><div><p className="section-kicker">LIVE QUEUE</p><h2>Complaints needing attention</h2></div><button className="text-button" onClick={() => setActiveNav('Complaints')}>View all <ArrowUpRight size={15} /></button></div><div className="queue-toolbar"><div className="segmented-control">{(['All', 'Critical', 'High', 'Medium'] as const).map((item) => <button className={filter === item ? 'selected' : ''} onClick={() => setFilter(item)} key={item}>{item}{item !== 'All' && <span>{complaints.filter((complaint) => complaint.priority === item).length}</span>}</button>)}</div><button className="filter-button"><Filter size={15} /> Filters</button></div><div className="complaint-list">{visibleComplaints.map((complaint) => <ComplaintRow key={complaint.id} complaint={complaint} selected={complaint.id === selectedId} onClick={() => setSelectedId(complaint.id)} />)}</div></section>
            <aside className="panel insight-panel"><div className="insight-header"><div className="ai-symbol"><Sparkles size={17} /></div><div><p className="section-kicker">AI INSIGHTS</p><h2>What the data is telling you</h2></div><button className="icon-button subtle"><ArrowUpRight size={16} /></button></div><div className="insight-feature"><div className="insight-feature-top"><div className="trend-icon"><Activity size={19} /></div><span className="insight-tag">RECURRING PATTERN</span></div><h3>North wing network issues are up 34%</h3><p>14 reports in 7 days, concentrated around Engineering Block floors 2–3. This cluster may need an infrastructure audit.</p><button className="insight-link" onClick={() => { setSelectedId('CF-1048'); setActiveNav('Issue clusters') }}>Explore cluster <ArrowUpRight size={14} /></button></div><div className="insight-feature secondary"><div className="mini-chart"><span style={{ height: '38%' }} /><span style={{ height: '55%' }} /><span style={{ height: '42%' }} /><span style={{ height: '68%' }} /><span style={{ height: '61%' }} /><span style={{ height: '84%' }} /><span style={{ height: '96%' }} /></div><div><h3>Most affected location</h3><p>Engineering Block <strong>· 28 reports</strong></p></div></div><div className="ai-footnote"><BrainCircuit size={14} /> AI suggestions are reviewed by your team before action.</div></aside>
          </div>

          <section className="lower-grid"><div className="panel activity-panel"><div className="panel-heading"><div><p className="section-kicker">ACTIVITY</p><h2>Recent updates</h2></div><button className="text-button" onClick={() => setActiveNav('Complaints')}>See activity <ArrowUpRight size={15} /></button></div><div className="timeline"><TimelineItem color="orange" title="Critical complaint assigned" detail="CF-1045 · Facilities Response" time="38 min ago" /><TimelineItem color="blue" title="14 reports grouped into a cluster" detail="North wing network issues · NET-22" time="1 hr ago" /><TimelineItem color="green" title="Complaint marked resolved" detail="CF-1030 · Library lighting" time="3 hrs ago" /></div></div><div className="panel team-panel"><div className="panel-heading"><div><p className="section-kicker">TEAM LOAD</p><h2>Department capacity</h2></div><button className="icon-button subtle" onClick={() => setActiveNav('Teams')}><Settings2 size={16} /></button></div><TeamLoad name="IT Infrastructure" value={72} color="blue" /><TeamLoad name="Facilities Response" value={48} color="orange" /><TeamLoad name="Campus Services" value={31} color="green" /><div className="team-note"><Users size={15} /> 4 teams active <span>·</span> 12 staff online</div></div></section>
          </> : activeNav === 'Analytics' ? <AnalyticsView /> : <WorkspacePage section={activeNav} complaints={complaints} query={query} onQueryChange={setQuery} onSelect={setSelectedId} />}
        </section>
      </main>

      {showReport && <div className="modal-backdrop" onClick={() => setShowReport(false)}><form className="report-modal" onSubmit={createComplaint} onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><p className="section-kicker">STUDENT PORTAL</p><h2>Report a campus issue</h2><p>Our AI will classify and route your report for faster action.</p></div><button type="button" className="icon-button subtle" onClick={() => setShowReport(false)}><X size={18} /></button></div><label>What is the issue? <input required name="title" placeholder="e.g. Broken lights in the library" /></label><label>Location <div className="input-with-icon"><MapPin size={16} /><input required name="location" placeholder="Building, floor, or room" /></div></label><label>Describe what happened <textarea name="description" rows={4} placeholder="Add useful details, safety concerns, or how many people are affected..." /></label><div className="upload-zone"><FileText size={20} /><div><strong>Add a photo</strong><span>Optional · JPG or PNG up to 10MB</span></div><button type="button" className="secondary-button">Browse</button></div><div className="ai-preview"><BrainCircuit size={18} /><div><strong>AI triage preview</strong><p>Category, priority, and team assignment will be suggested after submission.</p></div></div><button className="primary-button submit-button" type="submit"><Send size={17} /> Submit complaint</button></form></div>}

      <section className="detail-drawer"><div className="drawer-heading"><div><p className="section-kicker">SELECTED COMPLAINT</p><h2>{selectedComplaint.id} <span className={`priority-badge ${selectedComplaint.priority.toLowerCase()}`}>{selectedComplaint.priority}</span></h2></div><button className="icon-button subtle"><X size={17} /></button></div><h3>{selectedComplaint.title}</h3><p className="drawer-description">{selectedComplaint.description}</p><div className="drawer-meta"><span><MapPin size={14} /> {selectedComplaint.location}</span><span><Clock3 size={14} /> Reported {selectedComplaint.time}</span></div><div className="ai-assessment"><div className="assessment-heading"><div className="ai-symbol small"><Sparkles size={14} /></div><strong>AI assessment</strong><span>{selectedComplaint.confidence}% confidence</span></div><div className="assessment-row"><span>Category</span><strong>{selectedComplaint.category}</strong></div><div className="assessment-row"><span>Recommended team</span><strong>{selectedComplaint.assignee}</strong></div><div className="confidence-bar"><span style={{ width: `${selectedComplaint.confidence}%` }} /></div></div><div className="status-block"><div className="status-label"><span>Lifecycle status</span><strong>{selectedComplaint.status}</strong></div><div className="status-track">{(['Pending', 'Acknowledged', 'Assigned', 'In Progress', 'Resolved'] as Status[]).map((status) => <button className={status === selectedComplaint.status ? 'current' : ''} key={status} onClick={() => updateStatus(status)} title={`Mark as ${status}`}><span>{status === selectedComplaint.status && <Check size={12} />}</span><small>{status}</small></button>)}</div></div><div className="drawer-footer"><div className="reporter"><div className="small-avatar">{selectedComplaint.reporter.split(' ').map((name) => name[0]).join('').slice(0, 2)}</div><div><small>Reported by</small><strong>{selectedComplaint.reporter}</strong></div></div><button className="secondary-button"><MessageSquareText size={15} /> Add note</button></div><div className="feedback"><div><strong>Was this resolution helpful?</strong><span>Your feedback improves campus operations.</span></div><div className="feedback-stars">{[1, 2, 3, 4, 5].map((value) => <button aria-label={`${value} stars`} className={value <= feedback ? 'rated' : ''} onClick={() => setFeedback(value)} key={value}><ThumbsUp size={14} /></button>)}</div></div></section>
    </div>
  )
}

function StatCard({ icon, label, value, detail, trend, color }: { icon: React.ReactNode, label: string, value: string, detail: string, trend: string, color: string }) { return <div className="stat-card"><div className={`stat-icon ${color}`}>{icon}</div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className={`stat-detail ${trend === 'alert' ? 'alert-detail' : ''}`}>{trend === 'alert' ? <AlertTriangle size={13} /> : <ArrowUpRight size={13} />} {detail}</div></div> }
function ComplaintRow({ complaint, selected, onClick }: { complaint: Complaint, selected: boolean, onClick: () => void }) { return <button className={`complaint-row ${selected ? 'selected' : ''}`} onClick={onClick}><div className={`priority-line ${complaint.priority.toLowerCase()}`} /><div className="complaint-main"><div className="complaint-id">{complaint.id} <span>·</span> {complaint.time}</div><h3>{complaint.title}</h3><div className="complaint-sub"><span><MapPin size={13} /> {complaint.location}</span><span className="category-pill">{complaint.category}</span></div></div><div className="complaint-side"><span className={`priority-badge ${complaint.priority.toLowerCase()}`}>{complaint.priority}</span><span className={`status-text ${complaint.status.toLowerCase().replace(' ', '-')}`}>{complaint.status}</span><span className="report-count">{complaint.reports} reports</span></div></button> }
function TimelineItem({ color, title, detail, time }: { color: string, title: string, detail: string, time: string }) { return <div className="timeline-item"><span className={`timeline-dot ${color}`} /><div><strong>{title}</strong><p>{detail}</p></div><time>{time}</time></div> }
function TeamLoad({ name, value, color }: { name: string, value: number, color: string }) { return <div className="load-row"><div className="load-label"><span>{name}</span><strong>{value}%</strong></div><div className="load-bar"><span className={color} style={{ width: `${value}%` }} /></div></div> }

export default App

createRoot(document.getElementById('root')!).render(<App />)
