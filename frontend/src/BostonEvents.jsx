import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
const categories={all:'All activities',movement:'Movement & outdoors',food:'Food & gardening',culture:'Arts & culture',community:'Community & learning'};
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
  return <div className="events-map-wrap"><div ref={node} className="events-map" role="region" aria-label="Map of Boston event locations"/>{tileError&&<p className="error" role="status">Some map tiles could not load. The event list and source links are still available.</p>}</div>;
}
export default function BostonEvents({goals=[]}){
  const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [range,setRange]=useState('7'),[category,setCategory]=useState('all'),[query,setQuery]=useState('');
  const [online,setOnline]=useState(false),[cancelled,setCancelled]=useState(false),[selected,setSelected]=useState(null);
  const [clock,setClock]=useState(Date.now()),inFlight=useRef(false);
  const selectEvent=useCallback(id=>setSelected(id),[]);
  const load=useCallback(async(force=false)=>{
    if(inFlight.current)return;inFlight.current=true;setBusy(true);setError('');
    try{const response=await fetch('/api/events/boston'+(force?'?refresh=true':''));const payload=await response.json();if(!response.ok)throw Error(payload.detail||'Boston events are temporarily unavailable.');setData(payload);setClock(Date.now());}
    catch(e){setError(e.message);}finally{inFlight.current=false;setBusy(false);}
  },[]);
  useEffect(()=>{load();const timer=setInterval(()=>{if(document.visibilityState==='visible')load();},300000);return()=>clearInterval(timer);},[load]);
  const events=useMemo(()=>{
    if(!data)return[];
    const today=bostonDate(new Date(clock));
    const last=range==='today'?today:bostonDate(new Date(clock+(Number(range)-1)*86400000));
    return data.events.filter(e=>{const date=bostonDate(new Date(e.start_at));const notEnded=e.end_at?Date.parse(e.end_at)>clock:date>=today;return notEnded&&date>=today&&date<=last&&(online||!e.virtual)&&(cancelled||!e.cancelled)&&(category==='all'||e.category===category)&&(!query||`${e.title} ${e.address} ${e.department}`.toLowerCase().includes(query.toLowerCase()));});
  },[data,range,category,query,online,cancelled,clock]);
  const selectedEvent=events.find(e=>e.id===selected),pins=events.filter(e=>e.coordinates).length;
  return <section className="boston-events" aria-labelledby="boston-events-heading"><div className="events-heading"><div><p className="eyebrow">A LITTLE LIFE BEYOND THE KITCHEN</p><h2 id="boston-events-heading">Make a little room for Boston.</h2><p>Find a workshop, a community gathering, or a little inspiration nearby.</p></div><span className="live-badge"><i/>{data?'Connected to Boston.gov':'Public events · no API key'}</span></div>
    <div className="events-toolbar"><div><label htmlFor="event-range">When</label><select id="event-range" value={range} onChange={e=>setRange(e.target.value)}><option value="today">Today</option><option value="7">Next 7 days</option><option value="30">Next 30 days</option></select></div><div><label htmlFor="event-category">Your kind of activity</label><select id="event-category" value={category} onChange={e=>setCategory(e.target.value)}>{Object.entries(categories).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></div><div><label htmlFor="event-query">Search the listings</label><input id="event-query" placeholder="Art, bikes, a neighborhood…" value={query} onChange={e=>setQuery(e.target.value)}/></div><button className="events-refresh" disabled={busy} onClick={()=>load(true)}>{busy?'Updating…':'Refresh activities ↻'}</button></div>
    <div className="events-toggles"><label><input type="checkbox" checked={online} onChange={e=>setOnline(e.target.checked)}/> Include online events</label><label><input type="checkbox" checked={cancelled} onChange={e=>setCancelled(e.target.checked)}/> Include cancelled listings</label></div>
    {(goals.includes('strength')||goals.includes('endurance'))&&<p className="hint">For an active day, try the Movement & outdoors filter. A workshop or meetup is not a personalized workout prescription.</p>}
    {error&&<p role="alert" className="error">{data?'Refresh failed; the previous listings below may be out of date. ':''}{error}</p>}{data?.warning&&<p className="error" role="status">{data.warning}</p>}
    {data&&<p className="events-freshness">{events.length} matching activities · {pins} with map locations · Last fetched {eventTime(data.fetched_at)} · {data.status==='stale'?'Older snapshot':data.status==='cached'?'Recent cached snapshot':'Source updated'} · Refreshes every 5 minutes while this page is visible</p>}
    <div className="events-layout"><div><EventsMap events={events} selected={selected} onSelect={selectEvent}/><p className="hint">Pins are approximate public street-address matches from the U.S. Census Geocoder. Online and unlocated events remain in the list. Map tiles: OpenStreetMap.</p>{selectedEvent&&<div className="event-selected"><p className="eyebrow">YOUR SELECTED ACTIVITY</p><h3>{selectedEvent.title}</h3><p>{eventTime(selectedEvent.start_at)}{selectedEvent.end_at?' – '+eventTime(selectedEvent.end_at):' · End time not supplied'}</p><p>{selectedEvent.address}</p>{selectedEvent.coordinates&&<p className="hint">Matched address: {selectedEvent.coordinates.matched_address}</p>}<a href={selectedEvent.source_url} target="_blank" rel="noreferrer">Check details & registration at Boston.gov ↗</a></div>}</div>
    <div className="events-list" aria-live="polite">{!data&&!error&&<p className="notice">Connecting to the official Boston events feed…</p>}{data&&!events.length&&<div className="empty"><h3>A little more room to explore</h3><p>No matching activities in this source snapshot. Try a different date range or category.</p></div>}{events.map(e=><article key={e.id} className={'event-card '+(selected===e.id?'selected':'')}><div className="event-card-top"><span>{categories[e.category]}</span>{e.cancelled&&<strong>Cancelled</strong>}</div><h3><button onClick={()=>selectEvent(e.id)}>{e.title}</button></h3><p className="event-clock">{eventTime(e.start_at)}</p><p>{e.address}</p><p className="hint">{e.virtual?'Online event':e.coordinates?'Approximate location on map':'Location could not be confirmed on map'}{!e.end_at?' · End time not supplied':''}</p><a href={e.source_url} target="_blank" rel="noreferrer">Organizer details ↗</a></article>)}</div></div>
    <div className="events-source"><p><strong>Source:</strong> <a href="https://www.boston.gov/events" target="_blank" rel="noreferrer">City of Boston official calendar ↗</a> · <a href="https://www.boston.gov/rss/events" target="_blank" rel="noreferrer">RSS feed ↗</a></p><p>{data?.coverage_note||'City-published events only; this is not a complete Boston events directory.'} {data?.freshness_note||'Source updates may be delayed. Confirm details with the organizer before leaving.'}</p><p className="hint">Categories use title and department keywords. Times use the source’s visible local clock in America/New_York; its machine-readable UTC values can disagree. Prices and ticket availability are not supplied by this integration.</p></div>
  </section>;
}
