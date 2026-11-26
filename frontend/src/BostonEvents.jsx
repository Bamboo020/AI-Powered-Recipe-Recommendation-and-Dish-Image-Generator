import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
const categories={all:'All free food options',meal:'Prepared meals',groceries:'Groceries to cook',fridge:'Community fridges',event:'Events with free food'};
const bostonDate=date=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);
const eventTime=value=>new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(new Date(value));
function EventsMap({events,selected,onSelect}){
  const node=useRef(null),map=useRef(null),markers=useRef(new Map());
  const [tileError,setTileError]=useState(false);
  useEffect(()=>{
    const instance=L.map(node.current,{scrollWheelZoom:false}).setView([42.355,-71.065],12);map.current=instance;
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(instance);
    tiles.on('tileerror',()=>setTileError(true));
    const observer=new ResizeObserver(()=>instance.invalidateSize());observer.observe(node.current);
    return()=>{observer.disconnect();instance.remove();map.current=null;};
  },[]);
  useEffect(()=>{
    if(!map.current)return;
    const layer=L.layerGroup().addTo(map.current);markers.current.clear();
    const groups=new Map();
    events.filter(e=>e.coordinates).forEach(e=>{const key=e.coordinates.latitude+','+e.coordinates.longitude;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);});
    const points=[];
    let index=0;
    groups.forEach(group=>{
      index+=1;const first=group[0],point=[first.coordinates.latitude,first.coordinates.longitude];points.push(point);
      const content=document.createElement('div');
      const heading=document.createElement('strong');heading.textContent=first.address;content.append(heading);
      group.forEach(event=>{const button=document.createElement('button');button.type='button';button.className='event-popup-button';button.textContent=event.title;button.addEventListener('click',()=>onSelect(event.id));content.append(button);});
      const marker=L.marker(point,{title:`${group.length} event${group.length>1?'s':''} at ${first.address}`,icon:L.divIcon({className:'event-map-pin',html:`<span>${index}${group.length>1?`<small>+${group.length-1}</small>`:''}</span>`,iconSize:[36,36],iconAnchor:[18,36]})}).bindPopup(content).addTo(layer);
      marker.on('click',()=>onSelect(first.id));group.forEach(event=>markers.current.set(event.id,marker));
    });
    if(points.length)map.current.fitBounds(L.latLngBounds(points),{padding:[35,35],maxZoom:14,animate:false});
    return()=>{layer.remove();markers.current.clear();};
  },[events,onSelect]);
  useEffect(()=>{const marker=markers.current.get(selected);if(marker&&map.current){map.current.panTo(marker.getLatLng(),{animate:false});marker.openPopup();}},[selected,events]);
  return <div className="events-map-wrap"><div ref={node} className="events-map" role="region" aria-label="Map of Boston free food locations"/>{tileError&&<p className="error" role="status">Some map tiles could not load. The event list and source links are still available.</p>}</div>;
}
export default function BostonEvents({goals=[]}){
  const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [range,setRange]=useState('7'),[category,setCategory]=useState('all'),[query,setQuery]=useState('');
  const [online,setOnline]=useState(false),[cancelled,setCancelled]=useState(false),[selected,setSelected]=useState(null);
  const [clock,setClock]=useState(Date.now()),inFlight=useRef(false);
  const selectEvent=useCallback(id=>setSelected(id),[]);
  const load=useCallback(async(force=false)=>{
    if(inFlight.current)return;inFlight.current=true;setBusy(true);setError('');
    try{const response=await fetch('/api/food-resources/boston'+(force?'?refresh=true':''));const payload=await response.json();if(!response.ok)throw Error(payload.detail||'Free food resources are temporarily unavailable.');setData(payload);setClock(Date.now());}
    catch(e){setError(e.message);}finally{inFlight.current=false;setBusy(false);}
  },[]);
  useEffect(()=>{load();const timer=setInterval(()=>{if(document.visibilityState==='visible')load();},300000);return()=>clearInterval(timer);},[load]);
  const events=useMemo(()=>{
    if(!data)return[];
    const today=bostonDate(new Date(clock));
    const last=range==='today'?today:bostonDate(new Date(clock+(Number(range)-1)*86400000));
    return data.events.filter(e=>{const date=bostonDate(new Date(e.start_at));const notEnded=e.end_at?Date.parse(e.end_at)>clock:date>=today;return notEnded&&date>=today&&date<=last&&(online||!e.virtual)&&(cancelled||!e.cancelled)&&(category==='all'||(category==='meal'?e.full_meal===true:e.category===category))&&(!query||`${e.title} ${e.address} ${e.department}`.toLowerCase().includes(query.toLowerCase()));});
  },[data,range,category,query,online,cancelled,clock]);
  const selectedEvent=events.find(e=>e.id===selected),pins=events.filter(e=>e.coordinates).length;
  return <section className="boston-events" aria-labelledby="boston-events-heading"><div className="events-heading"><div><p className="eyebrow">A GOOD MEAL SHOULD FEEL WITHIN REACH</p><h2 id="boston-events-heading">Not cooking? Find free food in Boston.</h2><p>Find a prepared meal, groceries to cook, or an event that explicitly offers free food.</p></div><span className="live-badge"><i/>{data?'Provider sources checked':'Free food resources · no API key'}</span></div>
    <div className="events-toolbar"><div><label htmlFor="event-range">When</label><select id="event-range" value={range} onChange={e=>setRange(e.target.value)}><option value="today">Today</option><option value="7">Next 7 days</option><option value="30">Next 30 days</option></select></div><div><label htmlFor="event-category">What food do you need?</label><select id="event-category" value={category} onChange={e=>setCategory(e.target.value)}>{Object.entries(categories).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></div><div><label htmlFor="event-query">Search food resources</label><input id="event-query" placeholder="Meals, groceries, a neighborhood…" value={query} onChange={e=>setQuery(e.target.value)}/></div><button className="events-refresh" disabled={busy} onClick={()=>load(true)}>{busy?'Updating…':'Refresh food resources ↻'}</button></div>
    <div className="events-toggles"><label><input type="checkbox" checked={online} onChange={e=>setOnline(e.target.checked)}/> Include online events</label><label><input type="checkbox" checked={cancelled} onChange={e=>setCancelled(e.target.checked)}/> Include cancelled listings</label></div>
    <p className="notice">Prepared meals are ready to eat. Grocery pickups need cooking facilities. Community fridge contents vary and may not provide a full meal. No live stock or calorie information is available.</p>
    {error&&<p role="alert" className="error">{data?'Refresh failed; the previous listings below may be out of date. ':''}{error}</p>}{data?.warning&&<p className="error" role="status">{data.warning}</p>}
    {data&&<p className="events-freshness">{events.length} food options · {pins} with map locations · Last fetched {eventTime(data.fetched_at)} · {data.status==='stale'?'Source needs checking':data.status==='cached'?'Recent cached snapshot':'Source check completed'} · Refreshes every 5 minutes while this page is visible</p>}
    <div className="events-layout"><div><EventsMap events={events} selected={selected} onSelect={selectEvent}/><p className="hint">Pins are approximate public street-address matches from the U.S. Census Geocoder. Online and unlocated events remain in the list. Map tiles: OpenStreetMap.</p>{selectedEvent&&<div className="event-selected"><p className="eyebrow">YOUR SELECTED FOOD OPTION</p><h3>{selectedEvent.title}</h3><p>{selectedEvent.schedule_note}</p><p>{selectedEvent.food_offer}</p><p><strong>Access:</strong> {selectedEvent.eligibility}</p><p>{selectedEvent.address}</p>{selectedEvent.coordinates&&<p className="hint">Matched address: {selectedEvent.coordinates.matched_address}</p>}<a href={selectedEvent.source_url} target="_blank" rel="noreferrer">Check the provider’s current details ↗</a></div>}</div>
    <div className="events-list" aria-live="polite">{!data&&!error&&<p className="notice">Checking free food provider sources…</p>}{data&&!events.length&&<div className="empty"><h3>A little more room to explore</h3><p>No food options in this source snapshot. Try a different date range or category.</p></div>}{events.map(e=><article key={e.id} className={'event-card '+(selected===e.id?'selected':'')}><div className="event-card-top"><span>{categories[e.category]}</span>{e.cancelled&&<strong>Cancelled</strong>}</div><h3><button onClick={()=>selectEvent(e.id)}>{e.title}</button></h3><p className="event-clock">{e.resource_type==='fridge'?'24/7 access published · stock unknown':'Next published service: '+eventTime(e.start_at)}</p><p>{e.food_offer}</p><p><span className="food-type">{e.full_meal===true?'Prepared meal described':e.full_meal===false?'Ingredients or snacks; full meal not promised':'Full meal availability unknown'}</span></p><p><strong>Access:</strong> {e.eligibility}</p><p className="hint">{e.schedule_note}</p><p className="hint resource-check">{e.source_status==='needs_recheck'?'Source details could not be rechecked. Contact provider before travel.':'Source checked '+eventTime(e.source_checked_at)+' · not a live stock check'}</p>{e.evidence&&<p className="hint resource-evidence">Organizer evidence: {e.evidence}</p>}<p>{e.address}</p><p className="hint">{e.virtual?'Online event':e.coordinates?'Approximate location on map':'Location could not be confirmed on map'}{!e.end_at?' · End time not supplied':''}</p><a href={e.source_url} target="_blank" rel="noreferrer">Provider details ↗</a></article>)}</div></div>
    <div className="events-source"><p><strong>Only food explicitly described as free is included.</strong> {data?.free_food_event_count===0?'No one-off city events in the current feed explicitly promise free food. Regular programs below are separate provider listings.':''}</p><p>{data?.coverage_note} {data?.freshness_note}</p><p className="hint">Program schedules are manually reviewed source summaries (reviewed November 17, 2026), with periodic checks for matching source details. A successful page check is not proof the program is serving right now. Exact menus, quantities, calories and dietary suitability remain unknown.</p>{(data?.directories||[]).map(d=><p key={d.url}><a href={d.url} target="_blank" rel="noreferrer">{d.title} ↗</a></p>)}</div>

  </section>;
}
