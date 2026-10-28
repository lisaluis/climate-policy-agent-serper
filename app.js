// Replace this with the actual Render URL after deploying the backend.
const API_BASE_URL = "https://YOUR-RENDER-SERVICE.onrender.com";
const form=document.getElementById("ask-form"), questionInput=document.getElementById("question");
const locationInput=document.getElementById("location"), submitButton=document.getElementById("submit");
const statusBox=document.getElementById("status"), resultsSection=document.getElementById("results");
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function renderRecommendations(items){
 const box=document.getElementById("recommendations");box.replaceChildren();
 items.forEach(x=>{const c=el("article","rec-card"),p=el("div","pills");p.append(el("span","pill","Priority: "+x.priority));
 c.append(p,el("h3","",x.title),el("p","",x.action),el("p","","Responsible stakeholders: "+x.stakeholders),el("p","source-meta","Rationale / caution: "+x.rationale));box.append(c);});
}
function renderEvidence(items){
 const box=document.getElementById("evidence");box.replaceChildren();
 items.forEach((x,i)=>{const c=el("article","evidence-card");c.append(el("div","eyebrow","SOURCE "+(i+1)));
 const a=el("a","",x.title);a.href=x.url;a.target="_blank";a.rel="noopener noreferrer";c.append(a);
 c.append(el("p","",x.snippet||"No search snippet supplied."),el("p","source-meta","Domain: "+x.source+" · "+x.source_quality_hint+(x.date?" · Date shown by search: "+x.date:"")));box.append(c);});
}
form.addEventListener("submit",async e=>{
 e.preventDefault();const question=questionInput.value.trim();
 if(question.length<5){statusBox.textContent="Please enter a more specific question.";return;}
 if(API_BASE_URL.includes("YOUR-RENDER-SERVICE")){statusBox.textContent="Deploy the backend, then set API_BASE_URL in app.js to your Render URL.";return;}
 submitButton.disabled=true;statusBox.textContent="Searching sources and preparing recommendations…";resultsSection.hidden=true;
 try{
  const response=await fetch(API_BASE_URL+"/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({question,location:locationInput.value,max_results:8})});
  const data=await response.json();if(!response.ok)throw new Error(data.detail||"Request failed ("+response.status+")");
  renderRecommendations(data.recommendations||[]);renderEvidence(data.evidence||[]);
  const list=document.getElementById("limitations");list.replaceChildren();(data.limitations||[]).forEach(t=>list.append(el("li","",t)));
  document.getElementById("method").textContent="Method: "+data.method+". Search query: "+data.search_query;
  resultsSection.hidden=false;statusBox.textContent="Found "+data.evidence.length+" source(s). Review them before relying on recommendations.";
 }catch(err){statusBox.textContent="Could not complete the request: "+err.message;}
 finally{submitButton.disabled=false;}
});
