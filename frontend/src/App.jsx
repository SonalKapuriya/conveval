import React, { useState, useRef, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL || '/api'

// ── Helpers ──────────────────────────────────────────────────────────────────
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n))
const avg   = arr => arr.length ? arr.reduce((a,b)=>a+b,0)/arr.length : 0
const scoreColor = s => ['','#1a7a44','#6aaa6a','#c9a227','#c9611a','#c91a1a'][s]
const scoreBg    = s => ['','#e8f5ee','#f0f9f0','#fdf8e8','#fdf0e8','#fde8e8'][s]
const dirColor   = d => d==='negative'?'#c91a1a':d==='positive'?'#1a7a44':'#8a8680'

const DEMO_TURNS = [
  {speaker:'user',      text:"I've been feeling completely hopeless lately. Nothing seems to matter anymore."},
  {speaker:'assistant', text:"I'm really sorry to hear you're feeling this way. Can you tell me more about what's been going on?"},
  {speaker:'user',      text:"I don't know. I just feel like nobody actually cares whether I'm here or not."},
]

// ── API ───────────────────────────────────────────────────────────────────────
async function callEvaluate(turn_id, speaker, text, context) {
  const r = await fetch(`${API}/evaluate`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({turn_id, speaker, text, context, batch_size:25}),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`, {signal: AbortSignal.timeout(4000)})
    return r.ok ? r.json() : null
  } catch { return null }
}

// ── Components ────────────────────────────────────────────────────────────────

function Header({ health, mockMode }) {
  return (
    <header style={{
      borderBottom: '3px solid var(--ink)', padding: '0 32px',
      display: 'flex', alignItems: 'stretch', gap: 0, background: 'var(--paper)',
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{ padding: '16px 24px 16px 0', borderRight: '2px solid var(--ink)', display:'flex', alignItems:'center', gap: 12 }}>
        <div style={{ width: 36, height: 36, background: 'var(--ink)', display:'flex', alignItems:'center', justifyContent:'center' }}>
          <span style={{ color: 'var(--paper)', fontFamily: 'var(--mono)', fontSize: 11, fontWeight:500 }}>CV</span>
        </div>
        <div>
          <div style={{ fontFamily:'var(--syne)', fontWeight: 800, fontSize: 15, letterSpacing:'-0.02em' }}>CONVEVAL</div>
          <div style={{ fontFamily:'var(--mono)', fontSize: 9, color:'var(--muted)', letterSpacing:'0.1em' }}>FACET EVALUATOR</div>
        </div>
      </div>

      <div style={{ flex:1, display:'flex', alignItems:'center', padding:'0 24px', gap: 16 }}>
        <div style={{ fontFamily:'var(--serif)', fontStyle:'italic', fontSize: 13, color:'var(--muted)' }}>
          399 facets · 16 batch stages · Mistral-powered
        </div>
      </div>

      <div style={{ display:'flex', alignItems:'center', gap: 8, padding:'0 0 0 24px', borderLeft:'2px solid var(--ink)' }}>
        {mockMode && (
          <div style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--warn)',
            border:'1px solid var(--warn)', padding:'3px 8px', borderRadius: 'var(--r)' }}>
            MOCK MODE
          </div>
        )}
        <div style={{ display:'flex', alignItems:'center', gap: 6 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: health ? 'var(--safe)' : '#c91a1a',
            boxShadow: health ? '0 0 6px var(--safe)' : '0 0 6px #c91a1a',
          }}/>
          <span style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--muted)' }}>
            {health ? `API · ${health.facets} facets` : 'OFFLINE'}
          </span>
        </div>
      </div>
    </header>
  )
}

function TurnBubble({ turn, index, isLatest }) {
  const isUser = turn.speaker === 'user'
  return (
    <div style={{
      display:'flex', flexDirection:'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
      animation: 'slideIn 0.2s ease',
    }}>
      <div style={{
        fontFamily:'var(--mono)', fontSize: 9, color:'var(--muted)',
        letterSpacing:'0.1em', textTransform:'uppercase',
        marginBottom: 4,
      }}>
        {turn.speaker} · T{String(index+1).padStart(2,'0')}
        {isLatest && <span style={{ marginLeft: 6, color:'var(--accent)' }}>← latest</span>}
      </div>
      <div style={{
        maxWidth: '85%', padding: '10px 14px',
        background: isUser ? 'var(--ink)' : 'var(--cream)',
        color: isUser ? 'var(--paper)' : 'var(--ink)',
        border: isUser ? 'none' : '1.5px solid var(--mid)',
        borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
        fontSize: 13, lineHeight: 1.6, fontFamily:'var(--syne)',
      }}>
        {turn.text}
      </div>
    </div>
  )
}

function ScoreBadge({ score }) {
  return (
    <div style={{
      display:'inline-flex', alignItems:'center', justifyContent:'center',
      width: 24, height: 24, borderRadius: 'var(--r)',
      background: scoreBg(score), border: `1.5px solid ${scoreColor(score)}`,
      fontFamily:'var(--mono)', fontSize: 11, fontWeight:500,
      color: scoreColor(score),
    }}>
      {score}
    </div>
  )
}

function ConfBar({ value }) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap: 6 }}>
      <div style={{ width: 48, height: 4, background: 'var(--cream)', borderRadius: 2, overflow:'hidden', border:'1px solid var(--mid)' }}>
        <div style={{ width:`${value*100}%`, height:'100%', background:'var(--accent2)', borderRadius:2 }}/>
      </div>
      <span style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--muted)' }}>
        {(value*100).toFixed(0)}%
      </span>
    </div>
  )
}

function SummaryPanel({ result }) {
  const { summary } = result
  const cats = Object.entries(summary.category_averages || {}).sort((a,b)=>b[1]-a[1])
  const maxCat = cats[0]?.[1] || 5

  return (
    <div style={{ display:'flex', flexDirection:'column', gap: 20 }}>
      {/* Big stats row */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap: 12 }}>
        {[
          { label:'AVG SCORE', value: summary.avg_score, sub:`/ 5.0 · ${summary.total_facets} facets` },
          { label:'AVG CONFIDENCE', value:`${(summary.avg_confidence*100).toFixed(0)}%`, sub:'model certainty' },
          { label:'HIGH RISK', value: summary.high_risk?.length || 0, sub:'score ≥4, direction: negative', danger: summary.high_risk?.length > 0 },
        ].map(s => (
          <div key={s.label} style={{
            border: `2px solid ${s.danger ? 'var(--danger)' : 'var(--ink)'}`,
            padding: 16, background: s.danger ? '#fde8e8' : 'var(--paper)',
          }}>
            <div style={{ fontFamily:'var(--mono)', fontSize: 9, color:'var(--muted)', letterSpacing:'0.12em', marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontFamily:'var(--syne)', fontWeight:800, fontSize: 28, color: s.danger?'var(--danger)':'var(--ink)', letterSpacing:'-0.02em' }}>{s.value}</div>
            <div style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--muted)', marginTop: 2 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Routing info */}
      <div style={{ border:'1.5px solid var(--mid)', padding: 14, background:'var(--cream)', borderRadius: 'var(--r)' }}>
        <div style={{ fontFamily:'var(--mono)', fontSize: 9, color:'var(--muted)', letterSpacing:'0.1em', marginBottom: 8 }}>STAGE 1 — ROUTING CONTEXT</div>
        <div style={{ display:'flex', gap: 12, flexWrap:'wrap' }}>
          {Object.entries(summary.routing || {}).map(([k,v]) => (
            <div key={k} style={{ display:'flex', gap: 4, alignItems:'center' }}>
              <span style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--muted)' }}>{k}:</span>
              <span style={{ fontFamily:'var(--mono)', fontSize: 10, fontWeight:500,
                color: k==='risk_flag'&&v ? 'var(--danger)' : 'var(--ink)',
                background: 'var(--paper)', padding:'1px 6px', borderRadius: 'var(--r)', border:'1px solid var(--mid)' }}>
                {Array.isArray(v) ? v.join(', ') || '—' : String(v)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* High-risk alert */}
      {summary.high_risk?.length > 0 && (
        <div style={{ border:'2px solid var(--danger)', padding: 14, background:'#fde8e8' }}>
          <div style={{ fontFamily:'var(--mono)', fontSize: 9, color:'var(--danger)', letterSpacing:'0.1em', marginBottom: 8 }}>⚠ HIGH-RISK SIGNALS DETECTED</div>
          <div style={{ display:'flex', gap: 6, flexWrap:'wrap' }}>
            {summary.high_risk.map(r => (
              <div key={r.name} style={{
                padding:'3px 10px', border:'1px solid var(--danger)',
                fontFamily:'var(--mono)', fontSize: 10, color:'var(--danger)',
                background:'white', borderRadius:'var(--r)',
              }}>
                {r.name} <strong>({r.score}/5)</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category bars */}
      <div>
        <div style={{ fontFamily:'var(--mono)', fontSize: 9, color:'var(--muted)', letterSpacing:'0.12em', marginBottom: 12 }}>CATEGORY AVERAGES</div>
        <div style={{ display:'flex', flexDirection:'column', gap: 8 }}>
          {cats.map(([cat, val]) => {
            const pct = (val/5*100).toFixed(0)
            const col = val >= 4 ? 'var(--danger)' : val >= 3 ? 'var(--warn)' : val >= 2 ? 'var(--accent2)' : 'var(--mid)'
            return (
              <div key={cat} style={{ display:'grid', gridTemplateColumns:'180px 1fr 36px', gap: 10, alignItems:'center' }}>
                <div style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--ink)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{cat}</div>
                <div style={{ height: 6, background:'var(--cream)', border:'1px solid var(--mid)', borderRadius:3, overflow:'hidden' }}>
                  <div style={{ width:`${pct}%`, height:'100%', background:col, transition:'width 0.6s ease' }}/>
                </div>
                <div style={{ fontFamily:'var(--mono)', fontSize: 10, fontWeight:500, textAlign:'right' }}>{val}</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Stage log */}
      <div>
        <div style={{ fontFamily:'var(--mono)', fontSize: 9, color:'var(--muted)', letterSpacing:'0.12em', marginBottom: 8 }}>PIPELINE LOG</div>
        <div style={{ background:'var(--ink)', padding: 12, borderRadius:'var(--r)', fontFamily:'var(--mono)', fontSize: 10, lineHeight:1.8, color:'var(--mid)' }}>
          {(result.stage_log||[]).map((l,i) => (
            <div key={i} style={{ color: l.startsWith('Stage')?'var(--gold)':l.includes('→')?'#a0c8ff':'var(--mid)' }}>{l}</div>
          ))}
          {result.mock_mode && <div style={{ color:'var(--warn)', marginTop:4 }}>⚠ Mock mode — set MISTRAL_API_KEY for real scores</div>}
        </div>
      </div>
    </div>
  )
}

function FacetTable({ scores }) {
  const [search, setSearch] = useState('')
  const [dirFilter, setDirFilter] = useState('all')
  const [catFilter, setCatFilter] = useState('all')
  const [sortBy, setSortBy] = useState('score-desc')


  const cats = ['all', ...new Set(scores.map(s=>s.category))]

  let filtered = scores
  if (search) filtered = filtered.filter(s=>s.facet_name.toLowerCase().includes(search.toLowerCase())||s.category.toLowerCase().includes(search.toLowerCase()))
  if (dirFilter !== 'all') filtered = filtered.filter(s=>s.direction===dirFilter)
  if (catFilter !== 'all') filtered = filtered.filter(s=>s.category===catFilter)

  filtered = [...filtered].sort((a,b) => {
    if (sortBy==='score-desc') return b.score - a.score
    if (sortBy==='score-asc')  return a.score - b.score
    if (sortBy==='conf-desc')  return b.confidence - a.confidence
    if (sortBy==='name')       return a.facet_name.localeCompare(b.facet_name)
    return 0
  })

  return (
    <div>
      {/* Controls */}
      <div style={{ display:'flex', gap: 8, marginBottom: 14, flexWrap:'wrap', alignItems:'center' }}>
        <input
          placeholder="Search facets…"
          value={search}
          onChange={e=>setSearch(e.target.value)}
          style={{
            border:'1.5px solid var(--mid)', borderRadius:'var(--r)', padding:'6px 10px',
            fontFamily:'var(--mono)', fontSize: 11, background:'var(--paper)', color:'var(--ink)',
            outline:'none', width: 180,
          }}
        />
        <select value={dirFilter} onChange={e=>setDirFilter(e.target.value)}
          style={{ border:'1.5px solid var(--mid)', borderRadius:'var(--r)', padding:'6px 8px',
            fontFamily:'var(--mono)', fontSize: 10, background:'var(--paper)', color:'var(--ink)' }}>
          <option value="all">All directions</option>
          <option value="positive">▲ Positive</option>
          <option value="negative">▼ Negative</option>
          <option value="neutral">○ Neutral</option>
        </select>
        <select value={catFilter} onChange={e=>setCatFilter(e.target.value)}
          style={{ border:'1.5px solid var(--mid)', borderRadius:'var(--r)', padding:'6px 8px',
            fontFamily:'var(--mono)', fontSize: 10, background:'var(--paper)', color:'var(--ink)', maxWidth:180 }}>
          {cats.map(c=><option key={c} value={c}>{c==='all'?'All categories':c}</option>)}
        </select>
        <select value={sortBy} onChange={e=>setSortBy(e.target.value)}
          style={{ border:'1.5px solid var(--mid)', borderRadius:'var(--r)', padding:'6px 8px',
            fontFamily:'var(--mono)', fontSize: 10, background:'var(--paper)', color:'var(--ink)' }}>
          <option value="score-desc">Score ↓</option>
          <option value="score-asc">Score ↑</option>
          <option value="conf-desc">Confidence ↓</option>
          <option value="name">Name A–Z</option>
        </select>
        <span style={{ fontFamily:'var(--mono)', fontSize: 10, color:'var(--muted)', marginLeft:'auto' }}>
          {filtered.length} / {scores.length}
        </span>
      </div>

      {/* Table */}
      <div style={{ border:'1.5px solid var(--mid)', borderRadius:'var(--r)', overflow:'hidden' }}>
        <div style={{ display:'grid', gridTemplateColumns:'24px 1fr 140px 60px 100px 1fr',
          gap: 0, padding:'8px 12px', background:'var(--ink)', borderBottom:'1px solid var(--mid)' }}>
          {['','FACET','CATEGORY','SCORE','CONFIDENCE','REASONING'].map(h=>(
            <div key={h} style={{ fontFamily:'var(--mono)', fontSize:9, color:'var(--mid)', letterSpacing:'0.1em' }}>{h}</div>
          ))}
        </div>
        <div style={{ maxHeight: 480, overflowY:'auto' }}>
          {filtered.map((s,i) => (
            <div key={s.facet_id} style={{
              display:'grid', gridTemplateColumns:'24px 1fr 140px 60px 100px 1fr',
              padding:'8px 12px', borderBottom: i<filtered.length-1?'1px solid var(--cream)':'none',
              background: i%2===0?'var(--paper)':'var(--cream)',
              alignItems:'center', gap: 0, transition:'background 0.1s',
            }}
            onMouseEnter={e=>e.currentTarget.style.background='#ede9d8'}
            onMouseLeave={e=>e.currentTarget.style.background=i%2===0?'var(--paper)':'var(--cream)'}
            >
              <div style={{ width:6, height:6, borderRadius:'50%', background:dirColor(s.direction) }}/>
              <div style={{ fontFamily:'var(--mono)', fontSize:11, fontWeight:500, paddingRight:8,
                overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }} title={s.facet_name}>
                {s.facet_name}
              </div>
              <div style={{ fontSize:10, fontFamily:'var(--mono)', color:'var(--muted)',
                overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', paddingRight:8 }}>
                {s.category}
              </div>
              <div><ScoreBadge score={s.score}/></div>
              <div><ConfBar value={s.confidence}/></div>
              <div style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--muted)',
                overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }} title={s.reasoning}>
                {s.reasoning}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [health, setHealth]       = useState(null)
  const [context, setContext]     = useState([])
  const [text, setText]           = useState('')
  const [speaker, setSpeaker]     = useState('user')
  const [showPaste, setShowPaste] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  
  const [tab, setTab]             = useState('summary')
  const [turnCounter, setTurnCounter] = useState(0)
  const [loadingMsg, setLoadingMsg]   = useState('')
  const convRef  = useRef(null)
  const msgInterval = useRef(null)

  useEffect(() => {
    checkHealth().then(h => setHealth(h))
    const iv = setInterval(() => checkHealth().then(h=>setHealth(h)), 20000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    if (convRef.current) convRef.current.scrollTop = convRef.current.scrollHeight
  }, [context])

  const startLoading = () => {
    const msgs = [
      'Stage 1: Routing context…',
      'Stage 2: Batch 1/16 — scoring 25 facets…',
      'Stage 2: Batch 4/16 — personality traits…',
      'Stage 2: Batch 8/16 — cognitive facets…',
      'Stage 2: Batch 12/16 — spiritual & behavioral…',
      'Stage 2: Batch 16/16 — finalising…',
      'Stage 3: Aggregating 399 scores…',
    ]
    let i = 0
    setLoadingMsg(msgs[0])
    msgInterval.current = setInterval(() => {
      i = (i+1) % msgs.length
      setLoadingMsg(msgs[i])
    }, 900)
  }

  const stopLoading = () => {
    clearInterval(msgInterval.current)
    setLoadingMsg('')
  }

  const addTurn = useCallback(() => {
    if (!text.trim()) return
    setContext(c => [...c, {speaker, text: text.trim()}])
    setText('')
  }, [text, speaker])

  const evaluate = useCallback(async () => {
    if (!text.trim()) return
    const currentText = text.trim()
    const newContext  = [...context, {speaker, text: currentText}]
    setContext(newContext)
    setText('')
    setLoading(true)
    startLoading()
    const tc = turnCounter + 1
    setTurnCounter(tc)

    try {
      const contextPayload = context.map(c=>({speaker:c.speaker, text:c.text}))
      const res = await callEvaluate(
        `T${String(tc).padStart(3,'0')}`, speaker, currentText, contextPayload
      )
      setResult(res)
      setTab('summary')
    } catch(e) {
      console.error(e)
      alert('Evaluation failed: ' + e.message)
    } finally {
      stopLoading()
      setLoading(false)
    }
  }, [text, speaker, context, turnCounter])

  const loadDemo = () => {
    setContext(DEMO_TURNS.slice(0,2))
    setText(DEMO_TURNS[2].text)
    setSpeaker('user')
    setResult(null)
  }

  const clearAll = () => {
    setContext([])
    setText('')
    setResult(null)
    setTurnCounter(0)
  }
  function parseAndLoadChat() {
  const lines = pasteText.trim().split('\n').filter(l => l.trim())
  const parsed = []

  for (const line of lines) {
    const userMatch      = line.match(/^(user|human|you)\s*[:\]]\s*(.+)/i)
    const assistantMatch = line.match(/^(assistant|bot|ai|system)\s*[:\]]\s*(.+)/i)

    if (userMatch) {
      parsed.push({ speaker: 'user', text: userMatch[2].trim() })
    } else if (assistantMatch) {
      parsed.push({ speaker: 'assistant', text: assistantMatch[2].trim() })
    }
  }

  if (parsed.length === 0) {
    alert('Could not parse chat. Use format:\nUser: message\nAssistant: reply')
    return
  }

  setContext(parsed)
  setPasteText('')
  setShowPaste(false)
}

  const mockMode = health ? health.mock_mode : true

  return (
    <div style={{ minHeight:'100vh', display:'flex', flexDirection:'column' }}>
      <style>{`
        @keyframes slideIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin    { to{transform:rotate(360deg)} }
        @keyframes pulse   { 0%,100%{opacity:1}50%{opacity:0.4} }
      `}</style>

      <Header health={health} mockMode={mockMode}/>

      <div style={{ display:'grid', gridTemplateColumns:'400px 1fr', flex:1, overflow:'hidden' }}>

        {/* ── LEFT: Conversation Builder ── */}
        <div style={{ borderRight:'2px solid var(--ink)', display:'flex', flexDirection:'column', overflow:'hidden' }}>

          {/* Label */}
          <div style={{ padding:'14px 20px', borderBottom:'1.5px solid var(--mid)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
            <div style={{ fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.12em', color:'var(--muted)' }}>CONVERSATION BUILDER</div>
            <div style={{ display:'flex', gap: 8 }}>
              <button onClick={loadDemo} style={{
                fontFamily:'var(--mono)', fontSize:9, letterSpacing:'0.08em',
                padding:'4px 10px', border:'1px solid var(--mid)', background:'transparent',
                color:'var(--muted)', borderRadius:'var(--r)', transition:'all 0.15s',
              }}
              onMouseEnter={e=>{e.target.style.borderColor='var(--accent2)';e.target.style.color='var(--accent2)'}}
              onMouseLeave={e=>{e.target.style.borderColor='var(--mid)';e.target.style.color='var(--muted)'}}>
                DEMO
              </button>
              <button onClick={clearAll} style={{
                fontFamily:'var(--mono)', fontSize:9, letterSpacing:'0.08em',
                padding:'4px 10px', border:'1px solid var(--mid)', background:'transparent',
                color:'var(--muted)', borderRadius:'var(--r)', transition:'all 0.15s',
              }}
              onMouseEnter={e=>{e.target.style.borderColor='var(--danger)';e.target.style.color='var(--danger)'}}
              onMouseLeave={e=>{e.target.style.borderColor='var(--mid)';e.target.style.color='var(--muted)'}}>
                CLEAR
              </button>
              <button onClick={() => setShowPaste(true)} style={{
              fontFamily:'var(--mono)', fontSize:9, letterSpacing:'0.08em',
              padding:'4px 10px', border:'1px solid var(--mid)', background:'transparent',
              color:'var(--muted)', borderRadius:'var(--r)',
              transition:'all 0.15s', }}>
                PASTE CHAT
              </button>
            </div>
          </div>

          {/* Conversation area */}
          <div ref={convRef} style={{ flex:1, overflowY:'auto', padding:'16px 20px', display:'flex', flexDirection:'column', gap: 12 }}>
            {context.length === 0 ? (
              <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap: 8, color:'var(--mid)' }}>
                <div style={{ fontFamily:'var(--serif)', fontStyle:'italic', fontSize: 20 }}>Start a conversation</div>
                <div style={{ fontFamily:'var(--mono)', fontSize: 10, letterSpacing:'0.08em' }}>or click DEMO to load an example</div>
              </div>
            ) : (
              context.map((t,i) => (
                <TurnBubble key={i} turn={t} index={i} isLatest={i===context.length-1}/>
              ))
            )}
          </div>

          {/* Input area */}
          <div style={{ borderTop:'2px solid var(--ink)', padding:'16px 20px', background:'var(--cream)' }}>
            {/* Speaker toggle */}
            <div style={{ display:'flex', marginBottom:10, border:'1.5px solid var(--ink)', borderRadius:'var(--r)', overflow:'hidden' }}>
              {['user','assistant'].map(s=>(
                <button key={s} onClick={()=>setSpeaker(s)} style={{
                  flex:1, padding:'7px', fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.08em',
                  border:'none', background: speaker===s?'var(--ink)':'transparent',
                  color: speaker===s?'var(--paper)':'var(--muted)', transition:'all 0.15s',
                  textTransform:'uppercase',
                }}>{s}</button>
              ))}
            </div>

            <textarea
              value={text}
              onChange={e=>setText(e.target.value)}
              onKeyDown={e=>{ if(e.key==='Enter'&&e.ctrlKey) evaluate() }}
              placeholder="Type a message… (Ctrl+Enter to evaluate)"
              style={{
                width:'100%', border:'1.5px solid var(--mid)', borderRadius:'var(--r)',
                padding:'10px 12px', fontSize:13, lineHeight:1.5, resize:'vertical',
                minHeight:80, background:'var(--paper)', color:'var(--ink)', outline:'none',
                transition:'border 0.2s',
              }}
              onFocus={e=>e.target.style.borderColor='var(--ink)'}
              onBlur={e=>e.target.style.borderColor='var(--mid)'}
            />

            <div style={{ display:'flex', gap: 8, marginTop:10 }}>
              <button onClick={addTurn} disabled={!text.trim()} style={{
                padding:'9px 16px', border:'1.5px solid var(--mid)', borderRadius:'var(--r)',
                background:'transparent', color:'var(--muted)', fontFamily:'var(--mono)',
                fontSize:10, letterSpacing:'0.08em', transition:'all 0.15s',
                opacity: text.trim()?1:0.4,
              }}
              onMouseEnter={e=>{ if(text.trim()){e.target.style.borderColor='var(--ink)';e.target.style.color='var(--ink)'} }}
              onMouseLeave={e=>{e.target.style.borderColor='var(--mid)';e.target.style.color='var(--muted)'}}>
                + ADD
              </button>

              <button onClick={evaluate} disabled={loading||!text.trim()} style={{
                flex:1, padding:'9px', border:'none', borderRadius:'var(--r)',
                background: loading||!text.trim()?'var(--mid)':'var(--ink)',
                color:'var(--paper)', fontFamily:'var(--mono)', fontSize:10,
                letterSpacing:'0.1em', transition:'all 0.15s', cursor: loading||!text.trim()?'not-allowed':'pointer',
              }}>
                {loading ? '⟳ EVALUATING…' : '▶ EVALUATE TURN'}
              </button>
            </div>
          </div>
        </div>

        {/* ── RIGHT: Results ── */}
        <div style={{ display:'flex', flexDirection:'column', overflow:'hidden' }}>

          {/* Results header */}
          <div style={{ padding:'14px 28px', borderBottom:'1.5px solid var(--mid)', display:'flex', alignItems:'center', gap: 16 }}>
            <div style={{ fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.12em', color:'var(--muted)' }}>EVALUATION RESULTS</div>
            {result && (
              <div style={{ marginLeft:'auto', display:'flex', gap: 10 }}>
                <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--muted)',
                  background:'var(--cream)', padding:'2px 8px', border:'1px solid var(--mid)', borderRadius:'var(--r)' }}>
                  {result.scores?.length} facets
                </span>
                <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--muted)',
                  background:'var(--cream)', padding:'2px 8px', border:'1px solid var(--mid)', borderRadius:'var(--r)' }}>
                  {result.duration_ms}ms
                </span>
              </div>
            )}
          </div>

          {/* Tabs */}
          {result && (
            <div style={{ display:'flex', borderBottom:'1.5px solid var(--mid)', padding:'0 28px' }}>
              {[['summary','Summary'],['facets','Facet Scores'],].map(([id,label])=>(
                <button key={id} onClick={()=>setTab(id)} style={{
                  padding:'10px 18px', fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.08em',
                  border:'none', background:'transparent', cursor:'pointer',
                  color: tab===id?'var(--ink)':'var(--muted)',
                  borderBottom: tab===id?'2px solid var(--ink)':'2px solid transparent',
                  marginBottom:'-1.5px', transition:'all 0.15s',
                  textTransform:'uppercase',
                }}>{label}</button>
              ))}
            </div>
          )}

          {/* Content */}
          <div style={{ flex:1, overflowY:'auto', padding:'24px 28px' }}>
            {loading && (
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', gap: 20 }}>
                <div style={{
                  width:40, height:40, border:'3px solid var(--cream)', borderTopColor:'var(--ink)',
                  borderRadius:'50%', animation:'spin 0.7s linear infinite',
                }}/>
                <div style={{ fontFamily:'var(--mono)', fontSize:11, color:'var(--muted)', letterSpacing:'0.08em', textAlign:'center', lineHeight:2 }}>
                  {loadingMsg}
                </div>
                <div style={{ fontFamily:'var(--serif)', fontStyle:'italic', fontSize:13, color:'var(--mid)' }}>
                  Scoring {result ? result.scores?.length : 399} facets in 16 batches…
                </div>
              </div>
            )}

            {!loading && !result && (
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', gap: 16 }}>
                <div style={{ fontFamily:'var(--serif)', fontStyle:'italic', fontSize:28, color:'var(--mid)' }}>
                  No evaluation yet
                </div>
                <div style={{ fontFamily:'var(--mono)', fontSize:11, color:'var(--muted)', textAlign:'center', lineHeight:1.8 }}>
                  Add a conversation turn and click<br/>
                  <strong style={{color:'var(--ink)'}}>▶ EVALUATE TURN</strong> to score across 399 facets
                </div>
                <div style={{ display:'flex', flexDirection:'column', gap: 6, marginTop:8 }}>
                  {['Linguistic Quality · Pragmatics · Safety','Emotion · Personality · Cognition','Spiritual · Behavioral · Lifestyle'].map(t=>(
                    <div key={t} style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--mid)', letterSpacing:'0.06em', textAlign:'center' }}>{t}</div>
                  ))}
                </div>
              </div>
            )}

            {!loading && result && tab==='summary' && <SummaryPanel result={result}/>}
            {!loading && result && tab==='facets'  && <FacetTable scores={result.scores||[]}/>}
          </div>
        </div>
      </div>
    </div>
  )
}
