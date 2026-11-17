import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

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
  const [datasetNotice,setDatasetNotice]=useState('真实数据模式使用 Food.com 食谱，演示样例单独标注。');
  useEffect(()=>()=>{if(photo) URL.revokeObjectURL(photo);},[photo]);
  async function classify(event) {
    const file=event.target.files?.[0];setPredictions([]);setPhotoError('');
    if(!file) return;
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
  return <><header><a className="brand" href="/">✳ <span>Pantry Studio</span></a><span className="edition">CSYE 7380 / PROJECT LAB</span></header>
    <main><section className="hero"><div><p className="eyebrow">LESS WASTE. MORE POSSIBILITY.</p><h1>冰箱里有什么，<br/>今晚就做点什么。</h1><p className="intro">从手边的食材出发，发现下一道家常美味。<br/>查看搭配、补齐食材，把灵感变成一餐。</p><div className="tags"><span>01 食材匹配</span><span>02 食谱推荐</span><span>03 菜品灵感</span></div></div><aside className="hero-art" aria-label="厨房食材插画"><div className="plate"><span>🍅</span><span>🥚</span><span>🌿</span></div><p>GOOD FOOD STARTS<br/>WITH WHAT YOU HAVE.</p><small>THE EVERYDAY KITCHEN / 001</small></aside></section>
    <section className="photo-section"><div><p className="eyebrow">PHOTO TO RECIPE</p><h2>拍下这道菜，找找怎么做</h2><p className="hint">五类实验模型：炒饭、煎蛋、披萨、拉面、饺子。其他菜品也会被强制分入这五类，不能据此判断已识别成功。请核对 Top-3 并手动确认；概率未经校准。</p><label htmlFor="photo">上传菜品图片（JPEG / PNG / WebP，最大 5 MB）</label><input id="photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={classify} disabled={photoBusy||busy}/>{photoBusy&&<p role="status">CNN 正在分析图片…</p>}{photoError&&<p className="error" role="alert">{photoError}</p>}<div className="prediction-list">{predictions.map(p=><button key={p.label} type="button" disabled={busy||photoBusy} onClick={()=>searchByPhoto(p.label)}>确认 {dishNames[p.label]||p.label} · {(p.confidence*100).toFixed(1)}% → 检索</button>)}</div></div>{photo&&<img className="photo-preview" src={photo} alt="已上传的菜品"/>}</section>
    <section className="workspace"><form onSubmit={search}><div className="section-top"><span className="eyebrow">YOUR PANTRY</span><span>01 / 03</span></div><h2>今天，用这些做饭</h2><label htmlFor="dataset">食谱数据</label><select id="dataset" value={dataset} onChange={e=>setDataset(e.target.value)}><option value="real">真实 Food.com 食谱</option><option value="demo">项目演示样例</option><option value="all">全部（来源分别标注）</option></select><label htmlFor="category">菜品类别（可手动纠正）</label><select id="category" value={dishCategory} onChange={e=>setDishCategory(e.target.value)}><option value="">不限类别</option>{Object.entries(dishNames).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select><label htmlFor="ingredients">已有食材</label><textarea id="ingredients" value={ingredients} onChange={e=>setIngredients(e.target.value)} required={!dishCategory} maxLength={2000}/><p className="hint">用逗号分隔；熟米饭与生米会分别匹配。</p><div className="fields"><div><label htmlFor="minutes">最多用时 · 分钟</label><input id="minutes" type="number" min="1" max="1440" required value={minutes} onChange={e=>setMinutes(e.target.value)}/></div><div><label htmlFor="servings">用餐人数</label><input id="servings" type="number" min="1" max="20" required value={servings} onChange={e=>setServings(e.target.value)}/></div></div><label htmlFor="cuisine">想吃的风味</label><select id="cuisine" value={cuisine} onChange={e=>setCuisine(e.target.value)}><option value="chinese_home_style">中式家常</option><option value="italian">意式风味</option><option value="any">不限菜系</option></select><label htmlFor="excluded">不想放的食材</label><input id="excluded" placeholder="例如：花生，鸡蛋" value={excluded} onChange={e=>setExcluded(e.target.value)}/><button className="primary" disabled={busy}>{busy?'正在寻找搭配…':'寻找我的晚餐 →'}</button>{error&&<p role="alert" className="error">{error}</p>}<p className="hint">仅匹配明确列出的食材，不能保证过敏安全。</p></form>
    <div className="results" aria-live="polite"><div className="section-top"><span className="eyebrow">THE MENU</span><span>{results ? results.length+' 道灵感':'等待你的食材'}</span></div><h2>一餐的可能性</h2>{results===null?<div className="empty"><span>✳</span><h3>好好吃饭，从这里开始</h3><p>输入食材，查看最多三道符合时间的食谱。<br/>每道菜都会列出已有和待补齐的食材。</p></div>:results.length===0?<div className="empty"><h3>暂时没有合适的搭配</h3><p>试试增加食材、放宽烹饪时间，或调整忌口。</p></div>:results.map((recipe,index)=><button type="button" className={'recipe '+(selected?.recipe_id===recipe.recipe_id?'active':'')} key={recipe.recipe_id} onClick={()=>{setSelected(recipe);setExplanation('');setImageError('');setImage(null);}}><span className="recipe-index">0{index+1}</span><div><div className="recipe-meta">{recipe.total_minutes} MIN <span>·</span> 原食谱 {recipe.servings ?? "未注明"} 人份</div><h3>{recipe.title}</h3><p>已有：{recipe.available_ingredients.map(label).join('、')||'未提供或未匹配'}</p><p className="missing">需补齐：{recipe.missing_ingredients.map(label).join('、')||'食材齐全'}</p><small>{recipe.recipe_id.startsWith("foodcom-")?"Food.com 真实记录":"项目演示样例"} · 食材覆盖 {Math.round(recipe.match_factors.ingredient_match*100)}% · 综合分 {recipe.final_score.toFixed(2)}</small></div><span>↗</span></button>)}<div className="notice">{datasetNotice} 规则过滤后最多重排 128 条候选。来源记录不代表已独立审核。</div></div></section>
    {selected&&<section className="detail"><div className="section-top"><span className="eyebrow">FROM PANTRY TO PLATE</span><span>食谱详情</span></div><h2>{selected.title}</h2><p className="hint">来源：{selected.source} · 原食谱 {selected.servings ?? "未注明"} 人份；当前选择 {servings} 人，数量暂未自动换算。</p>{selected.source_url&&<a href={selected.source_url} target="_blank" rel="noreferrer">查看 Food.com 原始来源 ↗</a>}<div className="detail-grid"><div><h3>食材清单</h3><ul>{selected.ingredient_items.map((item,index)=><li key={index}>{label(item.name)} <span>{item.quantity} {item.unit}</span></li>)}</ul><p className="hint">排序因素：{Object.entries(selected.match_factors).map(([key,value])=>`${key}: ${value.toFixed(2)}`).join(" · ")}。初始权重未经实验验证。</p></div><div><h3>烹饪步骤</h3><ol>{selected.steps.map((step,i)=><li key={i}>{step}</li>)}</ol><div className="actions"><button disabled={detailBusy} onClick={explain}>查看说明</button><button disabled={detailBusy} onClick={generate}>生成菜品概念图</button></div>{explanation&&<p className="notice">{explanation}</p>}{image&&<figure><img src={image.url} alt="AI 生成菜品概念图" style={{maxWidth:"100%"}}/><figcaption>AI 生成概念图 · {image.model}</figcaption></figure>}{imageError&&<p role="alert" className="error">{imageError}</p>}</div></div></section>}
    <footer><span>Pantry Studio — An everyday cooking experiment.</span><span>Made for the ingredients you already have.</span></footer></main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
