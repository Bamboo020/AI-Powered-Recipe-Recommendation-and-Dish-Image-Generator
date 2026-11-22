import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';
import PhotoUpload from './PhotoUpload';
import IngredientPhotos from './IngredientPhotos';
import MealPlanner from './MealPlanner';

const names = {egg:'Egg',tomato:'Tomato',cooked_rice:'Cooked rice',raw_rice:'Uncooked rice',rice_unspecified:'Rice (cooking state unspecified)',oil:'Oil',salt:'Salt',scallion:'Scallion',soy_sauce:'Soy sauce',tofu:'Tofu',garlic:'Garlic',noodles:'Noodles',potato:'Potato',onion:'Onion',chicken:'Chicken',olive_oil:'Olive oil'};
const dishNames = {fried_rice:'Fried rice',omelette:'Omelette',pizza:'Pizza',ramen:'Ramen',dumplings:'Dumplings'};
const label = x => names[x] || x.replaceAll('_', ' ');
const split = value => value.split(/[,，、\n]+/).map(x=>x.trim()).filter(Boolean);
async function api(path, body) {
  const response = await fetch('/api/'+path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let data;
  try { data = await response.json(); } catch { throw new Error('The kitchen is temporarily unavailable. Please try again shortly.'); }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your ingredients and enter a cooking time between 1 and 1,440 minutes.');
  return data;
}
function App() {
  const [ingredients,setIngredients]=useState('egg, tomato, cooked rice');
  const [minutes,setMinutes]=useState(30), [cuisine,setCuisine]=useState('chinese_home_style');
  const [excluded,setExcluded]=useState(''), [servings,setServings]=useState(1);
  const [results,setResults]=useState(null), [selected,setSelected]=useState(null);
  const [busy,setBusy]=useState(false), [error,setError]=useState('');
  const [explanation,setExplanation]=useState(''), [detailBusy,setDetailBusy]=useState(false);
  const [imageError,setImageError]=useState('');
  const [image,setImage]=useState(null), [imageJob,setImageJob]=useState(null);
  const [dataset,setDataset]=useState('real'), [dishCategory,setDishCategory]=useState('');
  const [photo,setPhoto]=useState(null), [predictions,setPredictions]=useState([]);
  const [photoError,setPhotoError]=useState(''), [photoBusy,setPhotoBusy]=useState(false);
  const [datasetNotice,setDatasetNotice]=useState('Every recipe keeps its original source, so you can explore it with confidence.');
  useEffect(()=>()=>{if(photo) URL.revokeObjectURL(photo);},[photo]);
  async function classify(file) {
    if(!file) return;
    setPredictions([]);setPhotoError('');
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setPhotoError('Please choose a JPG, PNG, or WebP photo.');return;}
    if(file.size>5*1024*1024){setPhotoError('Please choose an image smaller than 5 MB.');return;}
    setPhoto(URL.createObjectURL(file));setPhotoBusy(true);
    try {
      const response=await fetch('/api/classify-food',{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file});
      const data=await response.json();
      if(!response.ok) throw new Error(data.detail||'We could not recognize this photo. Please try another.');
      setPredictions(data.predictions);
      if(data.low_confidence) setPhotoError('This match is uncertain. Please confirm the dish or try another photo.');
    } catch(e){setPhotoError(e.message);} finally{setPhotoBusy(false);}
  }
  function validatePreferences() {
    if(!Number.isInteger(Number(minutes)) || Number(minutes)<1 || Number(minutes)>1440){setError('Enter a cooking time between 1 and 1,440 minutes.');return false;}
    if(!Number.isInteger(Number(servings)) || Number(servings)<1 || Number(servings)>20){setError('Choose between 1 and 20 people at the table.');return false;}
    return true;
  }
  async function searchByPhoto(category) {
    if(!validatePreferences()) return;
    setDishCategory(category);setDataset('real');setBusy(true);setError('');setSelected(null);setImage(null);setImageJob(null);setExplanation('');
    try {const data=await api('recommend',{ingredients:split(ingredients),dish_category:category,dataset:'real',max_cooking_time:Number(minutes),excluded_ingredients:split(excluded),cuisine:'any',servings:Number(servings),top_k:3});setResults(data.recommendations);setDatasetNotice('Recipes follow the dish category you confirmed. Photos do not reveal a complete ingredient list.');}
    catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function search(event) {
    event.preventDefault();
    if(!validatePreferences()) return;
    if(!split(ingredients).length&&!dishCategory){setError('Add an ingredient or choose a dish category to get started.');return;}
    setBusy(true);setError('');setSelected(null);setExplanation('');setImageError('');setImage(null);setImageJob(null);
    try {const data=await api('recommend',{ingredients:split(ingredients),max_cooking_time:Number(minutes),cuisine,servings:Number(servings),excluded_ingredients:split(excluded),top_k:3,dataset,dish_category:dishCategory||null});setResults(data.recommendations);setDatasetNotice(dataset==='real'?'Original Food.com recipes with source links and steps. Ingredient names and quantities may need checking.':'This selection includes clearly labeled project examples. Check each recipe’s source.');}
    catch(e){setError(e.message);} finally{setBusy(false);}
  }
  async function confirmedIngredients(values) {
    if(!validatePreferences()) return;
    setIngredients(values.join(', '));setDishCategory('');setDataset('real');setBusy(true);setError('');setSelected(null);setImage(null);setImageJob(null);setExplanation('');
    try {const data=await api('recommend',{ingredients:values,max_cooking_time:Number(minutes),excluded_ingredients:split(excluded),cuisine:'any',servings:Number(servings),top_k:3,dataset:'real',meal_only:true});setResults(data.recommendations);setDatasetNotice('Meal suggestions exclude obvious desserts, drinks, standalone sauces and single-ingredient records. Recipes use the ingredients you confirmed from your photos and corrections. Recognition suggestions can be incomplete.');}
    catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function explain() {
    setDetailBusy(true);setExplanation('');
    try {const data=await api('explain',{recipe_id:selected.recipe_id});setExplanation((data.is_llm_generated ? 'AI-generated notes — please check the original recipe: ' : 'Recipe notes: ') + data.text);} catch(e){setExplanation(e.message);} finally{setDetailBusy(false);}
  }
  async function generate() {
    setDetailBusy(true);setImageError('');setImage(null);setImageJob(null);
    try {
      let response=await fetch('/api/image-jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({recipe_id:selected.recipe_id})});
      let job=await response.json();
      if(!response.ok)throw Error(job.detail||'Image generation is unavailable.');
      setImageJob(job);
      for(let attempt=0;attempt<180;attempt+=1){
        if(job.status==='completed'){setImage(job.result);return;}
        if(job.status==='failed'||job.status==='cancelled')throw Error(job.error||`Image job ${job.status}.`);
        await new Promise(resolve=>setTimeout(resolve,1000));
        response=await fetch('/api/image-jobs/'+job.job_id);
        job=await response.json();
        if(!response.ok)throw Error(job.detail||'Could not check the image job.');
        setImageJob(job);
      }
      throw Error('Image generation is still running. Check again later.');
    } catch(e){setImageError(e.message);} finally{setDetailBusy(false);}
  }
  async function cancelImageJob(){
    if(!imageJob?.job_id)return;
    try{const response=await fetch('/api/image-jobs/'+imageJob.job_id,{method:'DELETE'});const data=await response.json();if(!response.ok)throw Error(data.detail||'Could not cancel the image job.');setImageJob(data);}
    catch(e){setImageError(e.message);}
  }
  return <><header><a className="brand" href="/" aria-label="Pantry Studio home"><span className="brand-mark" aria-hidden="true">♧</span><span>Pantry Studio<small>YOUR EVERYDAY KITCHEN</small></span></a><span className="edition">A little comfort, one meal at a time <span aria-hidden="true">♡</span></span></header>
    <main><section className="hero"><div><p className="eyebrow">A LITTLE PANTRY, A LOT OF LOVE.</p><h1>Simple ingredients.<br/>A little <span className="warm-word">everyday joy.</span></h1><p className="intro">Good food starts with what you have.<br/>Tell us what’s in your fridge. Let’s make something lovely.</p><div className="tags"><a href="#boston-events-heading">Need a meal? Find free food nearby ↓</a><span>✦ Make the most of your pantry</span><span>♡ Make a little time for yourself</span></div></div><aside className="hero-art" aria-label="A warm kitchen illustration with a bowl of rice and fresh ingredients"><div className="steam" aria-hidden="true"><i/><i/><i/></div><div className="plate" aria-hidden="true"><span>🍅</span><span>🍚</span><span>🌿</span></div><span className="art-note note-one">A little freshness</span><span className="art-note note-two">Made with care ♡</span><p>Life gets busy.<br/>There’s always time for a little comfort.</p><small>MADE WITH A LITTLE LOVE</small></aside></section>
    <IngredientPhotos onConfirm={confirmedIngredients} disabled={busy||photoBusy}/>
    <section className="photo-section"><div className="photo-heading"><p className="eyebrow">A PHOTO, A LITTLE INSPIRATION</p><h2>Found a dish you love?<br/> Bring the inspiration home.</h2><p>A little inspiration from a photo.<br/> A lovely reason to start cooking.</p><span className="supported-label">FIVE DISHES WE KNOW FOR NOW</span><div className="dish-chips">{Object.values(dishNames).map(name=><span key={name}>{name}</span>)}</div></div><div className="photo-upload-panel"><PhotoUpload photo={photo} busy={photoBusy} disabled={photoBusy||busy} onFile={classify} onClear={()=>{setPhoto(null);setPredictions([]);setPhotoError('');}}/>{photoError&&<p className="error" role="alert">{photoError}</p>}{predictions.length>0&&<><p className="prediction-heading">Which dish looks right? You decide.</p><div className="prediction-list">{predictions.map(p=><button key={p.label} type="button" disabled={busy||photoBusy} onClick={()=>searchByPhoto(p.label)}><span>{dishNames[p.label]||p.label}</span><small>{(p.confidence*100).toFixed(1)}%</small><span aria-hidden="true">→</span></button>)}</div></>}<p className="photo-disclaimer">Recognition supports these five dishes only. Other foods may receive an incorrect label. Please confirm or correct the match; a photo cannot identify every ingredient.</p></div></section>
    <MealPlanner ingredients={ingredients} excluded={excluded}/>
    <section className="workspace"><form onSubmit={search} noValidate><div className="section-top"><span className="eyebrow">WHAT’S IN YOUR KITCHEN</span><span>01 / 03</span></div><h2>What’s in your kitchen?</h2><label htmlFor="dataset">Recipe collection</label><select id="dataset" value={dataset} onChange={e=>setDataset(e.target.value)}><option value="real">Original Food.com recipes</option><option value="demo">Project examples</option><option value="all">All recipes (sources labeled)</option></select><label htmlFor="category">Dish category (you can change it)</label><select id="category" value={dishCategory} onChange={e=>setDishCategory(e.target.value)}><option value="">Any dish</option>{Object.entries(dishNames).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select><label htmlFor="ingredients">Ingredients you have</label><textarea id="ingredients" value={ingredients} onChange={e=>setIngredients(e.target.value)} required={!dishCategory} maxLength={2000}/><p className="hint">Separate ingredients with commas. Cooked and uncooked rice are matched separately.</p><div className="fields"><div><label htmlFor="minutes">Time available · minutes</label><input id="minutes" type="number" min="1" max="1440" required value={minutes} onChange={e=>setMinutes(e.target.value)}/></div><div><label htmlFor="servings">People at the table</label><input id="servings" type="number" min="1" max="20" required value={servings} onChange={e=>setServings(e.target.value)}/></div></div><label htmlFor="cuisine">Your favorite flavors</label><select id="cuisine" value={cuisine} onChange={e=>setCuisine(e.target.value)}><option value="chinese_home_style">Chinese home-style</option><option value="italian">Italian</option><option value="any">Any cuisine</option></select><label htmlFor="excluded">Ingredients to leave out</label><input id="excluded" placeholder="For example: peanuts, egg" value={excluded} onChange={e=>setExcluded(e.target.value)}/><button className="primary" disabled={busy}>{busy?'Finding something lovely…':'Let’s find something delicious →'}</button>{error&&<p role="alert" className="error">{error}</p>}<p className="hint">Exclusions match listed ingredients only and cannot guarantee allergy safety.</p></form>
    <div className="results" id="recipe-ideas" aria-live="polite"><div className="section-top"><span className="eyebrow">SOMETHING GOOD IS COOKING</span><span>{results ? results.length+' recipe ideas':'Ready when you are'}</span></div><h2>A little inspiration for your table</h2>{results===null?<div className="empty"><span>✳</span><h3>Make an ordinary day a little delicious</h3><p>Tell us what you have on hand.<br/>We’ll find a few recipes that fit your day.</p></div>:results.length===0?<div className="empty"><h3>Nothing on the menu just yet</h3><p>Try adding ingredients, allowing more time, or adjusting your exclusions.</p></div>:results.map((recipe,index)=><button type="button" className={'recipe '+(selected?.recipe_id===recipe.recipe_id?'active':'')} key={recipe.recipe_id} onClick={()=>{setSelected(recipe);setExplanation('');setImageError('');setImage(null);setImageJob(null);}}><span className="recipe-index">0{index+1}</span><div><div className="recipe-meta">{recipe.total_minutes} MIN <span>·</span> Original yield: {recipe.servings ?? "not specified"} servings</div><h3>{recipe.title}</h3><p>On hand: {recipe.available_ingredients.map(label).join(', ')||'No ingredients provided or matched'}</p><p className="missing">Still needed: {recipe.missing_ingredients.map(label).join(', ')||'You have everything listed'}</p><small>{recipe.recipe_id.startsWith("foodcom-")?"Food.com original":"Project examples"} · ingredient match {Math.round(recipe.match_factors.ingredient_match*100)}% · score {recipe.final_score.toFixed(2)}</small></div><span>↗</span></button>)}<div className="notice">{datasetNotice} Please check the ingredients and original instructions before cooking.</div></div></section>
    {selected&&<section className="detail"><div className="section-top"><span className="eyebrow">FROM PANTRY TO PLATE</span><span>Recipe details</span></div><h2>{selected.title}</h2><p className="hint">Source: {selected.source} · Original yield: {selected.servings ?? "not specified"} servings · Your table:  {servings}  people. Quantities have not been rescaled.</p>{selected.source_url&&<a href={selected.source_url} target="_blank" rel="noreferrer">Visit the original Food.com recipe ↗</a>}<div className="detail-grid"><div><h3>What you’ll need</h3><ul>{selected.ingredient_items.map((item,index)=><li key={index}>{label(item.name)} <span>{item.quantity} {item.unit}</span></li>)}</ul><p className="hint">Match factors: {Object.entries(selected.match_factors).map(([key,value])=>`${key}: ${value.toFixed(2)}`).join(" · ")}. These initial weights have not been validated.</p></div><div><h3>Let’s get cooking</h3><ol>{selected.steps.map((step,i)=><li key={i}>{step}</li>)}</ol><div className="actions"><button disabled={detailBusy} onClick={explain}>A few recipe notes</button><button disabled={detailBusy} onClick={generate}>Imagine this dish</button>{imageJob?.status==='queued'&&<button onClick={cancelImageJob}>Cancel queued image</button>}</div>{imageJob&&['queued','running'].includes(imageJob.status)&&<p className="hint" aria-live="polite">Image job: {imageJob.status}. {imageJob.status==='running'?'Running local generation cannot be interrupted safely.':'You can cancel while it is waiting.'}</p>}{explanation&&<p className="notice">{explanation}</p>}{image&&<figure><img src={image.url} alt="AI-generated dish concept" style={{maxWidth:"100%"}}/><figcaption>AI-generated concept · {image.model}</figcaption></figure>}{imageError&&<p role="alert" className="error">{imageError}</p>}</div></div></section>}
    <footer><span>Pantry Studio <span aria-hidden="true">♡</span> A little taste of home, in every meal.</span><span>PANTRY STUDIO · TAKE YOUR TIME. EAT WELL.</span></footer></main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
