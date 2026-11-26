import React, {useRef, useState} from 'react';

export function UploadIcon(){return <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="4"/><circle cx="8" cy="9" r="1.5"/><path d="m4 16 5-4 4 3 3-5 5 6"/></svg>;}

export default function PhotoUpload({photo, busy, disabled=busy, onFile, onClear}){
  const input=useRef(null), depth=useRef(0);
  const [dragging,setDragging]=useState(false);
  const accept=(file)=>{if(file&&!disabled) onFile(file);};
  return <div className={'upload-zone '+(dragging?'is-dragging ':'')+(photo?'has-photo':'')}
    tabIndex={0} role="region" aria-label="Food photo upload area. Drop or paste an image here." aria-busy={busy}
    onDragEnter={e=>{e.preventDefault();depth.current++;if(!disabled)setDragging(true);}}
    onDragOver={e=>{e.preventDefault();e.dataTransfer.dropEffect=disabled?'none':'copy';}}
    onDragLeave={e=>{e.preventDefault();depth.current--;if(depth.current<=0){depth.current=0;setDragging(false);}}}
    onDrop={e=>{e.preventDefault();depth.current=0;setDragging(false);accept(e.dataTransfer.files?.[0]);}}
    onPaste={e=>{const file=[...e.clipboardData.items].find(item=>item.kind==='file'&&item.type.startsWith('image/'))?.getAsFile();if(file){e.preventDefault();accept(file);}}}>
    <input ref={input} type="file" hidden tabIndex={-1} aria-label="Photo file" accept="image/jpeg,image/png,image/webp" disabled={disabled} onChange={e=>{accept(e.target.files?.[0]);e.target.value='';}}/>
    {photo?<div className="upload-preview"><img src={photo} alt="Your uploaded dish photo"/><span className="preview-label">A little table inspiration</span></div>:<span className="upload-icon"><UploadIcon/></span>}
    <div className="upload-copy"><strong>{busy?'Taking a closer look…':dragging?'Drop it here, nice and easy':photo?'A little inspiration for dinner':'Drop a little inspiration here'}</strong><p>{photo?'Confirm the dish below, then let’s find a recipe.':'Drag a photo here, or paste one from your clipboard'}</p><div className="upload-actions"><button type="button" className="upload-button" disabled={disabled} onClick={()=>input.current?.click()}>{photo?'Choose another photo':'Choose a food photo'}<span aria-hidden="true"> ↗</span></button>{photo&&<button className="text-button" type="button" disabled={disabled} onClick={onClear}>Remove</button>}</div><small>JPG, PNG, WebP · Up to 5 MB</small></div>
    {busy&&<span className="upload-progress" role="status">Recognizing your dish. One little moment…</span>}
  </div>;
}
