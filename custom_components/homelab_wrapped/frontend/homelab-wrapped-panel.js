var V=globalThis,q=V.ShadowRoot&&(V.ShadyCSS===void 0||V.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ie=Symbol(),ke=new WeakMap,H=class{constructor(t,r,s){if(this._$cssResult$=!0,s!==ie)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=r}get styleSheet(){let t=this.o,r=this.t;if(q&&t===void 0){let s=r!==void 0&&r.length===1;s&&(t=ke.get(r)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&ke.set(r,t))}return t}toString(){return this.cssText}},we=e=>new H(typeof e=="string"?e:e+"",void 0,ie),L=(e,...t)=>{let r=e.length===1?e[0]:t.reduce((s,i,n)=>s+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[n+1],e[0]);return new H(r,e,ie)},xe=(e,t)=>{if(q)e.adoptedStyleSheets=t.map(r=>r instanceof CSSStyleSheet?r:r.styleSheet);else for(let r of t){let s=document.createElement("style"),i=V.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=r.cssText,e.appendChild(s)}},ne=q?e=>e:e=>e instanceof CSSStyleSheet?(t=>{let r="";for(let s of t.cssRules)r+=s.cssText;return we(r)})(e):e;var{is:pt,defineProperty:ct,getOwnPropertyDescriptor:ut,getOwnPropertyNames:ht,getOwnPropertySymbols:mt,getPrototypeOf:gt}=Object,G=globalThis,Se=G.trustedTypes,bt=Se?Se.emptyScript:"",ft=G.reactiveElementPolyfillSupport,O=(e,t)=>e,ae={toAttribute(e,t){switch(t){case Boolean:e=e?bt:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let r=e;switch(t){case Boolean:r=e!==null;break;case Number:r=e===null?null:Number(e);break;case Object:case Array:try{r=JSON.parse(e)}catch{r=null}}return r}},Ae=(e,t)=>!pt(e,t),Te={attribute:!0,type:String,converter:ae,reflect:!1,useDefault:!1,hasChanged:Ae};Symbol.metadata??=Symbol("metadata"),G.litPropertyMetadata??=new WeakMap;var x=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,r=Te){if(r.state&&(r.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((r=Object.create(r)).wrapped=!0),this.elementProperties.set(t,r),!r.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,r);i!==void 0&&ct(this.prototype,t,i)}}static getPropertyDescriptor(t,r,s){let{get:i,set:n}=ut(this.prototype,t)??{get(){return this[r]},set(a){this[r]=a}};return{get:i,set(a){let d=i?.call(this);n?.call(this,a),this.requestUpdate(t,d,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Te}static _$Ei(){if(this.hasOwnProperty(O("elementProperties")))return;let t=gt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(O("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(O("properties"))){let r=this.properties,s=[...ht(r),...mt(r)];for(let i of s)this.createProperty(i,r[i])}let t=this[Symbol.metadata];if(t!==null){let r=litPropertyMetadata.get(t);if(r!==void 0)for(let[s,i]of r)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[r,s]of this.elementProperties){let i=this._$Eu(r,s);i!==void 0&&this._$Eh.set(i,r)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let r=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)r.unshift(ne(i))}else t!==void 0&&r.push(ne(t));return r}static _$Eu(t,r){let s=r.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,r=this.constructor.elementProperties;for(let s of r.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return xe(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,r,s){this._$AK(t,s)}_$ET(t,r){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let n=(s.converter?.toAttribute!==void 0?s.converter:ae).toAttribute(r,s.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,r){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let n=s.getPropertyOptions(i),a=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:ae;this._$Em=i;let d=a.fromAttribute(r,n.type);this[i]=d??this._$Ej?.get(i)??d,this._$Em=null}}requestUpdate(t,r,s,i=!1,n){if(t!==void 0){let a=this.constructor;if(i===!1&&(n=this[t]),s??=a.getPropertyOptions(t),!((s.hasChanged??Ae)(n,r)||s.useDefault&&s.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,s))))return;this.C(t,r,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,r,{useDefault:s,reflect:i,wrapped:n},a){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??r??this[t]),n!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(r=void 0),this._$AL.set(t,r)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(r){Promise.reject(r)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,n]of s){let{wrapped:a}=n,d=this[i];a!==!0||this._$AL.has(i)||d===void 0||this.C(i,void 0,n,d)}}let t=!1,r=this._$AL;try{t=this.shouldUpdate(r),t?(this.willUpdate(r),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(r)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(r)}willUpdate(t){}_$AE(t){this._$EO?.forEach(r=>r.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(r=>this._$ET(r,this[r])),this._$EM()}updated(t){}firstUpdated(t){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[O("elementProperties")]=new Map,x[O("finalized")]=new Map,ft?.({ReactiveElement:x}),(G.reactiveElementVersions??=[]).push("2.1.2");var le=globalThis,Ce=e=>e,X=le.trustedTypes,Ee=X?X.createPolicy("lit-html",{createHTML:e=>e}):void 0,de="$lit$",S=`lit$${Math.random().toFixed(9).slice(2)}$`,pe="?"+S,yt=`<${pe}>`,R=document,W=()=>R.createComment(""),F=e=>e===null||typeof e!="object"&&typeof e!="function",ce=Array.isArray,Ue=e=>ce(e)||typeof e?.[Symbol.iterator]=="function",oe=`[ 	
\f\r]`,I=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Re=/-->/g,Pe=/>/g,C=RegExp(`>|${oe}(?:([^\\s"'>=/]+)(${oe}*=${oe}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),De=/'/g,Ne=/"/g,He=/^(?:script|style|textarea|title)$/i,ue=e=>(t,...r)=>({_$litType$:e,strings:t,values:r}),l=ue(1),er=ue(2),tr=ue(3),P=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),Me=new WeakMap,E=R.createTreeWalker(R,129);function Le(e,t){if(!ce(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return Ee!==void 0?Ee.createHTML(t):t}var Oe=(e,t)=>{let r=e.length-1,s=[],i,n=t===2?"<svg>":t===3?"<math>":"",a=I;for(let d=0;d<r;d++){let c=e[d],u,h,m=-1,$=0;for(;$<c.length&&(a.lastIndex=$,h=a.exec(c),h!==null);)$=a.lastIndex,a===I?h[1]==="!--"?a=Re:h[1]!==void 0?a=Pe:h[2]!==void 0?(He.test(h[2])&&(i=RegExp("</"+h[2],"g")),a=C):h[3]!==void 0&&(a=C):a===C?h[0]===">"?(a=i??I,m=-1):h[1]===void 0?m=-2:(m=a.lastIndex-h[2].length,u=h[1],a=h[3]===void 0?C:h[3]==='"'?Ne:De):a===Ne||a===De?a=C:a===Re||a===Pe?a=I:(a=C,i=void 0);let T=a===C&&e[d+1].startsWith("/>")?" ":"";n+=a===I?c+yt:m>=0?(s.push(u),c.slice(0,m)+de+c.slice(m)+S+T):c+S+(m===-2?d:T)}return[Le(e,n+(e[r]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},K=class e{constructor({strings:t,_$litType$:r},s){let i;this.parts=[];let n=0,a=0,d=t.length-1,c=this.parts,[u,h]=Oe(t,r);if(this.el=e.createElement(u,s),E.currentNode=this.el.content,r===2||r===3){let m=this.el.content.firstChild;m.replaceWith(...m.childNodes)}for(;(i=E.nextNode())!==null&&c.length<d;){if(i.nodeType===1){if(i.hasAttributes())for(let m of i.getAttributeNames())if(m.endsWith(de)){let $=h[a++],T=i.getAttribute(m).split(S),Y=/([.?@])?(.*)/.exec($);c.push({type:1,index:n,name:Y[2],strings:T,ctor:Y[1]==="."?Z:Y[1]==="?"?Q:Y[1]==="@"?ee:N}),i.removeAttribute(m)}else m.startsWith(S)&&(c.push({type:6,index:n}),i.removeAttribute(m));if(He.test(i.tagName)){let m=i.textContent.split(S),$=m.length-1;if($>0){i.textContent=X?X.emptyScript:"";for(let T=0;T<$;T++)i.append(m[T],W()),E.nextNode(),c.push({type:2,index:++n});i.append(m[$],W())}}}else if(i.nodeType===8)if(i.data===pe)c.push({type:2,index:n});else{let m=-1;for(;(m=i.data.indexOf(S,m+1))!==-1;)c.push({type:7,index:n}),m+=S.length-1}n++}}static createElement(t,r){let s=R.createElement("template");return s.innerHTML=t,s}};function D(e,t,r=e,s){if(t===P)return t;let i=s!==void 0?r._$Co?.[s]:r._$Cl,n=F(t)?void 0:t._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(e),i._$AT(e,r,s)),s!==void 0?(r._$Co??=[])[s]=i:r._$Cl=i),i!==void 0&&(t=D(e,i._$AS(e,t.values),i,s)),t}var J=class{constructor(t,r){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=r}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:r},parts:s}=this._$AD,i=(t?.creationScope??R).importNode(r,!0);E.currentNode=i;let n=E.nextNode(),a=0,d=0,c=s[0];for(;c!==void 0;){if(a===c.index){let u;c.type===2?u=new M(n,n.nextSibling,this,t):c.type===1?u=new c.ctor(n,c.name,c.strings,this,t):c.type===6&&(u=new te(n,this,t)),this._$AV.push(u),c=s[++d]}a!==c?.index&&(n=E.nextNode(),a++)}return E.currentNode=R,i}p(t){let r=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,r),r+=s.strings.length-2):s._$AI(t[r])),r++}},M=class e{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,r,s,i){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=t,this._$AB=r,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,r=this._$AM;return r!==void 0&&t?.nodeType===11&&(t=r.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,r=this){t=D(this,t,r),F(t)?t===p||t==null||t===""?(this._$AH!==p&&this._$AR(),this._$AH=p):t!==this._$AH&&t!==P&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ue(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==p&&F(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){let{values:r,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=K.createElement(Le(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(r);else{let n=new J(i,this),a=n.u(this.options);n.p(r),this.T(a),this._$AH=n}}_$AC(t){let r=Me.get(t.strings);return r===void 0&&Me.set(t.strings,r=new K(t)),r}k(t){ce(this._$AH)||(this._$AH=[],this._$AR());let r=this._$AH,s,i=0;for(let n of t)i===r.length?r.push(s=new e(this.O(W()),this.O(W()),this,this.options)):s=r[i],s._$AI(n),i++;i<r.length&&(this._$AR(s&&s._$AB.nextSibling,i),r.length=i)}_$AR(t=this._$AA.nextSibling,r){for(this._$AP?.(!1,!0,r);t!==this._$AB;){let s=Ce(t).nextSibling;Ce(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},N=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,r,s,i,n){this.type=1,this._$AH=p,this._$AN=void 0,this.element=t,this.name=r,this._$AM=i,this.options=n,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=p}_$AI(t,r=this,s,i){let n=this.strings,a=!1;if(n===void 0)t=D(this,t,r,0),a=!F(t)||t!==this._$AH&&t!==P,a&&(this._$AH=t);else{let d=t,c,u;for(t=n[0],c=0;c<n.length-1;c++)u=D(this,d[s+c],r,c),u===P&&(u=this._$AH[c]),a||=!F(u)||u!==this._$AH[c],u===p?t=p:t!==p&&(t+=(u??"")+n[c+1]),this._$AH[c]=u}a&&!i&&this.j(t)}j(t){t===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Z=class extends N{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===p?void 0:t}},Q=class extends N{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==p)}},ee=class extends N{constructor(t,r,s,i,n){super(t,r,s,i,n),this.type=5}_$AI(t,r=this){if((t=D(this,t,r,0)??p)===P)return;let s=this._$AH,i=t===p&&s!==p||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,n=t!==p&&(s===p||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},te=class{constructor(t,r,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=r,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){D(this,t)}},Ie={M:de,P:S,A:pe,C:1,L:Oe,R:J,D:Ue,V:D,I:M,H:N,N:Q,U:ee,B:Z,F:te},$t=le.litHtmlPolyfillSupport;$t?.(K,M),(le.litHtmlVersions??=[]).push("3.3.3");var We=(e,t,r)=>{let s=r?.renderBefore??t,i=s._$litPart$;if(i===void 0){let n=r?.renderBefore??null;s._$litPart$=i=new M(t.insertBefore(W(),n),n,void 0,r??{})}return i._$AI(e),i};var he=globalThis,_=class extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let r=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=We(r,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return P}};_._$litElement$=!0,_.finalized=!0,he.litElementHydrateSupport?.({LitElement:_});var vt=he.litElementPolyfillSupport;vt?.({LitElement:_});(he.litElementVersions??=[]).push("4.2.2");var Fe=e=>(...t)=>({_$litDirective$:e,values:t}),re=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,r,s){this._$Ct=t,this._$AM=r,this._$Ci=s}_$AS(t,r){return this.update(t,r)}update(t,r){return this.render(...r)}};var{I:br}=Ie;var _t={},Ke=(e,t=_t)=>e._$AH=t;var Be=Fe(class extends re{constructor(){super(...arguments),this.key=p}render(e,t){return this.key=e,t}update(e,[t,r]){return t!==this.key&&(Ke(e),this.key=t),r}});var U=class{constructor(t){this.language=t}number(t,r=0){return new Intl.NumberFormat(this.language,{maximumFractionDigits:r}).format(t)}amount(t){return this.number(t,t<10?1:0)}money(t,r,s=0){try{return new Intl.NumberFormat(this.language,{style:"currency",currency:r,maximumFractionDigits:s,minimumFractionDigits:s}).format(t)}catch{return`${this.number(t,s)} ${r}`}}percent(t,r=0){return new Intl.NumberFormat(this.language,{style:"percent",maximumFractionDigits:r}).format(t/100)}big(t){return t<1e6?this.number(t):new Intl.NumberFormat(this.language,{notation:"compact",maximumFractionDigits:1}).format(t)}date(t){return new Date(t.length===10?`${t}T00:00:00`:t).toLocaleDateString(this.language,{day:"numeric",month:"long"})}hour(t){return new Date(2e3,0,1,t).toLocaleTimeString(this.language,{hour:"numeric",minute:"2-digit"})}month(t){return new Date(2e3,t,1).toLocaleDateString(this.language,{month:"short"})}weekday(t){return new Date(2024,0,1+t).toLocaleDateString(this.language,{weekday:"short"})}};var je=e=>e.endsWith(".")?e:`${e}.`,Ye={intro:{title:"Your lab",about:"Hosts, guests and containers"},uptime:{title:"Uptime",about:"The longest streak without a restart"},restarts:{title:"Restarts",about:"What restarted most"},blocked:{title:"Blocked",about:"DNS queries your blocker stopped"},media:{title:"Media",about:"Hours streamed from your media server"},power:{title:"Power",about:"What the lab used, and what it cost"},personality:{title:"Personality",about:"Your homelab personality"},summary:{title:"Summary",about:"One image to share"}},Ve={history_break:"An integration update stopped a sensor's history; Wrapped stitches the old history to what it records now.",price_hourly:"Priced hour by hour with your price sensor.",price_live:"Your price sensor has no history yet; prices are collected from now on.",price_fixed:"Priced with the fixed price from your Energy dashboard.",price_missing:"Add a price to the Energy dashboard to see what it cost.",pick_meters:"Pick the energy meters your lab is on (smart plugs, a PDU, a UPS that measures kWh) in Homelab Wrapped's options: Settings \u2192 Devices & services \u2192 Homelab Wrapped \u2192 Configure."},qe={title:"Homelab Wrapped",heading:"Your lab can make these cards today",readyCount:(e,t)=>`${e} of ${t} ready`,ready:"Ready",counting:"Counting",locked:"Locked",since:e=>`Since ${e}`,readyOn:e=>`Ready ${e}`,collectingSince:e=>`Collecting since ${e}`,from:e=>`From ${e}`,connect:e=>`Connect ${e}`,builtFromOthers:"Built from the other cards",copy:"Copy diagnostics",copied:"Copied: no names, hostnames or IPs",copyFailed:"Couldn't copy; your browser blocked it",privacy:"Read-only. Nothing leaves your network.",refresh:"Check again",loading:"Checking what your lab has\u2026",failed:e=>`Couldn't check your lab: ${e}`,storyFailed:e=>`Couldn't load your Wrapped: ${e}`},Ge={play:e=>`Play your ${e} Wrapped`,years:"Which year",loadingCards:"Wrapping up your year\u2026",noCards:"No cards yet: connect something above, or give Wrapped a week.",close:"Close",previous:"Previous card",next:"Next card",earlyLook:"Early look: Wrapped is still counting",sinceNote:e=>`Since ${e}`,introKicker:e=>`Your ${e} in the lab`,introTitle:"Here's what kept your homelab busy.",hosts:e=>e===1?"host":"hosts",guests:e=>e===1?"guest":"guests",containers:e=>e===1?"container":"containers",watching:e=>`Wrapped watched ${e} ${e==="1"?"machine":"machines"}.`,uptimeKicker:"Longest streak",days:e=>`${e} ${e==="1"?"day":"days"}`,uptimeLine:(e,t,r,s)=>`${r?"At least that long: ":""}${e} went without a single restart${t?s?", and was still going at the end of the year":", and it's still going":""}.`,currentStreaks:"Up right now",upAtYearEnd:"Up at the end of the year",servicesKicker:"Services",servicesUp:(e,t)=>`${e===1?"Your monitored service was":`Your ${e} monitored services were`} up ${t} of the past year.`,leastReliable:"Least reliable",summaryServices:e=>"services up",gridTitle:"Your year, day by day",gridUp:"Up all day",gridRestart:"Restarted 1, 2, 3+ times",gridUnknown:"No data",restartsKicker:"Restarts",restartsMost:(e,t)=>`${e} restarted most: ${t} ${t==="1"?"time":"times"}.`,restartsNone:"Not a single restart. Impressive.",busiestDay:(e,t)=>`Busiest day: ${e}, with ${t} restarts.`,favouriteHour:e=>`Restarts like to happen around ${e}.`,never:e=>`Never restarted: ${e}.`,andMore:(e,t)=>`${e} and ${t} more`,containersKicker:"Container restarts",containersMost:(e,t,r)=>`Your containers restarted ${e} ${e==="1"?"time":"times"}. ${t} led with ${r}.`,containersNone:e=>e==="1"?"Your container didn't restart.":`None of your ${e} containers restarted.`,networkKicker:"Network restarts",networkMost:(e,t,r)=>`Your network gear restarted ${e} ${e==="1"?"time":"times"}. ${t} led with ${r}.`,networkNone:e=>e==="1"?"Your network device didn't restart.":`None of your ${e} network devices restarted.`,machinesTitle:"Machines",containersTitle:"Containers",networkTitle:"Network",blockedKicker:"Blocked",blockedTitle:e=>`${e} DNS ${e==="1"?"query":"queries"} blocked`,perDay:e=>`That's ${e} a day kept away from your devices.`,bestBlockedDay:(e,t)=>`Busiest day: ${e}, with ${t} blocked.`,mediaKicker:"Media",mediaTitle:e=>`${e==="1"?"hour":"hours"} of films, shows and music played.`,mediaDays:e=>`That's ${e} days of non-stop streaming.`,bestMediaDay:(e,t)=>`Biggest day: ${e}, with ${t} ${t==="1"?"hour":"hours"}.`,topTitle:(e,t)=>`Played most: ${e}, ${t} ${t==="1"?"hour":"hours"}.`,topTitles:"Most played",hoursUnit:"h",servers:"Per media server",powerKicker:"Power",powerTitle:"kWh to keep the lab running.",powerCost:(e,t)=>je(`That cost ${t?"about ":""}${e}`),powerWatts:e=>`An average of ${e} W, day and night.`,powerPrice:e=>`You paid ${e} per kWh on average.`,cutsKicker:"Power cuts",cutsTitle:e=>e===1?"power cut your UPS rode out.":"power cuts your UPS rode out.",cuts:(e,t,r)=>e==="1"?`Your UPS rode out one power cut: ${t} on battery.`:`Your UPS rode out ${e} power cuts: ${t} on battery, the longest ${r}.`,seconds:e=>`${e} ${e==="1"?"second":"seconds"}`,minutes:e=>`${e} ${e==="1"?"minute":"minutes"}`,hours:e=>`${e} ${e==="1"?"hour":"hours"}`,noCuts:"Not one power cut: your UPS never had to step in.",summaryCuts:e=>e==="1"?"power cut":"power cuts",summaryKicker:e=>`That was ${e}`,summaryTitle:"Your homelab, wrapped.",summaryStreak:e=>e==="1"?"day without a restart":"days without a restart",summaryRestarts:e=>e==="1"?"restart":"restarts",summaryContainerRestarts:e=>e==="1"?"container restart":"container restarts",summaryNetworkRestarts:e=>e==="1"?"network restart":"network restarts",summaryBlocked:e=>e==="1"?"query blocked":"queries blocked",summaryMedia:e=>e==="1"?"hour played":"hours played",summaryPower:e=>"kWh used",personalityKicker:"Your homelab personality",personalityWhy:"Why",summaryMachines:e=>e==="1"?"machine watched":"machines watched",done:"Done"},Xe={rock:{name:"The Rock",tagline:"Set it and forget it. Your lab just keeps going.",icon:"mdi:image-filter-hdr",reason:e=>`${e} ${e==="1"?"day":"days"} without a single restart`},tinkerer:{name:"The Tinkerer",tagline:"Something is always being upgraded, rebuilt or tried out.",icon:"mdi:wrench",reason:(e,t)=>`${e} ${e==="1"?"restart":"restarts"} in ${t}`},night_owl:{name:"The Night Owl",tagline:"Your maintenance window starts after bedtime.",icon:"mdi:owl",reason:e=>`${e}% of restarts between 22:00 and 05:00`},weekend_warrior:{name:"The Weekend Warrior",tagline:"Saturdays are for upgrades.",icon:"mdi:hammer-wrench",reason:e=>`${e}% of restarts on a weekend`},gatekeeper:{name:"The Gatekeeper",tagline:"Nothing gets past your DNS.",icon:"mdi:shield-check",reason:e=>`${e} ${e==="1"?"query":"queries"} blocked a day`},cinephile:{name:"The Cinephile",tagline:"Your media server is the busiest machine in the house.",icon:"mdi:popcorn",reason:e=>`${e} ${e==="1"?"hour":"hours"} played a day`},sipper:{name:"The Sipper",tagline:"The whole lab draws less than an old light bulb.",icon:"mdi:leaf",reason:e=>`${e} W on average`},survivor:{name:"The Survivor",tagline:"The power goes out. Your lab doesn't.",icon:"mdi:home-battery",reason:e=>`${e} ${e==="1"?"power cut":"power cuts"} ridden out`},power_plant:{name:"The Power Plant",tagline:"Your lab could heat a small room. It probably does.",icon:"mdi:lightning-bolt",reason:e=>`${e} W on average`},collector:{name:"The Collector",tagline:"Why run one service when you can run them all?",icon:"mdi:package-variant-closed",reason:e=>`${e} ${e==="1"?"guest or container":"guests and containers"}`},all_rounder:{name:"The All-Rounder",tagline:"A bit of everything, nothing overdone.",icon:"mdi:compass-outline",reason:()=>""}},Je={brand:"Homelab Wrapped",footer:"Made with Homelab Wrapped for Home Assistant",longestBy:(e,t)=>`Longest streak: ${e}, ${t}`,button:"Share image",title:"Your share image",names:"Show machine names",namesHint:"Off by default: hostnames can tell more about your network than you'd like to share.",save:"Save image",back:"Back",failed:"Couldn't save the image."},kt={intro:{title:"Dit lab",about:"V\xE6rter, g\xE6ster og containere"},uptime:{title:"Oppetid",about:"Den l\xE6ngste stime uden en genstart"},restarts:{title:"Genstarter",about:"Hvad der genstartede mest"},blocked:{title:"Blokeret",about:"DNS-foresp\xF8rgsler, som din DNS-blokker stoppede"},media:{title:"Medier",about:"Timer streamet fra din medieserver"},power:{title:"Str\xF8m",about:"Hvad labbet brugte, og hvad det kostede"},personality:{title:"Personlighed",about:"Dit homelabs personlighed"},summary:{title:"Opsummering",about:"\xC9t billede at dele"}},wt={history_break:"En opdatering af en integration stoppede en sensors historik; Wrapped syr den gamle historik sammen med det, den registrerer nu.",price_hourly:"Prissat time for time med din prissensor.",price_live:"Din prissensor har ingen historik endnu; priserne samles fra nu af.",price_fixed:"Prissat med den faste pris fra dit Energi-dashboard.",price_missing:"Tilf\xF8j en pris i Energi-dashboardet for at se, hvad det kostede.",pick_meters:"V\xE6lg de energim\xE5lere, dit lab sidder p\xE5 (smartstik, en PDU, en UPS, der m\xE5ler kWh), i Homelab Wrappeds indstillinger: Indstillinger \u2192 Enheder og tjenester \u2192 Homelab Wrapped \u2192 Konfigurer."},xt={title:"Homelab Wrapped",heading:"Dit lab kan lave disse kort i dag",readyCount:(e,t)=>`${e} af ${t} klar`,ready:"Klar",counting:"T\xE6ller",locked:"L\xE5st",since:e=>`Siden ${e}`,readyOn:e=>`Klar ${e}`,collectingSince:e=>`Samler data siden ${e}`,from:e=>`Fra ${e}`,connect:e=>`Forbind ${e}`,builtFromOthers:"Bygget ud fra de andre kort",copy:"Kopi\xE9r diagnostik",copied:"Kopieret: ingen navne, v\xE6rtsnavne eller IP-adresser",copyFailed:"Kunne ikke kopiere; din browser blokerede det",privacy:"L\xE6ser kun. Intet forlader dit netv\xE6rk.",refresh:"Tjek igen",loading:"Tjekker, hvad dit lab har\u2026",failed:e=>`Kunne ikke tjekke dit lab: ${e}`,storyFailed:e=>`Kunne ikke hente dit Wrapped: ${e}`},St={play:e=>`Se dit Wrapped for ${e}`,years:"Hvilket \xE5r",loadingCards:"Pakker dit \xE5r ind\u2026",noCards:"Ingen kort endnu: forbind noget ovenfor, eller giv Wrapped en uge.",close:"Luk",previous:"Forrige kort",next:"N\xE6ste kort",earlyLook:"Et tidligt kig: Wrapped t\xE6ller stadig",sinceNote:e=>`Siden ${e}`,introKicker:e=>`Dit ${e} i labbet`,introTitle:"Her er, hvad der gav dit homelab travlt.",hosts:e=>e===1?"v\xE6rt":"v\xE6rter",guests:e=>e===1?"g\xE6st":"g\xE6ster",containers:e=>e===1?"container":"containere",watching:e=>`Wrapped holdt \xF8je med ${e} ${e==="1"?"maskine":"maskiner"}.`,uptimeKicker:"L\xE6ngste stime",days:e=>`${e} ${e==="1"?"dag":"dage"}`,uptimeLine:(e,t,r,s)=>`${r?"Mindst s\xE5 l\xE6nge: ":""}${e} k\xF8rte uden en eneste genstart${t?s?", og den k\xF8rte stadig ved \xE5rets udgang":", og den k\xF8rer stadig":""}.`,currentStreaks:"K\xF8rer lige nu",upAtYearEnd:"K\xF8rte ved \xE5rets udgang",servicesKicker:"Tjenester",servicesUp:(e,t)=>`${e===1?"Din overv\xE5gede tjeneste":`Dine ${e} overv\xE5gede tjenester`} var oppe ${t} af det seneste \xE5r.`,leastReliable:"Mindst p\xE5lidelige",summaryServices:()=>"tjenester oppe",gridTitle:"Dit \xE5r, dag for dag",gridUp:"Oppe hele dagen",gridRestart:"Genstartet 1, 2, 3+ gange",gridUnknown:"Ingen data",restartsKicker:"Genstarter",restartsMost:(e,t)=>`${e} genstartede mest: ${t} ${t==="1"?"gang":"gange"}.`,restartsNone:"Ikke en eneste genstart. Imponerende.",busiestDay:(e,t)=>`Travleste dag: ${e}, med ${t} genstarter.`,favouriteHour:e=>`Genstarter sker gerne omkring kl. ${e}.`,never:e=>`Aldrig genstartet: ${e}.`,andMore:(e,t)=>`${e} og ${t} mere`,containersKicker:"Containergenstarter",containersMost:(e,t,r)=>`Dine containere genstartede ${e} ${e==="1"?"gang":"gange"}. ${t} f\xF8rte an med ${r}.`,containersNone:e=>e==="1"?"Din container genstartede ikke.":`Ingen af dine ${e} containere genstartede.`,networkKicker:"Netv\xE6rksgenstarter",networkMost:(e,t,r)=>`Dit netv\xE6rksudstyr genstartede ${e} ${e==="1"?"gang":"gange"}. ${t} f\xF8rte an med ${r}.`,networkNone:e=>e==="1"?"Din netv\xE6rksenhed genstartede ikke.":`Ingen af dine ${e} netv\xE6rksenheder genstartede.`,machinesTitle:"Maskiner",containersTitle:"Containere",networkTitle:"Netv\xE6rk",blockedKicker:"Blokeret",blockedTitle:e=>`${e} DNS-${e==="1"?"foresp\xF8rgsel":"foresp\xF8rgsler"} blokeret`,perDay:e=>`Det er ${e} om dagen, der aldrig n\xE5ede dine enheder.`,bestBlockedDay:(e,t)=>`Travleste dag: ${e}, med ${t} blokerede.`,mediaKicker:"Medier",mediaTitle:e=>`${e==="1"?"time":"timer"} med film, serier og musik.`,mediaDays:e=>`Det svarer til ${e} d\xF8gn med streaming i \xE9t str\xE6k.`,bestMediaDay:(e,t)=>`Travleste dag: ${e}, med ${t} ${t==="1"?"time":"timer"}.`,topTitle:(e,t)=>`Mest afspillet: ${e}, ${t} ${t==="1"?"time":"timer"}.`,topTitles:"Mest afspillet",hoursUnit:"t",servers:"Pr. medieserver",powerKicker:"Str\xF8m",powerTitle:"kWh for at holde labbet k\xF8rende.",powerCost:(e,t)=>je(`Det kostede ${t?"omkring ":""}${e}`),powerWatts:e=>`I gennemsnit ${e} W, d\xF8gnet rundt.`,powerPrice:e=>`Du betalte i gennemsnit ${e} pr. kWh.`,cutsKicker:"Str\xF8mafbrydelser",cutsTitle:e=>e===1?"str\xF8mafbrydelse klaret af din UPS.":"str\xF8mafbrydelser klaret af din UPS.",cuts:(e,t,r)=>e==="1"?`Din UPS klarede \xE9n str\xF8mafbrydelse: ${t} p\xE5 batteri.`:`Din UPS klarede ${e} str\xF8mafbrydelser: ${t} p\xE5 batteri, den l\xE6ngste ${r}.`,seconds:e=>`${e} ${e==="1"?"sekund":"sekunder"}`,minutes:e=>`${e} ${e==="1"?"minut":"minutter"}`,hours:e=>`${e} ${e==="1"?"time":"timer"}`,noCuts:"Ikke \xE9n str\xF8mafbrydelse: din UPS beh\xF8vede aldrig at tr\xE6de til.",summaryCuts:e=>e==="1"?"str\xF8mafbrydelse":"str\xF8mafbrydelser",summaryKicker:e=>`Det var ${e}`,summaryTitle:"Dit homelab, pakket ind.",summaryStreak:e=>e==="1"?"dag uden genstart":"dage uden genstart",summaryRestarts:e=>e==="1"?"genstart":"genstarter",summaryContainerRestarts:e=>e==="1"?"containergenstart":"containergenstarter",summaryNetworkRestarts:e=>e==="1"?"netv\xE6rksgenstart":"netv\xE6rksgenstarter",summaryBlocked:e=>e==="1"?"foresp\xF8rgsel blokeret":"foresp\xF8rgsler blokeret",summaryMedia:e=>e==="1"?"time afspillet":"timer afspillet",summaryPower:()=>"kWh brugt",personalityKicker:"Dit homelabs personlighed",personalityWhy:"Hvorfor",summaryMachines:e=>e==="1"?"maskine overv\xE5get":"maskiner overv\xE5get",done:"F\xE6rdig"},Tt={rock:{name:"Klippen",tagline:"S\xE6t det op og glem det. Dit lab bliver bare ved.",icon:"mdi:image-filter-hdr",reason:e=>`${e} ${e==="1"?"dag":"dage"} uden en eneste genstart`},tinkerer:{name:"N\xF8rkleren",tagline:"Der bliver altid opgraderet, bygget om eller pr\xF8vet noget nyt.",icon:"mdi:wrench",reason:(e,t)=>`${e} ${e==="1"?"genstart":"genstarter"} i ${t}`},night_owl:{name:"Natteravnen",tagline:"Dit servicevindue starter efter sengetid.",icon:"mdi:owl",reason:e=>`${e} % af genstarterne mellem kl. 22 og 05`},weekend_warrior:{name:"Weekendkrigeren",tagline:"L\xF8rdage er til opgraderinger.",icon:"mdi:hammer-wrench",reason:e=>`${e} % af genstarterne i weekenden`},gatekeeper:{name:"D\xF8rmanden",tagline:"Intet slipper forbi din DNS.",icon:"mdi:shield-check",reason:e=>`${e} ${e==="1"?"foresp\xF8rgsel":"foresp\xF8rgsler"} blokeret om dagen`},cinephile:{name:"Filmn\xF8rden",tagline:"Din medieserver er husets travleste maskine.",icon:"mdi:popcorn",reason:e=>`${e} ${e==="1"?"time":"timer"} afspillet om dagen`},sipper:{name:"Sparegrisen",tagline:"Hele labbet bruger mindre end en gammel gl\xF8dep\xE6re.",icon:"mdi:leaf",reason:e=>`${e} W i gennemsnit`},survivor:{name:"Overleveren",tagline:"Str\xF8mmen g\xE5r. Det g\xF8r dit lab ikke.",icon:"mdi:home-battery",reason:e=>`${e} ${e==="1"?"str\xF8mafbrydelse":"str\xF8mafbrydelser"} klaret`},power_plant:{name:"Kraftv\xE6rket",tagline:"Dit lab kunne varme et lille v\xE6relse op. Det g\xF8r det nok.",icon:"mdi:lightning-bolt",reason:e=>`${e} W i gennemsnit`},collector:{name:"Samleren",tagline:"Hvorfor k\xF8re \xE9n tjeneste, n\xE5r du kan k\xF8re dem alle?",icon:"mdi:package-variant-closed",reason:e=>`${e} ${e==="1"?"g\xE6st eller container":"g\xE6ster og containere"}`},all_rounder:{name:"Den alsidige",tagline:"Lidt af det hele, intet overdrevet.",icon:"mdi:compass-outline",reason:()=>""}},At={brand:"Homelab Wrapped",footer:"Lavet med Homelab Wrapped til Home Assistant",longestBy:(e,t)=>`L\xE6ngste stime: ${e}, ${t}`,button:"Del billede",title:"Dit delebillede",names:"Vis maskinnavne",namesHint:"Sl\xE5et fra som standard: v\xE6rtsnavne kan sige mere om dit netv\xE6rk, end du har lyst til at dele.",save:"Gem billede",back:"Tilbage",failed:"Kunne ikke gemme billedet."},ze={en:{cards:Ye,hints:Ve,text:qe,story:Ge,personalities:Xe,share:Je},da:{cards:kt,hints:wt,text:xt,story:St,personalities:Tt,share:At}},me=Ye,ge=Ve,g=qe,o=Ge,k=Xe,b=Je;function Ze(e){let r=(e??"").toLowerCase().split("-")[0]==="da"?ze.da:ze.en;me=r.cards,ge=r.hints,g=r.text,o=r.story,k=r.personalities,b=r.share}function et(e,t,r){switch(e.card){case"intro":return Ct(e,t,r);case"uptime":return Et(e,r);case"restarts":return Mt(e,r);case"blocked":return Ht(e,r);case"media":return Lt(e,r);case"power":return Ot(e,r);case"personality":return Wt(e,t,r)}}function v(e,t,r,s,i){return l`
    <section class="slide ${t}">
      <div class="text">
        ${r}
        <p class="note">
          ${e?.since?o.sinceNote(i.date(e.since)):p}
          ${e?.state==="counting"?l`<span class="early">${o.earlyLook}</span>`:p}
        </p>
      </div>
      <div class="visual">${s}</div>
    </section>
  `}function Ct(e,t,r){let s=[[e.hosts,o.hosts(e.hosts)],[e.guests,o.guests(e.guests)],[e.containers,o.containers(e.containers)]];return v(e,"intro",l`
      <p class="kicker">${o.introKicker(t)}</p>
      <h2 class="title">${o.introTitle}</h2>
      ${e.machines?l`<p class="line">${o.watching(r.number(e.machines))}</p>`:p}
    `,l`<div class="tiles">
      ${s.map(([i,n])=>l`<div class="tile"><b>${r.number(i)}</b><span>${n}</span></div>`)}
    </div>`,r)}function Et(e,t){let r=e.longest,s=e.services;return r?v(e,"uptime",l`
      <p class="kicker">${o.uptimeKicker}</p>
      <h2 class="hero">${o.days(t.number(r.days,r.days<10?1:0))}</h2>
      <p class="line">${o.uptimeLine(r.name,r.ongoing,r.open_start,e.over??!1)}</p>
      ${s?l`<p class="fact">${o.servicesUp(s.count,B(s.uptime,t))}</p>`:p}
      ${e.current.length?l`<p class="sub">${e.over?o.upAtYearEnd:o.currentStreaks}</p>
            <ul class="list">
              ${e.current.slice(0,3).map(i=>l`<li><span>${i.name}</span><b>${o.days(t.amount(i.days))}</b></li>`)}
            </ul>`:p}
    `,Dt(e,t),t):Rt(e,s,t)}function Rt(e,t,r){return t?v(e,"uptime",l`
      <p class="kicker">${o.servicesKicker}</p>
      <h2 class="hero">${B(t.uptime,r)}</h2>
      <p class="line">${o.servicesUp(t.count,B(t.uptime,r))}</p>
    `,t.least.length?l`<div>
          <p class="sub">${o.leastReliable}</p>
          <ul class="list">
            ${t.least.map(s=>l`<li><span>${s.name}</span><b>${B(s.uptime,r)}</b></li>`)}
          </ul>
        </div>`:l`<div class="icon" aria-hidden="true"><ha-icon .icon=${"mdi:check-network"}></ha-icon></div>`,r):l``}function B(e,t){if(e>=100)return t.percent(100,0);let r=e>=99.95?2:1,s=10**r;return t.percent(Math.floor(e*s)/s,r)}var z=5;function Pt(e){let t=e.slice(0,z).join(", ");return e.length>z?o.andMore(t,e.length-z):t}function y(e,t){return[e,t(e)]}function be(e,t){return e.longest?y(t.amount(e.longest.days),o.summaryStreak):y(B(e.services?.uptime??0,t),o.summaryServices)}function Dt(e,t){let s=(new Date(`${e.grid.start}T00:00:00`).getDay()+6)%7,i=[...Array(s).fill(null).map(()=>"pad"),...e.grid.restarts.map(Nt)];return l`
    <figure class="year">
      <figcaption>${o.gridTitle}</figcaption>
      <div class="grid" role="img" aria-label=${o.gridTitle}>
        ${i.map(n=>l`<i class=${n}></i>`)}
      </div>
      <div class="legend">
        <span><i class="up"></i>${o.gridUp}</span>
        <span><b class="scale"><i class="r1"></i><i class="r2"></i><i class="r3"></i></b>${o.gridRestart}</span>
        <span><i class="none"></i>${o.gridUnknown}</span>
        <span class="weekdays">${t.weekday(0)}–${t.weekday(6)} ↓</span>
      </div>
    </figure>
  `}function Nt(e){return e===null?"none":e===0?"up":e===1?"r1":e===2?"r2":"r3"}function Mt(e,t){let r=e.containers,s=e.network??null,i=r??s;if(!e.machines.length&&i)return Ut(e,i,t);let n=e.machines[0],a=e.by_hour.indexOf(Math.max(...e.by_hour));return v(e,"restarts",l`
      <p class="kicker">${o.restartsKicker}</p>
      <h2 class="hero">${t.number(e.total)}</h2>
      <p class="line">
        ${e.total&&n?o.restartsMost(n.name,t.number(n.restarts)):o.restartsNone}
      </p>
      ${e.busiest_day&&e.busiest_day.restarts>1?l`<p class="fact">
            ${o.busiestDay(t.date(e.busiest_day.date),t.number(e.busiest_day.restarts))}
          </p>`:p}
      ${e.total>2?l`<p class="fact">${o.favouriteHour(t.hour(a))}</p>`:p}
      ${e.never.length?l`<p class="fact">${o.never(Pt(e.never))}</p>`:p}
      ${r?l`<p class="fact">${tt(r,t)}</p>`:p}
      ${s?l`<p class="fact">${rt(s,t)}</p>`:p}
    `,l`${r?.top.length||s?.top.length?l`<p class="sub">${o.machinesTitle}</p>`:p}
      ${ye(e.machines,t)} ${se(r,o.containersTitle,t)}
      ${se(s,o.networkTitle,t)}`,t)}function se(e,t,r){return e?.top.length?l`<p class="sub">${t}</p>${ye(e.top.slice(0,3),r)}`:p}function fe(e,t){let r=e.machines.length?null:e.containers??e.network??null;return r?y(t.number(r.total),r===e.containers?o.summaryContainerRestarts:o.summaryNetworkRestarts):y(t.number(e.total),o.summaryRestarts)}function Ut(e,t,r){let s=e.containers,i=e.network??null;return v(e,"restarts",l`
      <p class="kicker">${t===s?o.containersKicker:o.networkKicker}</p>
      <h2 class="hero">${r.number(t.total)}</h2>
      ${s?l`<p class="line">${tt(s,r)}</p>`:p}
      ${i?l`<p class=${s?"fact":"line"}>${rt(i,r)}</p>`:p}
    `,s&&i?l`${se(s,o.containersTitle,r)} ${se(i,o.networkTitle,r)}`:ye(t.top,r),r)}function tt(e,t){let r=e.top[0];return r?o.containersMost(t.number(e.total),r.name,t.number(r.restarts)):o.containersNone(t.number(e.watched))}function rt(e,t){let r=e.top[0];return r?o.networkMost(t.number(e.total),r.name,t.number(r.restarts)):o.networkNone(t.number(e.watched))}function ye(e,t){let r=Math.max(1,...e.map(s=>s.restarts));return l`<ul class="bars">
    ${e.map(s=>l`<li>
        <span class="name">${s.name}</span>
        <span class="bar"><i style="width: ${s.restarts/r*100}%"></i></span>
        <b>${t.number(s.restarts)}</b>
      </li>`)}
  </ul>`}function Ht(e,t){return v(e,"blocked",l`
      <p class="kicker">${o.blockedKicker}</p>
      <h2 class="hero">${t.big(e.total)}</h2>
      <p class="line">${o.blockedTitle(t.number(e.total))}</p>
      <p class="fact">${o.perDay(t.number(e.per_day))}</p>
      <p class="fact">${o.bestBlockedDay(t.date(e.best_day.date),t.number(e.best_day.blocked))}</p>
    `,l`<div class="shield" aria-hidden="true">
      <svg viewBox="0 0 24 24"><path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Zm-1 14-4-4 1.4-1.4 2.6 2.6 5.6-5.6L18 9l-7 7Z" /></svg>
    </div>`,t)}function Lt(e,t){let r=Math.max(1,...e.by_month.map(i=>i??0)),s=e.titles??[];return v(e,"media",l`
      <p class="kicker">${o.mediaKicker}</p>
      <h2 class="hero">${t.amount(e.hours)}</h2>
      <p class="line">${o.mediaTitle(t.amount(e.hours))}</p>
      ${e.hours>=48?l`<p class="fact">${o.mediaDays(t.number(e.hours/24,1))}</p>`:p}
      <p class="fact">${o.bestMediaDay(t.date(e.best_day.date),t.number(e.best_day.hours,1))}</p>
      ${s.length===1?l`<p class="fact">${o.topTitle(s[0].title,t.number(s[0].hours,1))}</p>`:p}
      ${s.length>1?l`<p class="sub">${o.topTitles}</p>
            <ul class="list">
              ${s.map(i=>l`<li><span>${i.title}</span><b>${t.number(i.hours,1)} ${o.hoursUnit}</b></li>`)}
            </ul>`:p}
      ${e.servers.length>1?l`<p class="sub">${o.servers}</p>
            <ul class="list">
              ${e.servers.slice(0,z).map(i=>l`<li><span>${i.name}</span><b>${t.amount(i.hours)} ${o.hoursUnit}</b></li>`)}
            </ul>`:p}
    `,l`<div class="months">
      ${e.by_month.map((i,n)=>l`<div class=${i===null?"month none":"month"}>
          <span class="column"><i style="height: ${(i??0)/r*100}%"></i></span>
          <span class="label">${t.month(n)}</span>
        </div>`)}
    </div>`,t)}function Ot(e,t){let r=e.power_cuts;if(e.kwh===null||e.watts===null)return It(e,r,t);let s=Math.max(.001,...e.by_month.map(n=>n??0)),i=(n,a)=>t.money(n,e.currency??"",a);return v(e,"power",l`
      <p class="kicker">${o.powerKicker}</p>
      <h2 class="hero">${t.amount(e.kwh)}</h2>
      <p class="line">${o.powerTitle}</p>
      ${e.cost!==null?l`<p class="fact">${o.powerCost(i(e.cost,0),e.estimated)}</p>`:p}
      <p class="fact">${o.powerWatts(t.number(e.watts))}</p>
      ${e.average_price!==null?l`<p class="fact">${o.powerPrice(i(e.average_price,2))}</p>`:p}
      ${r?l`<p class="fact">${st(r,t)}</p>`:p}
      ${e.meters.length>1?l`<ul class="list">
            ${e.meters.slice(0,z).map(n=>l`<li><span>${n.name}</span><b>${t.amount(n.kwh)} kWh</b></li>`)}
          </ul>`:p}
    `,l`<div class="months">
      ${e.by_month.map((n,a)=>l`<div class=${n===null?"month none":"month"}>
          <span class="column"><i style="height: ${(n??0)/s*100}%"></i></span>
          <span class="label">${t.month(a)}</span>
        </div>`)}
    </div>`,t)}function It(e,t,r){return t?v(e,"power",l`
      <p class="kicker">${o.cutsKicker}</p>
      <h2 class="hero">${r.number(t.count)}</h2>
      <p class="line">${o.cutsTitle(t.count)}</p>
      <p class="fact">${st(t,r)}</p>
    `,l`<div class="icon" aria-hidden="true"><ha-icon .icon=${"mdi:home-battery"}></ha-icon></div>`,r):l``}function st(e,t){if(!e.count)return o.noCuts;let r=e.seconds??e.minutes*60,s=e.longest_seconds??e.longest_minutes*60;return o.cuts(t.number(e.count),Qe(r,t),Qe(s,t))}function Qe(e,t){return e<90?o.seconds(t.number(e)):e<90*60?o.minutes(t.amount(e/60)):o.hours(t.amount(e/3600))}function $e(e,t){return e.kwh!==null?y(t.amount(e.kwh),o.summaryPower):y(t.number(e.power_cuts?.count??0),o.summaryCuts)}function Wt(e,t,r){let s=k[e.key]??k.all_rounder,i=e.traits.map(n=>k[n.key]?.reason(r.number(n.value,n.value<10?1:0),t)).filter(n=>!!n);return v(null,"personality",l`
      <p class="kicker">${o.personalityKicker}</p>
      <h2 class="title">${s.name}</h2>
      <p class="line">${s.tagline}</p>
      ${i.length?l`<p class="sub">${o.personalityWhy}</p>
            <ul class="list">
              ${i.map(n=>l`<li><span>${n}</span></li>`)}
            </ul>`:p}
    `,l`<div class="icon" aria-hidden="true"><ha-icon .icon=${s.icon}></ha-icon></div>`,r)}function it(e,t,r){let s=[],i=e.find(a=>a.card==="personality"),n=i?k[i.key]??k.all_rounder:void 0;for(let a of e)a.card==="uptime"&&s.push(be(a,r)),a.card==="restarts"&&s.push(fe(a,r)),a.card==="blocked"&&s.push(y(r.big(a.total),o.summaryBlocked)),a.card==="media"&&s.push(y(r.amount(a.hours),o.summaryMedia)),a.card==="power"&&s.push($e(a,r)),a.card==="intro"&&a.machines&&s.push(y(r.number(a.machines),o.summaryMachines));return v(null,"summary",l`
      <p class="kicker">${o.summaryKicker(t)}</p>
      <h2 class="title">${o.summaryTitle}</h2>
      ${n?l`<p class="line who"><ha-icon .icon=${n.icon}></ha-icon>${n.name}</p>`:p}
    `,l`<div class="tiles">
      ${s.map(([a,d])=>l`<div class="tile"><b class=${a.length>6?"long":""}>${a}</b><span>${d}</span></div>`)}
    </div>`,r)}var A=1080,j=1920,f=88,w='Roboto, "Segoe UI", "Helvetica Neue", Arial, sans-serif';function at(e,t,r,s){let i=new U(s);e.width=A,e.height=j;let n=e.getContext("2d");if(!n)return;let a=n.createLinearGradient(0,0,A,j);a.addColorStop(0,"#312e81"),a.addColorStop(.55,"#6d28d9"),a.addColorStop(1,"#be185d"),n.fillStyle=a,n.fillRect(0,0,A,j),n.fillStyle="#fff",n.textBaseline="alphabetic";let d=150;n.font=`700 34px ${w}`,jt(n,b.brand.toUpperCase(),f,d,6),d+=190,n.font=`800 200px ${w}`,n.fillText(String(t.year),f-8,d);let c=nt(t.cards,"personality");if(c){let h=k[c.key]??k.all_rounder;d+=110,n.globalAlpha=.85,n.font=`600 34px ${w}`,n.fillText(o.personalityKicker,f,d),n.globalAlpha=1,d+=92,n.font=`800 88px ${w}`,n.fillText(h.name,f,d,A-2*f),d+=64,n.font=`500 38px ${w}`,d=Yt(n,h.tagline,f,d,A-2*f,50)}d+=70,d=Kt(n,Ft(t.cards,i),d);let u=nt(t.cards,"uptime");if(u?.longest){let h=j-190-Bt(u);if(r.names){n.font=`500 34px ${w}`;let m=u.longest,$=Math.max(h-110,d+64);n.fillText(b.longestBy(m.name,o.days(i.amount(m.days))),f,$,A-2*f)}n.font=`600 32px ${w}`,n.fillText(o.gridTitle,f,h-28),zt(n,u,h)}n.fillStyle="#fff",n.globalAlpha=.75,n.font=`500 30px ${w}`,n.fillText(b.footer,f,j-90),n.globalAlpha=1}async function ot(e,t){let r=`homelab-wrapped-${t}.png`,s=await new Promise(d=>e.toBlob(d,"image/png"));if(!s)throw new Error("no image");let i=new File([s],r,{type:"image/png"});if(navigator.canShare?.({files:[i]}))try{await navigator.share({files:[i],title:b.brand});return}catch(d){if(d?.name==="AbortError")throw d}let n=URL.createObjectURL(s),a=document.createElement("a");a.href=n,a.download=r,document.body.append(a),a.click(),a.remove(),setTimeout(()=>URL.revokeObjectURL(n),1e4)}function nt(e,t){return e.find(r=>r.card===t)}function Ft(e,t){let r=[];for(let s of e)s.card==="uptime"&&r.push(be(s,t)),s.card==="restarts"&&r.push(fe(s,t)),s.card==="blocked"&&r.push(y(t.big(s.total),o.summaryBlocked)),s.card==="media"&&r.push(y(t.amount(s.hours),o.summaryMedia)),s.card==="power"&&r.push($e(s,t));return r.slice(0,6)}function Kt(e,t,r){let i=(A-2*f-28)/2,n=190;return t.forEach(([a,d],c)=>{let u=f+c%2*(i+28),h=r+Math.floor(c/2)*(n+28);e.fillStyle="rgba(255, 255, 255, 0.14)",dt(e,u,h,i,n,28),e.fillStyle="#fff",e.font=`800 84px ${w}`,e.fillText(a,u+32,h+104,i-64),e.font=`500 32px ${w}`,e.globalAlpha=.9,e.fillText(d,u+32,h+152,i-64),e.globalAlpha=1}),r+Math.ceil(t.length/2)*(n+28)}function lt(e){let r=(new Date(`${e.grid.start}T00:00:00`).getDay()+6)%7,s=Math.ceil((r+e.grid.restarts.length)/7);return{offset:r,step:Math.min(34,(A-2*f)/Math.max(s,1))}}function Bt(e){return 7*lt(e).step}function zt(e,t,r){let{offset:s,step:i}=lt(t),n=i*.8;return t.grid.restarts.forEach((a,d)=>{let c=s+d;e.fillStyle=a===null?"rgba(255, 255, 255, 0.15)":a===0?"#34d399":a===1?"#fde68a":a===2?"#fbbf24":"#f97316",dt(e,f+Math.floor(c/7)*i,r+c%7*i,n,n,n/5)}),r+7*i}function dt(e,t,r,s,i,n){e.beginPath(),typeof e.roundRect=="function"?e.roundRect(t,r,s,i,n):(e.moveTo(t+n,r),e.arcTo(t+s,r,t+s,r+i,n),e.arcTo(t+s,r+i,t,r+i,n),e.arcTo(t,r+i,t,r,n),e.arcTo(t,r,t+s,r,n),e.closePath()),e.fill()}function jt(e,t,r,s,i){let n=r;for(let a of t)e.fillText(a,n,s),n+=e.measureText(a).width+i}function Yt(e,t,r,s,i,n){let a="";for(let d of t.split(" ")){let c=a?`${a} ${d}`:d;e.measureText(c).width>i&&a?(e.fillText(a,r,s),a=d,s+=n):a=c}return e.fillText(a,r,s),s}var ve=class extends _{constructor(){super();this._onKey=r=>{if(r.repeat||r.altKey||r.ctrlKey||r.metaKey)return;let s=r.composedPath()[0];if(s instanceof HTMLElement){let i=s instanceof HTMLInputElement&&!["checkbox","radio","button"].includes(s.type);if(s.isContentEditable||i||["TEXTAREA","SELECT"].includes(s.tagName)||["BUTTON","A","INPUT"].includes(s.tagName)&&(r.key===" "||r.key==="Enter"))return}if(this._sharing){r.key==="Escape"&&(this._sharing=!1,r.preventDefault());return}if(r.key==="ArrowRight"||r.key===" ")this._go(1);else if(r.key==="ArrowLeft")this._go(-1);else if(r.key==="Escape")this._close();else return;r.preventDefault()};this._tap=r=>{let s=this.getBoundingClientRect();this._go(r.clientX-s.left<s.width*.3?-1:1)};this._index=0,this._sharing=!1,this._names=!1,this.language=navigator.language}static{this.properties={data:{attribute:!1},language:{type:String},_index:{state:!0},_sharing:{state:!0},_names:{state:!0},_shareError:{state:!0}}}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey),this.setAttribute("role","dialog"),this.setAttribute("aria-modal","true")}firstUpdated(){this.setAttribute("aria-label",`${b.brand} ${this.data.year}`),this.renderRoot.querySelector("button.close")?.focus()}willUpdate(r){r.has("data")&&r.get("data")!==void 0&&(this._index=0)}disconnectedCallback(){window.removeEventListener("keydown",this._onKey),super.disconnectedCallback()}get _count(){return this.data.cards.length+1}_go(r){let s=this._index+r;s>=this._count?this._close():this._index=Math.max(0,s)}_close(){this.dispatchEvent(new CustomEvent("close"))}updated(r){if(r.has("_sharing")&&r.get("_sharing")!==void 0){let i=this._sharing?".share-controls input":".end .pill.light";this.renderRoot.querySelector(i)?.focus()}let s=this.renderRoot.querySelector("canvas.share");s&&at(s,this.data,{names:this._names},this.language)}async _save(){let r=this.renderRoot.querySelector("canvas.share");if(r){this._shareError=void 0;try{await ot(r,this.data.year)}catch(s){s?.name!=="AbortError"&&(this._shareError=b.failed)}}}_renderShare(){return l`
      <div class="share-view" role="dialog" aria-label=${b.title}>
        <canvas class="share"></canvas>
        <div class="share-controls">
          <label>
            <input
              type="checkbox"
              .checked=${this._names}
              @change=${r=>this._names=r.target.checked}
            />
            ${b.names}
          </label>
          <p class="share-hint">${b.namesHint}</p>
          ${this._shareError?l`<p class="share-hint">${this._shareError}</p>`:""}
          <div class="share-buttons">
            <button class="pill light" @click=${this._save}>${b.save}</button>
            <button class="pill" @click=${()=>this._sharing=!1}>${b.back}</button>
          </div>
        </div>
      </div>
    `}render(){let r=new U(this.language),{cards:s,year:i}=this.data,n=this._index===this._count-1;return l`
      <div class="shade"></div>
      <div class="progress">
        ${Array.from({length:this._count},(a,d)=>l`<i class=${d<=this._index?"seen":""}></i>`)}
      </div>
      <button class="close" aria-label=${o.close} ?inert=${this._sharing} @click=${this._close}>✕</button>
      <div class="stage" aria-live="polite" ?inert=${this._sharing} @click=${this._tap}>
        ${Be(this._index,n?it(s,i,r):et(s[this._index],i,r))}
      </div>
      <button
        class="nav previous"
        aria-label=${o.previous}
        ?inert=${this._sharing}
        @click=${()=>this._go(-1)}
      ></button>
      <button
        class="nav next"
        aria-label=${n?o.done:o.next}
        ?inert=${this._sharing}
        @click=${()=>this._go(1)}
      ></button>
      ${n?l`<div class="end" ?inert=${this._sharing}>
            <button class="pill light" @click=${()=>this._sharing=!0}>${b.button}</button>
            <button class="pill" @click=${this._close}>${o.done}</button>
          </div>`:""}
      ${this._sharing?this._renderShare():""}
    `}static{this.styles=L`
    :host {
      position: fixed;
      inset: 0;
      z-index: 10;
      display: block;
      color: #fff;
      font-family: var(--paper-font-body1_-_font-family, Roboto, "Segoe UI", sans-serif);
      background: #111827;
    }
    /* Behind the progress bar and the close button: they stay readable over a slide
       that scrolls under them. */
    .shade {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      z-index: 2;
      height: 64px;
      background: linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0));
      pointer-events: none;
    }
    .progress {
      position: absolute;
      top: 12px;
      left: 16px;
      right: 64px;
      z-index: 3;
      display: flex;
      gap: 6px;
    }
    .progress i {
      flex: 1;
      height: 4px;
      border-radius: 2px;
      background: rgba(255, 255, 255, 0.3);
    }
    .progress i.seen {
      background: #fff;
    }
    button {
      font: inherit;
      color: inherit;
      cursor: pointer;
    }
    .close {
      position: absolute;
      top: 4px;
      right: 8px;
      z-index: 4;
      width: 48px;
      height: 48px;
      border: 0;
      background: none;
      font-size: 22px;
    }
    /* For keyboards and screen readers. Clicks and taps land on the slide itself, so a
       slide taller than the screen still scrolls under a finger or a mouse wheel. */
    .nav {
      position: absolute;
      top: 48px;
      bottom: 0;
      z-index: 2;
      border: 0;
      background: none;
      padding: 0;
      pointer-events: none;
    }
    .nav.previous {
      left: 0;
      width: 30%;
    }
    .nav.next {
      right: 0;
      width: 70%;
    }
    .nav:focus-visible,
    .close:focus-visible,
    .pill:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }
    .end {
      position: absolute;
      bottom: 32px;
      left: 0;
      right: 0;
      z-index: 4;
      display: flex;
      justify-content: center;
      gap: 12px;
    }
    .pill {
      padding: 12px 28px;
      border-radius: 999px;
      border: 2px solid #fff;
      background: transparent;
      font-weight: 600;
    }
    .pill.light {
      background: #fff;
      color: #111827;
    }
    .share-view {
      position: absolute;
      inset: 0;
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      padding: 24px;
      background: rgba(10, 10, 20, 0.92);
    }
    canvas.share {
      height: min(86vh, 960px);
      max-width: 46vw;
      aspect-ratio: 9 / 16;
      object-fit: contain;
      border-radius: 16px;
      box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
    }
    .share-controls {
      max-width: 340px;
    }
    .share-controls label {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 18px;
      cursor: pointer;
    }
    .share-controls input {
      width: 20px;
      height: 20px;
    }
    .share-hint {
      margin-top: 8px;
      font-size: 14px;
      opacity: 0.75;
    }
    .share-buttons {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
    .stage {
      position: absolute;
      inset: 0;
    }

    /* A slide: text and a picture side by side on wide screens, stacked on phones. */
    .slide {
      box-sizing: border-box;
      height: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      align-items: center;
      gap: 48px;
      padding: 72px clamp(24px, 6vw, 96px) 48px;
      overflow: auto;
      animation: appear 0.35s ease-out;
    }
    @keyframes appear {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .slide {
        animation: none;
      }
    }
    .intro {
      background: linear-gradient(135deg, #312e81, #6d28d9);
    }
    .uptime {
      background: linear-gradient(135deg, #064e3b, #0f766e);
    }
    .restarts {
      background: linear-gradient(135deg, #7c2d12, #c2410c);
    }
    .blocked {
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
    }
    .media {
      background: linear-gradient(135deg, #701a75, #be185d);
    }
    .power {
      background: linear-gradient(135deg, #713f12, #a16207);
    }
    .power .column i {
      background: #fde047;
    }
    .personality {
      background: linear-gradient(135deg, #134e4a, #4338ca);
    }
    .icon {
      display: flex;
      justify-content: center;
      --mdc-icon-size: clamp(140px, 22vw, 320px);
      color: rgba(255, 255, 255, 0.92);
    }
    .who {
      display: flex;
      align-items: center;
      gap: 10px;
      --mdc-icon-size: 1.3em;
    }
    .summary {
      background: linear-gradient(135deg, #111827, #374151);
    }
    p {
      margin: 0 0 12px;
      font-size: clamp(16px, 1.6vw, 22px);
      line-height: 1.4;
    }
    .kicker {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 14px;
      font-weight: 600;
      opacity: 0.85;
    }
    .hero {
      margin: 0 0 0.12em;
      font-size: clamp(56px, 9vw, 140px);
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.03em;
    }
    .title {
      margin: 0 0 16px;
      font-size: clamp(32px, 4.5vw, 64px);
      font-weight: 800;
      line-height: 1.05;
    }
    .line {
      font-size: clamp(18px, 2vw, 28px);
      font-weight: 500;
    }
    .fact,
    .sub {
      opacity: 0.9;
    }
    .sub {
      margin-top: 20px;
      font-weight: 600;
    }
    .note {
      margin-top: 24px;
      font-size: 14px;
      opacity: 0.75;
    }
    .early {
      display: inline-block;
      margin-left: 8px;
      padding: 2px 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.18);
    }
    .list {
      list-style: none;
      margin: 0;
      padding: 0;
      max-width: 420px;
    }
    .list li {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    }
    /* A long container or title wraps instead of pushing its number off a phone's screen. */
    .list li span {
      min-width: 0;
      overflow-wrap: anywhere;
    }
    /* A name without break points (a container's) wraps instead of running out. */
    .slide p {
      overflow-wrap: anywhere;
    }
    .list li b {
      flex: none;
    }
    .tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
    }
    .tile {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 20px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.12);
      /* The number is sized by its tile, not the window: five tiles in a row on a wide
         screen are narrow, and "456,789" must still fit. */
      container-type: inline-size;
    }
    .tile b {
      font-size: clamp(28px, 22cqi, 56px);
      font-weight: 800;
      line-height: 1;
      white-space: nowrap;
    }
    /* "5,2 mio." and the like: smaller, so it stays in its tile. */
    .tile b.long {
      font-size: clamp(22px, 15cqi, 38px);
    }

    /* Uptime: the year, one square per day, a column per week. */
    .year {
      margin: 0;
    }
    .year figcaption {
      margin-bottom: 12px;
      font-weight: 600;
    }
    .grid {
      display: grid;
      grid-auto-flow: column;
      grid-template-rows: repeat(7, auto);
      grid-auto-columns: minmax(0, 1fr);
      gap: 3px;
    }
    .grid i,
    .legend i {
      display: block;
      aspect-ratio: 1;
      border-radius: 2px;
    }
    .up {
      background: #34d399;
    }
    .r1 {
      background: #fde68a;
    }
    .r2 {
      background: #fbbf24;
    }
    .r3 {
      background: #f97316;
    }
    .none {
      background: rgba(255, 255, 255, 0.12);
    }
    .pad {
      visibility: hidden;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 20px;
      margin-top: 12px;
      font-size: 13px;
      opacity: 0.9;
    }
    .legend span {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .legend i {
      width: 12px;
    }
    .legend .scale {
      display: flex;
      gap: 2px;
    }
    .legend .weekdays {
      margin-left: auto;
      opacity: 0.7;
    }

    /* Restarts: one bar per machine. */
    .bars {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 14px;
    }
    .bars li {
      display: grid;
      grid-template-columns: minmax(80px, 30%) 1fr auto;
      align-items: center;
      gap: 12px;
      font-size: 18px;
    }
    .bars .name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bars b {
      /* The same width in every row, so the bars end in one line. */
      min-width: 3ch;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .bar {
      height: 14px;
      border-radius: 7px;
      background: rgba(255, 255, 255, 0.15);
      overflow: hidden;
    }
    .bar i {
      display: block;
      height: 100%;
      min-width: 4px;
      border-radius: 7px;
      background: #fde68a;
    }

    /* Blocked. */
    .shield svg {
      width: min(320px, 60%);
      display: block;
      margin: auto;
      fill: rgba(255, 255, 255, 0.85);
    }

    /* Media: hours per month. */
    .months {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 8px;
      height: min(360px, 50vh);
    }
    .month {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .column {
      flex: 1;
      display: flex;
      align-items: flex-end;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.1);
    }
    .column i {
      display: block;
      width: 100%;
      border-radius: 6px;
      background: #f9a8d4;
    }
    .month.none .column {
      background: rgba(255, 255, 255, 0.04);
    }
    .label {
      font-size: 12px;
      text-align: center;
      opacity: 0.85;
    }

    @media (max-width: 800px) {
      /* Centred while it fits; a slide taller than the screen starts at its top and scrolls
         (auto margins work everywhere, unlike "safe center" on older Safari). */
      .slide {
        display: flex;
        flex-direction: column;
        /* The wide layout centres its two columns; here each block takes the full width. */
        align-items: stretch;
        gap: 28px;
        padding: 64px 20px 96px;
      }
      .slide > * {
        min-width: 0;
      }
      .slide > :first-child {
        margin-top: auto;
      }
      .slide > :last-child {
        margin-bottom: auto;
      }
      .bars li {
        font-size: 15px;
      }
      /* Two tiles a row on any phone; their numbers are sized by the tile. */
      .tiles {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .months {
        height: 180px;
        gap: 4px;
      }
      .legend .weekdays {
        margin-left: 0;
      }
      .share-view {
        flex-direction: column;
        justify-content: flex-start;
        gap: 16px;
        overflow-y: auto;
      }
      canvas.share {
        flex: none;
        height: auto;
        width: min(78vw, 40vh);
        max-width: none;
      }
    }
  `}};customElements.get("homelab-wrapped-story")||customElements.define("homelab-wrapped-story",ve);var Vt=3,qt=40,_e=class extends _{constructor(){super();this._loading=!1;this._retries=0;this.narrow=!1,this._wrapping=!1}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},_coverage:{state:!0},_error:{state:!0},_toast:{state:!0},_story:{state:!0},_wrapping:{state:!0},_year:{state:!0}}}updated(r){r.has("hass")&&this.hass&&!this._coverage&&!this._error&&!this._loading&&this._load()}_closeStory(){this._story=void 0,this.updateComplete.then(()=>this.renderRoot.querySelector(".play")?.focus())}_checkAgain(){this._retries=0,this._load()}disconnectedCallback(){super.disconnectedCallback(),window.clearTimeout(this._retryTimer),window.clearTimeout(this._toastTimer),this._coverage||(this._loading=!1)}async _load(){if(!this.hass)return;window.clearTimeout(this._retryTimer),this._loading=!0,this._error=void 0;let r=!1;try{let s=await this.hass.callWS({type:"homelab_wrapped/coverage"});(this._year===void 0||!s.years.includes(this._year))&&(this._year=s.year),this._coverage=s,this._retries=0}catch(s){if(s?.code==="not_found"&&this._retries<qt){this._retries+=1,this._retryTimer=window.setTimeout(()=>void this._load(),Vt*1e3),r=!0;return}this._error=s instanceof Error?s.message:String(s?.message??s)}finally{this._loading=r}}async _copyDiagnostics(){if(this.hass)try{let r=await this.hass.callWS({type:"homelab_wrapped/diagnostics"});await Gt(JSON.stringify(r,null,2)),this._showToast(g.copied)}catch{this._showToast(g.copyFailed)}}async _play(){if(!(!this.hass||this._wrapping)){this._wrapping=!0;try{let r=await this.hass.callWS({type:"homelab_wrapped/cards",year:this._year});r.cards.length?this._story=r:this._showToast(o.noCards)}catch(r){console.error("Homelab Wrapped: couldn't load the cards",r),this._showToast(g.storyFailed(String(r?.message??r)),15)}finally{this._wrapping=!1}}}get _language(){return this.hass?.locale?.language??this.hass?.language??navigator.language}_showToast(r,s=4){this._toast=r,window.clearTimeout(this._toastTimer),this._toastTimer=window.setTimeout(()=>this._toast=void 0,s*1e3)}_date(r){let s=new Date(`${r}T00:00:00`),i=s.getFullYear()===new Date().getFullYear()?void 0:"numeric";return s.toLocaleDateString(this._language,{day:"numeric",month:"short",year:i})}render(){Ze(this._language);let r=this._coverage?.cards??[],s=r.filter(d=>d.state==="ready").length,i=r.some(d=>d.number<=6&&d.state!=="locked"),n=this._year??new Date().getFullYear(),a=this._coverage?.years??[];return l`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">${g.title}</div>
      </div>
      <main ?inert=${!!this._story}>
        <header>
          <h1>${g.heading}</h1>
          ${this._coverage?l`<p class="count">${g.readyCount(s,r.length)}</p>`:p}
        </header>
        ${i?l`<button class="play" ?disabled=${this._wrapping} @click=${this._play}>
              ${this._wrapping?o.loadingCards:o.play(n)}
            </button>`:p}
        ${i&&a.length>1?l`<div class="years" role="group" aria-label=${o.years}>
              ${[...a].reverse().map(d=>l`<button
                  class=${d===n?"year on":"year"}
                  aria-pressed=${d===n?"true":"false"}
                  @click=${()=>this._year=d}
                >
                  ${d}
                </button>`)}
            </div>`:p}
        ${this._error?l`<p class="error">${g.failed(this._error)}</p>`:this._coverage?l`<section class="grid">${r.map(d=>this._renderCard(d))}</section>`:l`<p class="muted">${g.loading}</p>`}
        <footer>
          <button class="primary" @click=${this._copyDiagnostics}>${g.copy}</button>
          <button @click=${this._checkAgain}>${g.refresh}</button>
          <span class="muted">${g.privacy}</span>
        </footer>
      </main>
      ${this._toast?l`<div class="toast" role="status">${this._toast}</div>`:p}
      ${this._story?l`<homelab-wrapped-story
            .data=${this._story}
            .language=${this._language}
            @close=${this._closeStory}
          ></homelab-wrapped-story>`:p}
    `}_renderCard(r){let s=me[r.card];return l`
      <article class=${r.state}>
        <div class="top">
          <span class="number">${String(r.number).padStart(2,"0")}</span>
          <span class="chip">${g[r.state]}</span>
        </div>
        <h2>${s.title}</h2>
        <p class="about">${s.about}</p>
        <p class="status">${this._status(r)}</p>
        ${r.hints.map(i=>l`<p class="hint">${ge[i]}</p>`)}
      </article>
    `}_status(r){let s=r.card==="personality"||r.card==="summary";switch(r.state){case"ready":if(r.since){let i=g.since(this._date(r.since));return r.sources.length?`${i} \xB7 ${g.from(r.sources.join(", "))}`:i}return r.sources.length?g.from(r.sources.join(", ")):g.builtFromOthers;case"counting":{let i=[r.ready_on?g.readyOn(this._date(r.ready_on)):""];return r.since&&i.push(g.collectingSince(this._date(r.since))),i.filter(Boolean).join(" \xB7 ")}case"locked":return r.unlock.length?g.connect(new Intl.ListFormat(this._language,{type:"disjunction"}).format(r.unlock)):s?g.builtFromOthers:""}}static{this.styles=L`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--paper-font-body1_-_font-family, inherit);
    }
    .toolbar {
      display: flex;
      align-items: center;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color));
      font-size: 20px;
    }
    .title {
      margin-left: 12px;
    }
    main {
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px 16px 96px;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px 24px;
      margin-bottom: 20px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 500;
    }
    .count {
      margin: 0;
      color: var(--secondary-text-color);
      font-size: 18px;
    }
    .play {
      display: block;
      width: 100%;
      margin: 0 0 24px;
      padding: 20px 24px;
      border: 0;
      border-radius: var(--ha-card-border-radius, 12px);
      background: linear-gradient(135deg, #312e81, #6d28d9 55%, #be185d);
      color: #fff;
      font-size: 22px;
      font-weight: 700;
      text-align: left;
    }
    .play:disabled {
      opacity: 0.7;
      cursor: progress;
    }
    .years {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: -12px 0 24px;
    }
    .year {
      padding: 6px 16px;
      border: 1px solid var(--divider-color);
      border-radius: 999px;
      background: none;
      color: inherit;
      font: inherit;
      cursor: pointer;
    }
    .year.on {
      border-color: transparent;
      background: var(--primary-color);
      color: var(--text-primary-color);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }
    article {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 16px 18px;
      border-radius: var(--ha-card-border-radius, 12px);
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-left: 4px solid var(--state-color);
    }
    article.ready {
      --state-color: var(--success-color, #43a047);
    }
    article.counting {
      --state-color: var(--warning-color, #ffa600);
    }
    article.locked {
      --state-color: var(--disabled-text-color, #9e9e9e);
    }
    article.locked h2,
    article.locked .about {
      color: var(--secondary-text-color);
    }
    .top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .number {
      font-variant-numeric: tabular-nums;
      color: var(--secondary-text-color);
    }
    .chip {
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      color: var(--state-color);
      border: 1px solid var(--state-color);
    }
    h2 {
      margin: 4px 0 0;
      font-size: 20px;
      font-weight: 500;
    }
    p {
      margin: 0;
    }
    .about {
      color: var(--secondary-text-color);
    }
    .status {
      margin-top: auto;
      padding-top: 8px;
      font-size: 14px;
    }
    .hint {
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .muted {
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color, #db4437);
    }
    footer {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
      margin-top: 24px;
    }
    button {
      font: inherit;
      padding: 8px 16px;
      border-radius: 8px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      cursor: pointer;
    }
    button.primary {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
    .toast {
      position: fixed;
      left: 50%;
      bottom: 24px;
      transform: translateX(-50%);
      width: max-content;
      max-width: calc(100vw - 32px);
      box-sizing: border-box;
      padding: 12px 20px;
      border-radius: 8px;
      background: var(--primary-text-color);
      color: var(--primary-background-color);
    }
    @media (max-width: 600px) {
      main {
        padding-top: 16px;
      }
      h1 {
        font-size: 22px;
      }
      .grid {
        grid-template-columns: 1fr;
      }
    }
  `}};async function Gt(e){if(window.isSecureContext&&navigator.clipboard){await navigator.clipboard.writeText(e);return}let t=document.createElement("textarea");t.value=e,t.style.position="fixed",t.style.opacity="0",document.body.append(t),t.select();let r=document.execCommand("copy");if(t.remove(),!r)throw new Error("copy failed")}customElements.get("homelab-wrapped-panel")||customElements.define("homelab-wrapped-panel",_e);
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/lit-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directive.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directive-helpers.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directives/keyed.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
