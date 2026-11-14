import React,{useEffect,useState} from "react";
import {Activity,HeartPulse,BookOpen,CalendarCheck,Medal,Globe2,Brain,Wind,PersonStanding} from "lucide-react";
import {api} from "./api";

const tabs = [
 ["body","Human health map",PersonStanding],
 ["env","Mission environments",Globe2],
 ["routines","Health routines",CalendarCheck],
 ["challenges","Mission challenges",Medal],
 ["education","Health education",BookOpen]
];
const regionPositions = {
 brain:{x:105,y:18,w:70,h:58},
 lungs:{x:83,y:104,w:114,h:75},
 heart:{x:124,y:123,w:35,h:42},
 muscles:{x:69,y:184,w:142,h:112},
 digestive:{x:111,y:177,w:58,h:72},
 sleep:{x:207,y:23,w:36,h:36}
};
export default function App(){
 const [tab,setTab]=useState("body");
 const [systems,setSystems]=useState([]);
 const [active,setActive]=useState("heart");
 const [status,setStatus]=useState(null);
 const [envs,setEnvs]=useState([]);
 const [routines,setRoutines]=useState([]);
 const [challenges,setChallenges]=useState([]);
 const [education,setEducation]=useState([]);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function load(){
  try{
   setError("");
   const [s,e,r,c,ed]=await Promise.all([api.bodySystems(),api.environments(),api.routines(),api.challenges(),api.education()]);
   setSystems(s);setEnvs(e);setRoutines(r);setChallenges(c);setEducation(ed);
  }catch(err){setError(err.message);}
 }
 useEffect(()=>{load()},[]);
 useEffect(()=>{if(tab==="body"&&active)api.bodyStatus(active).then(setStatus).catch(e=>setError(e.message));},[active,tab]);
 async function completeRoutine(id){setBusy(true);try{await api.completeRoutine(id);await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function completeChallenge(id){setBusy(true);try{await api.completeChallenge(id);await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <div className="shell">
  <aside className="sidebar"><div className="brand"><span className="brandmark">A</span><div><b>ASTRA MIND</b><small>HEALTH INTELLIGENCE</small></div></div>
   <div className="navlabel">MISSION HEALTH</div>
   {tabs.map(([key,label,Icon])=><button className={`navitem ${tab===key?"selected":""}`} key={key} onClick={()=>setTab(key)}><Icon size={17}/>{label}</button>)}
   <div className="sidefoot">Research prototype<br/>Simulated extension data</div>
  </aside>
  <main className="main"><header><div><div className="eyebrow">ASTRA MIND / EXTENSION</div><h1>{tabs.find(x=>x[0]===tab)?.[1]}</h1></div><span className="sim-badge">SIMULATED / DEMO</span></header>
   {error&&<div className="error">{error}<button onClick={load}>Retry</button></div>}
   {tab==="body"&&<div className="grid2"><section className="card"><h2>Human health map</h2><p className="muted">Select a highlighted region to view its function and available indicators.</p><svg className="human" viewBox="0 0 280 330" role="img" aria-label="Interactive human body regions">
    <circle cx="140" cy="43" r="31" className="silhouette"/><path d="M113 77 Q140 65 167 77 L188 169 L170 184 L164 139 L177 226 L160 226 L151 177 L150 292 L128 292 L127 177 L115 226 L98 226 L111 139 L105 184 L92 169 Z" className="silhouette"/>
    {Object.entries(regionPositions).map(([key,p])=><rect key={key} x={p.x} y={p.y} width={p.w} height={p.h} rx="12" className={`region ${active===key?"active":""}`} onClick={()=>setActive(key)}><title>{key}</title></rect>)}
    </svg><div className="region-buttons">{systems.map(s=><button key={s.key} className={active===s.key?"chip activechip":"chip"} onClick={()=>setActive(s.key)}>{s.name}</button>)}</div></section>
    <section className="card"><h2>{status?.name||"Body system details"}</h2>{status?<><span className="status grey">Unavailable / no source data</span><p>{status.main_function}</p><h3>Relevant indicators</h3><div className="chips">{status.indicators.map(x=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div><div className="notice">{status.explanation}</div><h3>Suggested actions</h3><ul>{status.suggested_actions.map(x=><li key={x}>{x}</li>)}</ul></>:<p className="muted">Select a region.</p>}</section></div>}
   {tab==="env"&&<div className="cards">{envs.map(e=><section className="card" key={e.id}><span className="status blue">{e.env_type}</span><h2>{e.name}</h2><p>{e.location}</p><p>{e.duration_days} simulated mission days</p><b>Available demo streams</b><div className="chips">{e.streams.map(s=><span key={s}>{s}</span>)}</div><small className="muted">Context: {JSON.stringify(e.context)}</small></section>)}</div>}
   {tab==="routines"&&<section className="card"><h2>Mission health activities</h2><p className="muted">Demonstration schedule only; not an official medical protocol.</p>{routines.length===0?<p>No routines yet.</p>:routines.map(r=><div className="row" key={r.id}><div><b>{r.title}</b><small>{r.kind} · {r.completed?"Completed":"Pending"}</small></div><button disabled={r.completed||busy} onClick={()=>completeRoutine(r.id)}>{r.completed?"Completed":"Mark complete"}</button></div>)}
   <button className="primary" onClick={async()=>{try{await api.createRoutine({kind:"wellbeing",title:"Voluntary well-being check-in",astronaut_id:1});await load()}catch(e){setError(e.message)}}}>Add check-in</button></section>}
   {tab==="challenges"&&<div className="cards">{challenges.map(c=><section className="card" key={c.id}><span className="status blue">{c.points} participation points</span><h2>{c.title}</h2><p>{c.description}</p><button className="primary" disabled={busy} onClick={()=>completeChallenge(c.id)}>Complete challenge</button></section>)}</div>}
   {tab==="education"&&<div className="cards">{education.map(e=><section className="card" key={e.metric_key}><h2>{e.title}</h2><p><b>What:</b> {e.what}</p><p><b>Why:</b> {e.why}</p><p><b>How:</b> {e.how}</p><p><b>Influences:</b> {e.influences}</p><div className="notice">{e.limitations}</div><p><b>When to seek advice:</b> {e.when_advice}</p></section>)}</div>}
  </main>
 </div>
}
