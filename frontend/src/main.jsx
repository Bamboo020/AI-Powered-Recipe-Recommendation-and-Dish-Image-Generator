import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';
import PhotoUpload from './PhotoUpload';

const names = {egg:'鸡蛋',tomato:'番茄',cooked_rice:'熟米饭',raw_rice:'生米',rice_unspecified:'米（生熟未注明）',oil:'油',salt:'盐',scallion:'葱',soy_sauce:'酱油',tofu:'豆腐',garlic:'大蒜',noodles:'面条',potato:'土豆',onion:'洋葱',chicken:'鸡肉',olive_oil:'橄榄油'};
const dishNames = {fried_rice:'炒饭',omelette:'煎蛋 / 蛋饼',pizza:'披萨',ramen:'拉面',dumplings:'饺子'};
const label = x => names[x] || x;
const split = value => value.split(/[,，、\n]+/).map(x=>x.trim()).filter(Boolean);
async function api(path, body) {
  const response = await fetch('/api/'+path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let data;
  try { data = await response.json(); } catch { throw new Error('服务暂时不可用，请确认后端已启动后重试。'); }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请检查输入：食材不能为空，时间应为 1–1440 分钟。');
  return data;
}
function App() {
  const [ingredients,setIngredients]=useState('鸡蛋，番茄，熟米饭');
  const [minutes,setMinutes]=useState(30), [cuisine,setCuisine]=useState('chinese_home_style');
  const [excluded,setExcluded]=useState(''), [servings,setServings]=useState(1);
  const [results,setResults]=useState(null), [selected,setSelected]=useState(null);
  const [busy,setBusy]=useState(false), [error,setError]=useState('');
  const [explanation,setExplanation]=useState(''), [detailBusy,setDetailBusy]=useState(false);
  const [imageError,setImageError]=useState('');
  const [image,setImage]=useState(null);
  const [dataset,setDataset]=useState('real'), [dishCategory,setDishCategory]=useState('');
  const [photo,setPhoto]=useState(null), [predictions,setPredictions]=useState([]);
  const [photoError,setPhotoError]=useState(''), [photoBusy,setPhotoBusy]=useState(false);
  const [datasetNotice,setDatasetNotice]=useState('每道食谱保留原始来源，让这一餐更有依据。');
  useEffect(()=>()=>{if(photo) URL.revokeObjectURL(photo);},[photo]);
  async function classify(file) {
    if(!file) return;
    setPredictions([]);setPhotoError('');
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setPhotoError('这张图片暂时打不开，请换一张 JPG、PNG 或 WebP 照片。');return;}
    if(file.size>5*1024*1024){setPhotoError('请选择小于 5 MB 的图片。');return;}
    setPhoto(URL.createObjectURL(file));setPhotoBusy(true);
    try {
      const response=await fetch('/api/classify-food',{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file});
      const data=await response.json();
      if(!response.ok) throw new Error(data.detail||'识别失败');
      setPredictions(data.predictions);
      if(data.low_confidence) setPhotoError('模型把握较低，请确认类别或换一张图片。');
    } catch(e){setPhotoError(e.message);} finally{setPhotoBusy(false);}
  }
  async function searchByPhoto(category) {
    setDishCategory(category);setDataset('real');setBusy(true);setError('');setSelected(null);setImage(null);setExplanation('');
    try {const data=await api('recommend',{ingredients:split(ingredients),dish_category:category,dataset:'real',max_cooking_time:Number(minutes),excluded_ingredients:split(excluded),cuisine:'any',servings:Number(servings),top_k:3});setResults(data.recommendations);setDatasetNotice('图片类别由用户确认；相关食谱按标题关键词映射。照片不用于推断食材。');}
    catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function search(event) {
    event.preventDefault();setBusy(true);setError('');setSelected(null);setExplanation('');setImageError('');setImage(null);
    try {const data=await api('recommend',{ingredients:split(ingredients),max_cooking_time:Number(minutes),cuisine,servings:Number(servings),excluded_ingredients:split(excluded),top_k:3,dataset,dish_category:dishCategory||null});setResults(data.recommendations);setDatasetNotice(dataset==='real'?'真实 Food.com 数据；来源与原始步骤保留。食材别名和单位解析仍有限。':'包含单独标记的项目演示样例，请核对来源。');}
    catch(e){setError(e.message);} finally{setBusy(false);}
  }
  async function explain() {
    setDetailBusy(true);setExplanation('');
    try {const data=await api('explain',{recipe_id:selected.recipe_id});setExplanation((data.is_llm_generated ? 'LLM 生成说明（请核对原食谱）：' : '模板说明：') + data.text);} catch(e){setExplanation(e.message);} finally{setDetailBusy(false);}
  }
  async function generate() {
    setDetailBusy(true);setImageError('');
    try {const data=await api('generate-image',{recipe_id:selected.recipe_id});setImage(data);} catch(e){setImageError(e.message);} finally{setDetailBusy(false);}
  }
  return <><header><a className="brand" href="/" aria-label="暖暖小厨房首页"><span className="brand-mark" aria-hidden="true">♧</span><span>暖暖小厨房<small>PANTRY STUDIO</small></span></a><span className="edition">一屋烟火，一餐温暖 <span aria-hidden="true">♡</span></span></header>
    <main><section className="hero"><div><p className="eyebrow">A LITTLE PANTRY, A LOT OF LOVE.</p><h1>把手边的食材，<br/>做成一餐<span className="warm-word">小幸福。</span></h1><p className="intro">不必准备很多，也能好好吃饭。<br/>告诉我冰箱里有什么，今晚的菜单，我们一起想。</p><div className="tags"><span>✦ 用好手边食材</span><span>♡ 留一点时间给生活</span></div></div><aside className="hero-art" aria-label="厨房食材插画"><div className="steam" aria-hidden="true"><i/><i/><i/></div><div className="plate" aria-hidden="true"><span>🍅</span><span>🍚</span><span>🌿</span></div><span className="art-note note-one">一点新鲜</span><span className="art-note note-two">满满心意 ♡</span><p>生活有点忙，<br/>也要记得好好吃饭。</p><small>MADE WITH A LITTLE LOVE</small></aside></section>
    <section className="photo-section"><div className="photo-heading"><p className="eyebrow">A PHOTO, A LITTLE INSPIRATION</p><h2>遇到喜欢的菜，<br/>把灵感带回家。</h2><p>一张照片，也可以成为<br/>今天下厨的开始。</p><span className="supported-label">现在认识这 5 种美味</span><div className="dish-chips">{Object.values(dishNames).map(name=><span key={name}>{name}</span>)}</div></div><div className="photo-upload-panel"><PhotoUpload photo={photo} busy={photoBusy} disabled={photoBusy||busy} onFile={classify} onClear={()=>{setPhoto(null);setPredictions([]);setPhotoError('');}}/>{photoError&&<p className="error" role="alert">{photoError}</p>}{predictions.length>0&&<><p className="prediction-heading">看起来像哪一道？由你来确认。</p><div className="prediction-list">{predictions.map(p=><button key={p.label} type="button" disabled={busy||photoBusy} onClick={()=>searchByPhoto(p.label)}><span>{dishNames[p.label]||p.label}</span><small>{(p.confidence*100).toFixed(1)}%</small><span aria-hidden="true">→</span></button>)}</div></>}<p className="photo-disclaimer">目前仅支持以上五类，其他菜品也可能被归入其中。请确认或纠正结果；照片不会用于推断完整食材。</p></div></section>
    <section className="workspace"><form onSubmit={search}><div className="section-top"><span className="eyebrow">WHAT’S IN YOUR KITCHEN</span><span>01 / 03</span></div><h2>今天，厨房里有什么？</h2><label htmlFor="dataset">食谱数据</label><select id="dataset" value={dataset} onChange={e=>setDataset(e.target.value)}><option value="real">真实 Food.com 食谱</option><option value="demo">项目演示样例</option><option value="all">全部（来源分别标注）</option></select><label htmlFor="category">菜品类别（可手动纠正）</label><select id="category" value={dishCategory} onChange={e=>setDishCategory(e.target.value)}><option value="">不限类别</option>{Object.entries(dishNames).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select><label htmlFor="ingredients">已有食材</label><textarea id="ingredients" value={ingredients} onChange={e=>setIngredients(e.target.value)} required={!dishCategory} maxLength={2000}/><p className="hint">用逗号分隔；熟米饭与生米会分别匹配。</p><div className="fields"><div><label htmlFor="minutes">最多用时 · 分钟</label><input id="minutes" type="number" min="1" max="1440" required value={minutes} onChange={e=>setMinutes(e.target.value)}/></div><div><label htmlFor="servings">用餐人数</label><input id="servings" type="number" min="1" max="20" required value={servings} onChange={e=>setServings(e.target.value)}/></div></div><label htmlFor="cuisine">想吃的风味</label><select id="cuisine" value={cuisine} onChange={e=>setCuisine(e.target.value)}><option value="chinese_home_style">中式家常</option><option value="italian">意式风味</option><option value="any">不限菜系</option></select><label htmlFor="excluded">不想放的食材</label><input id="excluded" placeholder="例如：花生，鸡蛋" value={excluded} onChange={e=>setExcluded(e.target.value)}/><button className="primary" disabled={busy}>{busy?'正在寻找搭配…':'一起想想今晚吃什么 →'}</button>{error&&<p role="alert" className="error">{error}</p>}<p className="hint">仅匹配明确列出的食材，不能保证过敏安全。</p></form>
    <div className="results" aria-live="polite"><div className="section-top"><span className="eyebrow">SOMETHING GOOD IS COOKING</span><span>{results ? results.length+' 道灵感':'等待你的食材'}</span></div><h2>为你留好的餐桌灵感</h2>{results===null?<div className="empty"><span>✳</span><h3>把寻常日子，过得有滋有味</h3><p>把手边的食材告诉我。<br/>我会帮你找几道，刚好适合今天的菜。</p></div>:results.length===0?<div className="empty"><h3>暂时没有合适的搭配</h3><p>试试增加食材、放宽烹饪时间，或调整忌口。</p></div>:results.map((recipe,index)=><button type="button" className={'recipe '+(selected?.recipe_id===recipe.recipe_id?'active':'')} key={recipe.recipe_id} onClick={()=>{setSelected(recipe);setExplanation('');setImageError('');setImage(null);}}><span className="recipe-index">0{index+1}</span><div><div className="recipe-meta">{recipe.total_minutes} MIN <span>·</span> 原食谱 {recipe.servings ?? "未注明"} 人份</div><h3>{recipe.title}</h3><p>已有：{recipe.available_ingredients.map(label).join('、')||'未提供或未匹配'}</p><p className="missing">需补齐：{recipe.missing_ingredients.map(label).join('、')||'食材齐全'}</p><small>{recipe.recipe_id.startsWith("foodcom-")?"Food.com 真实记录":"项目演示样例"} · 食材覆盖 {Math.round(recipe.match_factors.ingredient_match*100)}% · 综合分 {recipe.final_score.toFixed(2)}</small></div><span>↗</span></button>)}<div className="notice">{datasetNotice} 食谱供日常烹饪参考，请核对食材和原始步骤。</div></div></section>
    {selected&&<section className="detail"><div className="section-top"><span className="eyebrow">FROM PANTRY TO PLATE</span><span>食谱详情</span></div><h2>{selected.title}</h2><p className="hint">来源：{selected.source} · 原食谱 {selected.servings ?? "未注明"} 人份；当前选择 {servings} 人，数量暂未自动换算。</p>{selected.source_url&&<a href={selected.source_url} target="_blank" rel="noreferrer">查看 Food.com 原始来源 ↗</a>}<div className="detail-grid"><div><h3>食材清单</h3><ul>{selected.ingredient_items.map((item,index)=><li key={index}>{label(item.name)} <span>{item.quantity} {item.unit}</span></li>)}</ul><p className="hint">排序因素：{Object.entries(selected.match_factors).map(([key,value])=>`${key}: ${value.toFixed(2)}`).join(" · ")}。初始权重未经实验验证。</p></div><div><h3>烹饪步骤</h3><ol>{selected.steps.map((step,i)=><li key={i}>{step}</li>)}</ol><div className="actions"><button disabled={detailBusy} onClick={explain}>查看说明</button><button disabled={detailBusy} onClick={generate}>生成菜品概念图</button></div>{explanation&&<p className="notice">{explanation}</p>}{image&&<figure><img src={image.url} alt="AI 生成菜品概念图" style={{maxWidth:"100%"}}/><figcaption>AI 生成概念图 · {image.model}</figcaption></figure>}{imageError&&<p role="alert" className="error">{imageError}</p>}</div></div></section>}
    <footer><span>暖暖小厨房 <span aria-hidden="true">♡</span> 愿每一餐，都有家的温度。</span><span>PANTRY STUDIO · 慢慢做，好好吃。</span></footer></main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
