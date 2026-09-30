// Exercise repeated job transitions without touching contacts or a browser.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const elements=new Map();
function element(){return {textContent:'',style:{},value:'',children:[],append(...x){this.children.push(...x)},replaceChildren(){this.children=[]},setAttribute(){}}}
const catalog={contacts:[{key:'example',name:'Example',fullName:'Example',candidates:[]}]};
const complete={status:'complete',message:'Saved and verified'};
const context=vm.createContext({document:{querySelector(s){if(!elements.has(s))elements.set(s,element());return elements.get(s)},createElement:element,createTextNode:t=>t},fetch:async url=>({ok:true,json:async()=>url==='/data.json'?catalog:url==='/apply-status'?complete:url==='/refresh-status'?{status:'idle'}:{}}),setInterval(){},setTimeout,console});
const html=fs.readFileSync(path.join(__dirname,'../photo-review/public/index.html'),'utf8');
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
(async()=>{
 await new Promise(setImmediate);
 const button=elements.get('#review-changes');
 assert.equal(button.disabled,false);
 for(let i=0;i<2;i++){
  vm.runInContext("applyState({status:'running',message:'Saving'})",context);
  assert.equal(button.disabled,true);
  await vm.runInContext('checkApply()',context);
  assert.equal(button.disabled,false,'Identical completion responses must release each new job');
 }
 vm.runInContext("sourceState({status:'running'})",context);assert.equal(button.disabled,true);
 vm.runInContext("sourceState({status:'failed',message:'Refresh failed'})",context);assert.equal(button.disabled,false);
 assert.equal(button.textContent,'Review changes for this contact');
 console.log('PASS: repeated update completion and failed refresh restore the review button');
})().catch(e=>{console.error(e);process.exitCode=1});
