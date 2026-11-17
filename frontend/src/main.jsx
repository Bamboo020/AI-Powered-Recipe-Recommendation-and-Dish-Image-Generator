import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

const names = {egg:'鸡蛋',tomato:'番茄',cooked_rice:'熟米饭',raw_rice:'生米',oil:'油',salt:'盐',scallion:'葱',soy_sauce:'酱油',tofu:'豆腐',garlic:'大蒜',noodles:'面条',potato:'土豆',onion:'洋葱',chicken:'鸡肉',olive_oil:'橄榄油'};
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
  async function search(event) {
    event.preventDefault();setBusy(true);setError('');setSelected(null);setExplanation('');setImageError('');setImage(null);
    try {const data=await api('recommend',{ingredients:split(ingredients),max_cooking_time:Number(minutes),cuisine,servings:Number(servings),excluded_ingredients:split(excluded),top_k:3});setResults(data.recommendations);}
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
    <section className="workspace"><form onSubmit={search}><div className="section-top"><span className="eyebrow">YOUR PANTRY</span><span>01 / 03</span></div><h2>今天，用这些做饭</h2><label htmlFor="ingredients">已有食材</label><textarea id="ingredients" value={ingredients} onChange={e=>setIngredients(e.target.value)} required maxLength={2000}/><p className="hint">用逗号分隔；熟米饭与生米会分别匹配。</p><div className="fields"><div><label htmlFor="minutes">最多用时 · 分钟</label><input id="minutes" type="number" min="1" max="1440" required value={minutes} onChange={e=>setMinutes(e.target.value)}/></div><div><label htmlFor="servings">用餐人数</label><input id="servings" type="number" min="1" max="20" required value={servings} onChange={e=>setServings(e.target.value)}/></div></div><label htmlFor="cuisine">想吃的风味</label><select id="cuisine" value={cuisine} onChange={e=>setCuisine(e.target.value)}><option value="chinese_home_style">中式家常</option><option value="italian">意式风味</option><option value="any">不限菜系</option></select><label htmlFor="excluded">不想放的食材</label><input id="excluded" placeholder="例如：花生，鸡蛋" value={excluded} onChange={e=>setExcluded(e.target.value)}/><button className="primary" disabled={busy}>{busy?'正在寻找搭配…':'寻找我的晚餐 →'}</button>{error&&<p role="alert" className="error">{error}</p>}<p className="hint">仅匹配明确列出的食材，不能保证过敏安全。</p></form>
    <div className="results" aria-live="polite"><div className="section-top"><span className="eyebrow">THE MENU</span><span>{results ? results.length+' 道灵感':'等待你的食材'}</span></div><h2>一餐的可能性</h2>{results===null?<div className="empty"><span>✳</span><h3>好好吃饭，从这里开始</h3><p>输入食材，查看最多三道符合时间的食谱。<br/>每道菜都会列出已有和待补齐的食材。</p></div>:results.length===0?<div className="empty"><h3>暂时没有合适的搭配</h3><p>试试增加食材、放宽烹饪时间，或调整忌口。</p></div>:results.map((recipe,index)=><button type="button" className={'recipe '+(selected?.recipe_id===recipe.recipe_id?'active':'')} key={recipe.recipe_id} onClick={()=>{setSelected(recipe);setExplanation('');setImageError('');setImage(null);}}><span className="recipe-index">0{index+1}</span><div><div className="recipe-meta">{recipe.total_minutes} MIN <span>·</span> 原食谱 {recipe.servings} 人份</div><h3>{recipe.title}</h3><p>已有：{recipe.available_ingredients.map(label).join('、')}</p><p className="missing">需补齐：{recipe.missing_ingredients.map(label).join('、')||'食材齐全'}</p><small>食材覆盖 {Math.round(recipe.match_factors.ingredient_match*100)}% · 综合分 {recipe.final_score.toFixed(2)}</small></div><span>↗</span></button>)}<div className="notice">项目演示数据 · 排序按可用模型选择语义混合或规则模式。示例食谱尚未经人工审核，不是 Food.com 导入记录。AI 模块需由服务端配置后启用。</div></div></section>
    {selected&&<section className="detail"><div className="section-top"><span className="eyebrow">FROM PANTRY TO PLATE</span><span>食谱详情</span></div><h2>{selected.title}</h2><p className="hint">来源：{selected.source} · 原食谱 {selected.servings} 人份；当前选择 {servings} 人，数量暂未自动换算。</p><div className="detail-grid"><div><h3>食材清单</h3><ul>{selected.ingredient_items.map(item=><li key={item.name}>{label(item.name)} <span>{item.quantity} {item.unit}</span></li>)}</ul><p className="hint">排序因素：{Object.entries(selected.match_factors).map(([key,value])=>`${key}: ${value.toFixed(2)}`).join(" · ")}。初始权重未经实验验证。</p></div><div><h3>烹饪步骤</h3><ol>{selected.steps.map((step,i)=><li key={i}>{step}</li>)}</ol><div className="actions"><button disabled={detailBusy} onClick={explain}>查看说明</button><button disabled={detailBusy} onClick={generate}>生成菜品概念图</button></div>{explanation&&<p className="notice">{explanation}</p>}{image&&<figure><img src={image.url} alt="AI 生成菜品概念图" style={{maxWidth:"100%"}}/><figcaption>AI 生成概念图 · {image.model}</figcaption></figure>}{imageError&&<p role="alert" className="error">{imageError}</p>}</div></div></section>}
    <footer><span>Pantry Studio — An everyday cooking experiment.</span><span>Made for the ingredients you already have.</span></footer></main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
