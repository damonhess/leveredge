import{R as se,K as Me,L as ae,M as ce,N as oe,O as Ct,P as Ae,Q as Ot,T as Pt,a as Ie,s as Le,D as Ye,E as Fe,b as We,c as Ve,g as ot,d as pt,U as ze,V as Oe,W as Pe,e as Ne,X as Re,Y as Z,l as wt,Z as Ut,_ as Qt,$ as Be,a0 as He,a1 as Xe,a2 as Ge,a3 as Ze,a4 as je,a5 as qe,a6 as Kt,a7 as $t,a8 as Jt,a9 as te,aa as ee,k as Ue,j as Qe,F as Ke,C as $e}from"./index-BCFbJY_N.js";const Je=Math.PI/180,tn=180/Math.PI,_t=18,le=.96422,ue=1,de=.82521,fe=4/29,lt=6/29,he=3*lt*lt,en=lt*lt*lt;function me(t){if(t instanceof K)return new K(t.l,t.a,t.b,t.opacity);if(t instanceof tt)return ke(t);t instanceof se||(t=Me(t));var e=At(t.r),n=At(t.g),i=At(t.b),a=St((.2225045*e+.7168786*n+.0606169*i)/ue),h,o;return e===n&&n===i?h=o=a:(h=St((.4360747*e+.3850649*n+.1430804*i)/le),o=St((.0139322*e+.0971045*n+.7141733*i)/de)),new K(116*a-16,500*(h-a),200*(a-o),t.opacity)}function nn(t,e,n,i){return arguments.length===1?me(t):new K(t,e,n,i??1)}function K(t,e,n,i){this.l=+t,this.a=+e,this.b=+n,this.opacity=+i}ae(K,nn,ce(oe,{brighter(t){return new K(this.l+_t*(t??1),this.a,this.b,this.opacity)},darker(t){return new K(this.l-_t*(t??1),this.a,this.b,this.opacity)},rgb(){var t=(this.l+16)/116,e=isNaN(this.a)?t:t+this.a/500,n=isNaN(this.b)?t:t-this.b/200;return e=le*Et(e),t=ue*Et(t),n=de*Et(n),new se(Mt(3.1338561*e-1.6168667*t-.4906146*n),Mt(-.9787684*e+1.9161415*t+.033454*n),Mt(.0719453*e-.2289914*t+1.4052427*n),this.opacity)}}));function St(t){return t>en?Math.pow(t,1/3):t/he+fe}function Et(t){return t>lt?t*t*t:he*(t-fe)}function Mt(t){return 255*(t<=.0031308?12.92*t:1.055*Math.pow(t,1/2.4)-.055)}function At(t){return(t/=255)<=.04045?t/12.92:Math.pow((t+.055)/1.055,2.4)}function rn(t){if(t instanceof tt)return new tt(t.h,t.c,t.l,t.opacity);if(t instanceof K||(t=me(t)),t.a===0&&t.b===0)return new tt(NaN,0<t.l&&t.l<100?0:NaN,t.l,t.opacity);var e=Math.atan2(t.b,t.a)*tn;return new tt(e<0?e+360:e,Math.sqrt(t.a*t.a+t.b*t.b),t.l,t.opacity)}function Lt(t,e,n,i){return arguments.length===1?rn(t):new tt(t,e,n,i??1)}function tt(t,e,n,i){this.h=+t,this.c=+e,this.l=+n,this.opacity=+i}function ke(t){if(isNaN(t.h))return new K(t.l,0,0,t.opacity);var e=t.h*Je;return new K(t.l,Math.cos(e)*t.c,Math.sin(e)*t.c,t.opacity)}ae(tt,Lt,ce(oe,{brighter(t){return new tt(this.h,this.c,this.l+_t*(t??1),this.opacity)},darker(t){return new tt(this.h,this.c,this.l-_t*(t??1),this.opacity)},rgb(){return ke(this).rgb()}}));function sn(t){return function(e,n){var i=t((e=Lt(e)).h,(n=Lt(n)).h),a=Ct(e.c,n.c),h=Ct(e.l,n.l),o=Ct(e.opacity,n.opacity);return function(x){return e.h=i(x),e.c=a(x),e.l=h(x),e.opacity=o(x),e+""}}}const an=sn(Ae);function cn(t){return t}var vt=1,It=2,Yt=3,bt=4,ne=1e-6;function on(t){return"translate("+t+",0)"}function ln(t){return"translate(0,"+t+")"}function un(t){return e=>+t(e)}function dn(t,e){return e=Math.max(0,t.bandwidth()-e*2)/2,t.round()&&(e=Math.round(e)),n=>+t(n)+e}function fn(){return!this.__axis}function ye(t,e){var n=[],i=null,a=null,h=6,o=6,x=3,C=typeof window<"u"&&window.devicePixelRatio>1?0:.5,D=t===vt||t===bt?-1:1,p=t===bt||t===It?"x":"y",M=t===vt||t===Yt?on:ln;function _(b){var B=i??(e.ticks?e.ticks.apply(e,n):e.domain()),A=a??(e.tickFormat?e.tickFormat.apply(e,n):cn),T=Math.max(h,0)+x,S=e.range(),L=+S[0]+C,Y=+S[S.length-1]+C,N=(e.bandwidth?dn:un)(e.copy(),C),P=b.selection?b.selection():b,X=P.selectAll(".domain").data([null]),O=P.selectAll(".tick").data(B,e).order(),m=O.exit(),w=O.enter().append("g").attr("class","tick"),v=O.select("line"),k=O.select("text");X=X.merge(X.enter().insert("path",".tick").attr("class","domain").attr("stroke","currentColor")),O=O.merge(w),v=v.merge(w.append("line").attr("stroke","currentColor").attr(p+"2",D*h)),k=k.merge(w.append("text").attr("fill","currentColor").attr(p,D*T).attr("dy",t===vt?"0em":t===Yt?"0.71em":"0.32em")),b!==P&&(X=X.transition(b),O=O.transition(b),v=v.transition(b),k=k.transition(b),m=m.transition(b).attr("opacity",ne).attr("transform",function(r){return isFinite(r=N(r))?M(r+C):this.getAttribute("transform")}),w.attr("opacity",ne).attr("transform",function(r){var l=this.parentNode.__axis;return M((l&&isFinite(l=l(r))?l:N(r))+C)})),m.remove(),X.attr("d",t===bt||t===It?o?"M"+D*o+","+L+"H"+C+"V"+Y+"H"+D*o:"M"+C+","+L+"V"+Y:o?"M"+L+","+D*o+"V"+C+"H"+Y+"V"+D*o:"M"+L+","+C+"H"+Y),O.attr("opacity",1).attr("transform",function(r){return M(N(r)+C)}),v.attr(p+"2",D*h),k.attr(p,D*T).text(A),P.filter(fn).attr("fill","none").attr("font-size",10).attr("font-family","sans-serif").attr("text-anchor",t===It?"start":t===bt?"end":"middle"),P.each(function(){this.__axis=N})}return _.scale=function(b){return arguments.length?(e=b,_):e},_.ticks=function(){return n=Array.from(arguments),_},_.tickArguments=function(b){return arguments.length?(n=b==null?[]:Array.from(b),_):n.slice()},_.tickValues=function(b){return arguments.length?(i=b==null?null:Array.from(b),_):i&&i.slice()},_.tickFormat=function(b){return arguments.length?(a=b,_):a},_.tickSize=function(b){return arguments.length?(h=o=+b,_):h},_.tickSizeInner=function(b){return arguments.length?(h=+b,_):h},_.tickSizeOuter=function(b){return arguments.length?(o=+b,_):o},_.tickPadding=function(b){return arguments.length?(x=+b,_):x},_.offset=function(b){return arguments.length?(C=+b,_):C},_}function hn(t){return ye(vt,t)}function mn(t){return ye(Yt,t)}var ge={exports:{}};(function(t,e){(function(n,i){t.exports=i()})(Ot,function(){var n="day";return function(i,a,h){var o=function(D){return D.add(4-D.isoWeekday(),n)},x=a.prototype;x.isoWeekYear=function(){return o(this).year()},x.isoWeek=function(D){if(!this.$utils().u(D))return this.add(7*(D-this.isoWeek()),n);var p,M,_,b,B=o(this),A=(p=this.isoWeekYear(),M=this.$u,_=(M?h.utc:h)().year(p).startOf("year"),b=4-_.isoWeekday(),_.isoWeekday()>4&&(b+=7),_.add(b,n));return B.diff(A,"week")+1},x.isoWeekday=function(D){return this.$utils().u(D)?this.day()||7:this.day(this.day()%7?D:D-7)};var C=x.startOf;x.startOf=function(D,p){var M=this.$utils(),_=!!M.u(p)||p;return M.p(D)==="isoweek"?_?this.date(this.date()-(this.isoWeekday()-1)).startOf("day"):this.date(this.date()-1-(this.isoWeekday()-1)+7).endOf("day"):C.bind(this)(D,p)}}})})(ge);var kn=ge.exports;const yn=Pt(kn);var pe={exports:{}};(function(t,e){(function(n,i){t.exports=i()})(Ot,function(){var n={LTS:"h:mm:ss A",LT:"h:mm A",L:"MM/DD/YYYY",LL:"MMMM D, YYYY",LLL:"MMMM D, YYYY h:mm A",LLLL:"dddd, MMMM D, YYYY h:mm A"},i=/(\[[^[]*\])|([-_:/.,()\s]+)|(A|a|Q|YYYY|YY?|ww?|MM?M?M?|Do|DD?|hh?|HH?|mm?|ss?|S{1,3}|z|ZZ?)/g,a=/\d/,h=/\d\d/,o=/\d\d?/,x=/\d*[^-_:/,()\s\d]+/,C={},D=function(T){return(T=+T)+(T>68?1900:2e3)},p=function(T){return function(S){this[T]=+S}},M=[/[+-]\d\d:?(\d\d)?|Z/,function(T){(this.zone||(this.zone={})).offset=function(S){if(!S||S==="Z")return 0;var L=S.match(/([+-]|\d\d)/g),Y=60*L[1]+(+L[2]||0);return Y===0?0:L[0]==="+"?-Y:Y}(T)}],_=function(T){var S=C[T];return S&&(S.indexOf?S:S.s.concat(S.f))},b=function(T,S){var L,Y=C.meridiem;if(Y){for(var N=1;N<=24;N+=1)if(T.indexOf(Y(N,0,S))>-1){L=N>12;break}}else L=T===(S?"pm":"PM");return L},B={A:[x,function(T){this.afternoon=b(T,!1)}],a:[x,function(T){this.afternoon=b(T,!0)}],Q:[a,function(T){this.month=3*(T-1)+1}],S:[a,function(T){this.milliseconds=100*+T}],SS:[h,function(T){this.milliseconds=10*+T}],SSS:[/\d{3}/,function(T){this.milliseconds=+T}],s:[o,p("seconds")],ss:[o,p("seconds")],m:[o,p("minutes")],mm:[o,p("minutes")],H:[o,p("hours")],h:[o,p("hours")],HH:[o,p("hours")],hh:[o,p("hours")],D:[o,p("day")],DD:[h,p("day")],Do:[x,function(T){var S=C.ordinal,L=T.match(/\d+/);if(this.day=L[0],S)for(var Y=1;Y<=31;Y+=1)S(Y).replace(/\[|\]/g,"")===T&&(this.day=Y)}],w:[o,p("week")],ww:[h,p("week")],M:[o,p("month")],MM:[h,p("month")],MMM:[x,function(T){var S=_("months"),L=(_("monthsShort")||S.map(function(Y){return Y.slice(0,3)})).indexOf(T)+1;if(L<1)throw new Error;this.month=L%12||L}],MMMM:[x,function(T){var S=_("months").indexOf(T)+1;if(S<1)throw new Error;this.month=S%12||S}],Y:[/[+-]?\d+/,p("year")],YY:[h,function(T){this.year=D(T)}],YYYY:[/\d{4}/,p("year")],Z:M,ZZ:M};function A(T){var S,L;S=T,L=C&&C.formats;for(var Y=(T=S.replace(/(\[[^\]]+])|(LTS?|l{1,4}|L{1,4})/g,function(v,k,r){var l=r&&r.toUpperCase();return k||L[r]||n[r]||L[l].replace(/(\[[^\]]+])|(MMMM|MM|DD|dddd)/g,function(f,c,g){return c||g.slice(1)})})).match(i),N=Y.length,P=0;P<N;P+=1){var X=Y[P],O=B[X],m=O&&O[0],w=O&&O[1];Y[P]=w?{regex:m,parser:w}:X.replace(/^\[|\]$/g,"")}return function(v){for(var k={},r=0,l=0;r<N;r+=1){var f=Y[r];if(typeof f=="string")l+=f.length;else{var c=f.regex,g=f.parser,s=v.slice(l),z=c.exec(s)[0];g.call(k,z),v=v.replace(z,"")}}return function(d){var u=d.afternoon;if(u!==void 0){var y=d.hours;u?y<12&&(d.hours+=12):y===12&&(d.hours=0),delete d.afternoon}}(k),k}}return function(T,S,L){L.p.customParseFormat=!0,T&&T.parseTwoDigitYear&&(D=T.parseTwoDigitYear);var Y=S.prototype,N=Y.parse;Y.parse=function(P){var X=P.date,O=P.utc,m=P.args;this.$u=O;var w=m[1];if(typeof w=="string"){var v=m[2]===!0,k=m[3]===!0,r=v||k,l=m[2];k&&(l=m[2]),C=this.$locale(),!v&&l&&(C=L.Ls[l]),this.$d=function(s,z,d,u){try{if(["x","X"].indexOf(z)>-1)return new Date((z==="X"?1e3:1)*s);var y=A(z)(s),V=y.year,E=y.month,F=y.day,I=y.hours,W=y.minutes,rt=y.seconds,st=y.milliseconds,kt=y.zone,yt=y.week,H=new Date,q=F||(V||E?1:H.getDate()),G=V||H.getFullYear(),et=0;V&&!E||(et=E>0?E-1:H.getMonth());var U,nt=I||0,j=W||0,ct=rt||0,it=st||0;return kt?new Date(Date.UTC(G,et,q,nt,j,ct,it+60*kt.offset*1e3)):d?new Date(Date.UTC(G,et,q,nt,j,ct,it)):(U=new Date(G,et,q,nt,j,ct,it),yt&&(U=u(U).week(yt).toDate()),U)}catch{return new Date("")}}(X,w,O,L),this.init(),l&&l!==!0&&(this.$L=this.locale(l).$L),r&&X!=this.format(w)&&(this.$d=new Date("")),C={}}else if(w instanceof Array)for(var f=w.length,c=1;c<=f;c+=1){m[1]=w[c-1];var g=L.apply(this,m);if(g.isValid()){this.$d=g.$d,this.$L=g.$L,this.init();break}c===f&&(this.$d=new Date(""))}else N.call(this,P)}}})})(pe);var gn=pe.exports;const pn=Pt(gn);var be={exports:{}};(function(t,e){(function(n,i){t.exports=i()})(Ot,function(){return function(n,i){var a=i.prototype,h=a.format;a.format=function(o){var x=this,C=this.$locale();if(!this.isValid())return h.bind(this)(o);var D=this.$utils(),p=(o||"YYYY-MM-DDTHH:mm:ssZ").replace(/\[([^\]]+)]|Q|wo|ww|w|WW|W|zzz|z|gggg|GGGG|Do|X|x|k{1,2}|S/g,function(M){switch(M){case"Q":return Math.ceil((x.$M+1)/3);case"Do":return C.ordinal(x.$D);case"gggg":return x.weekYear();case"GGGG":return x.isoWeekYear();case"wo":return C.ordinal(x.week(),"W");case"w":case"ww":return D.s(x.week(),M==="w"?1:2,"0");case"W":case"WW":return D.s(x.isoWeek(),M==="W"?1:2,"0");case"k":case"kk":return D.s(String(x.$H===0?24:x.$H),M==="k"?1:2,"0");case"X":return Math.floor(x.$d.getTime()/1e3);case"x":return x.$d.getTime();case"z":return"["+x.offsetName()+"]";case"zzz":return"["+x.offsetName("long")+"]";default:return M}});return h.bind(this)(p)}}})})(be);var bn=be.exports;const vn=Pt(bn);var Ft=function(){var t=function(k,r,l,f){for(l=l||{},f=k.length;f--;l[k[f]]=r);return l},e=[6,8,10,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,30,32,33,35,37],n=[1,25],i=[1,26],a=[1,27],h=[1,28],o=[1,29],x=[1,30],C=[1,31],D=[1,9],p=[1,10],M=[1,11],_=[1,12],b=[1,13],B=[1,14],A=[1,15],T=[1,16],S=[1,18],L=[1,19],Y=[1,20],N=[1,21],P=[1,22],X=[1,24],O=[1,32],m={trace:function(){},yy:{},symbols_:{error:2,start:3,gantt:4,document:5,EOF:6,line:7,SPACE:8,statement:9,NL:10,weekday:11,weekday_monday:12,weekday_tuesday:13,weekday_wednesday:14,weekday_thursday:15,weekday_friday:16,weekday_saturday:17,weekday_sunday:18,dateFormat:19,inclusiveEndDates:20,topAxis:21,axisFormat:22,tickInterval:23,excludes:24,includes:25,todayMarker:26,title:27,acc_title:28,acc_title_value:29,acc_descr:30,acc_descr_value:31,acc_descr_multiline_value:32,section:33,clickStatement:34,taskTxt:35,taskData:36,click:37,callbackname:38,callbackargs:39,href:40,clickStatementDebug:41,$accept:0,$end:1},terminals_:{2:"error",4:"gantt",6:"EOF",8:"SPACE",10:"NL",12:"weekday_monday",13:"weekday_tuesday",14:"weekday_wednesday",15:"weekday_thursday",16:"weekday_friday",17:"weekday_saturday",18:"weekday_sunday",19:"dateFormat",20:"inclusiveEndDates",21:"topAxis",22:"axisFormat",23:"tickInterval",24:"excludes",25:"includes",26:"todayMarker",27:"title",28:"acc_title",29:"acc_title_value",30:"acc_descr",31:"acc_descr_value",32:"acc_descr_multiline_value",33:"section",35:"taskTxt",36:"taskData",37:"click",38:"callbackname",39:"callbackargs",40:"href"},productions_:[0,[3,3],[5,0],[5,2],[7,2],[7,1],[7,1],[7,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,2],[9,2],[9,1],[9,1],[9,1],[9,2],[34,2],[34,3],[34,3],[34,4],[34,3],[34,4],[34,2],[41,2],[41,3],[41,3],[41,4],[41,3],[41,4],[41,2]],performAction:function(r,l,f,c,g,s,z){var d=s.length-1;switch(g){case 1:return s[d-1];case 2:this.$=[];break;case 3:s[d-1].push(s[d]),this.$=s[d-1];break;case 4:case 5:this.$=s[d];break;case 6:case 7:this.$=[];break;case 8:c.setWeekday("monday");break;case 9:c.setWeekday("tuesday");break;case 10:c.setWeekday("wednesday");break;case 11:c.setWeekday("thursday");break;case 12:c.setWeekday("friday");break;case 13:c.setWeekday("saturday");break;case 14:c.setWeekday("sunday");break;case 15:c.setDateFormat(s[d].substr(11)),this.$=s[d].substr(11);break;case 16:c.enableInclusiveEndDates(),this.$=s[d].substr(18);break;case 17:c.TopAxis(),this.$=s[d].substr(8);break;case 18:c.setAxisFormat(s[d].substr(11)),this.$=s[d].substr(11);break;case 19:c.setTickInterval(s[d].substr(13)),this.$=s[d].substr(13);break;case 20:c.setExcludes(s[d].substr(9)),this.$=s[d].substr(9);break;case 21:c.setIncludes(s[d].substr(9)),this.$=s[d].substr(9);break;case 22:c.setTodayMarker(s[d].substr(12)),this.$=s[d].substr(12);break;case 24:c.setDiagramTitle(s[d].substr(6)),this.$=s[d].substr(6);break;case 25:this.$=s[d].trim(),c.setAccTitle(this.$);break;case 26:case 27:this.$=s[d].trim(),c.setAccDescription(this.$);break;case 28:c.addSection(s[d].substr(8)),this.$=s[d].substr(8);break;case 30:c.addTask(s[d-1],s[d]),this.$="task";break;case 31:this.$=s[d-1],c.setClickEvent(s[d-1],s[d],null);break;case 32:this.$=s[d-2],c.setClickEvent(s[d-2],s[d-1],s[d]);break;case 33:this.$=s[d-2],c.setClickEvent(s[d-2],s[d-1],null),c.setLink(s[d-2],s[d]);break;case 34:this.$=s[d-3],c.setClickEvent(s[d-3],s[d-2],s[d-1]),c.setLink(s[d-3],s[d]);break;case 35:this.$=s[d-2],c.setClickEvent(s[d-2],s[d],null),c.setLink(s[d-2],s[d-1]);break;case 36:this.$=s[d-3],c.setClickEvent(s[d-3],s[d-1],s[d]),c.setLink(s[d-3],s[d-2]);break;case 37:this.$=s[d-1],c.setLink(s[d-1],s[d]);break;case 38:case 44:this.$=s[d-1]+" "+s[d];break;case 39:case 40:case 42:this.$=s[d-2]+" "+s[d-1]+" "+s[d];break;case 41:case 43:this.$=s[d-3]+" "+s[d-2]+" "+s[d-1]+" "+s[d];break}},table:[{3:1,4:[1,2]},{1:[3]},t(e,[2,2],{5:3}),{6:[1,4],7:5,8:[1,6],9:7,10:[1,8],11:17,12:n,13:i,14:a,15:h,16:o,17:x,18:C,19:D,20:p,21:M,22:_,23:b,24:B,25:A,26:T,27:S,28:L,30:Y,32:N,33:P,34:23,35:X,37:O},t(e,[2,7],{1:[2,1]}),t(e,[2,3]),{9:33,11:17,12:n,13:i,14:a,15:h,16:o,17:x,18:C,19:D,20:p,21:M,22:_,23:b,24:B,25:A,26:T,27:S,28:L,30:Y,32:N,33:P,34:23,35:X,37:O},t(e,[2,5]),t(e,[2,6]),t(e,[2,15]),t(e,[2,16]),t(e,[2,17]),t(e,[2,18]),t(e,[2,19]),t(e,[2,20]),t(e,[2,21]),t(e,[2,22]),t(e,[2,23]),t(e,[2,24]),{29:[1,34]},{31:[1,35]},t(e,[2,27]),t(e,[2,28]),t(e,[2,29]),{36:[1,36]},t(e,[2,8]),t(e,[2,9]),t(e,[2,10]),t(e,[2,11]),t(e,[2,12]),t(e,[2,13]),t(e,[2,14]),{38:[1,37],40:[1,38]},t(e,[2,4]),t(e,[2,25]),t(e,[2,26]),t(e,[2,30]),t(e,[2,31],{39:[1,39],40:[1,40]}),t(e,[2,37],{38:[1,41]}),t(e,[2,32],{40:[1,42]}),t(e,[2,33]),t(e,[2,35],{39:[1,43]}),t(e,[2,34]),t(e,[2,36])],defaultActions:{},parseError:function(r,l){if(l.recoverable)this.trace(r);else{var f=new Error(r);throw f.hash=l,f}},parse:function(r){var l=this,f=[0],c=[],g=[null],s=[],z=this.table,d="",u=0,y=0,V=2,E=1,F=s.slice.call(arguments,1),I=Object.create(this.lexer),W={yy:{}};for(var rt in this.yy)Object.prototype.hasOwnProperty.call(this.yy,rt)&&(W.yy[rt]=this.yy[rt]);I.setInput(r,W.yy),W.yy.lexer=I,W.yy.parser=this,typeof I.yylloc>"u"&&(I.yylloc={});var st=I.yylloc;s.push(st);var kt=I.options&&I.options.ranges;typeof W.yy.parseError=="function"?this.parseError=W.yy.parseError:this.parseError=Object.getPrototypeOf(this).parseError;function yt(){var $;return $=c.pop()||I.lex()||E,typeof $!="number"&&($ instanceof Array&&(c=$,$=c.pop()),$=l.symbols_[$]||$),$}for(var H,q,G,et,U={},nt,j,ct,it;;){if(q=f[f.length-1],this.defaultActions[q]?G=this.defaultActions[q]:((H===null||typeof H>"u")&&(H=yt()),G=z[q]&&z[q][H]),typeof G>"u"||!G.length||!G[0]){var gt="";it=[];for(nt in z[q])this.terminals_[nt]&&nt>V&&it.push("'"+this.terminals_[nt]+"'");I.showPosition?gt="Parse error on line "+(u+1)+`:
`+I.showPosition()+`
Expecting `+it.join(", ")+", got '"+(this.terminals_[H]||H)+"'":gt="Parse error on line "+(u+1)+": Unexpected "+(H==E?"end of input":"'"+(this.terminals_[H]||H)+"'"),this.parseError(gt,{text:I.match,token:this.terminals_[H]||H,line:I.yylineno,loc:st,expected:it})}if(G[0]instanceof Array&&G.length>1)throw new Error("Parse Error: multiple actions possible at state: "+q+", token: "+H);switch(G[0]){case 1:f.push(H),g.push(I.yytext),s.push(I.yylloc),f.push(G[1]),H=null,y=I.yyleng,d=I.yytext,u=I.yylineno,st=I.yylloc;break;case 2:if(j=this.productions_[G[1]][1],U.$=g[g.length-j],U._$={first_line:s[s.length-(j||1)].first_line,last_line:s[s.length-1].last_line,first_column:s[s.length-(j||1)].first_column,last_column:s[s.length-1].last_column},kt&&(U._$.range=[s[s.length-(j||1)].range[0],s[s.length-1].range[1]]),et=this.performAction.apply(U,[d,y,u,W.yy,G[1],g,s].concat(F)),typeof et<"u")return et;j&&(f=f.slice(0,-1*j*2),g=g.slice(0,-1*j),s=s.slice(0,-1*j)),f.push(this.productions_[G[1]][0]),g.push(U.$),s.push(U._$),ct=z[f[f.length-2]][f[f.length-1]],f.push(ct);break;case 3:return!0}}return!0}},w=function(){var k={EOF:1,parseError:function(l,f){if(this.yy.parser)this.yy.parser.parseError(l,f);else throw new Error(l)},setInput:function(r,l){return this.yy=l||this.yy||{},this._input=r,this._more=this._backtrack=this.done=!1,this.yylineno=this.yyleng=0,this.yytext=this.matched=this.match="",this.conditionStack=["INITIAL"],this.yylloc={first_line:1,first_column:0,last_line:1,last_column:0},this.options.ranges&&(this.yylloc.range=[0,0]),this.offset=0,this},input:function(){var r=this._input[0];this.yytext+=r,this.yyleng++,this.offset++,this.match+=r,this.matched+=r;var l=r.match(/(?:\r\n?|\n).*/g);return l?(this.yylineno++,this.yylloc.last_line++):this.yylloc.last_column++,this.options.ranges&&this.yylloc.range[1]++,this._input=this._input.slice(1),r},unput:function(r){var l=r.length,f=r.split(/(?:\r\n?|\n)/g);this._input=r+this._input,this.yytext=this.yytext.substr(0,this.yytext.length-l),this.offset-=l;var c=this.match.split(/(?:\r\n?|\n)/g);this.match=this.match.substr(0,this.match.length-1),this.matched=this.matched.substr(0,this.matched.length-1),f.length-1&&(this.yylineno-=f.length-1);var g=this.yylloc.range;return this.yylloc={first_line:this.yylloc.first_line,last_line:this.yylineno+1,first_column:this.yylloc.first_column,last_column:f?(f.length===c.length?this.yylloc.first_column:0)+c[c.length-f.length].length-f[0].length:this.yylloc.first_column-l},this.options.ranges&&(this.yylloc.range=[g[0],g[0]+this.yyleng-l]),this.yyleng=this.yytext.length,this},more:function(){return this._more=!0,this},reject:function(){if(this.options.backtrack_lexer)this._backtrack=!0;else return this.parseError("Lexical error on line "+(this.yylineno+1)+`. You can only invoke reject() in the lexer when the lexer is of the backtracking persuasion (options.backtrack_lexer = true).
`+this.showPosition(),{text:"",token:null,line:this.yylineno});return this},less:function(r){this.unput(this.match.slice(r))},pastInput:function(){var r=this.matched.substr(0,this.matched.length-this.match.length);return(r.length>20?"...":"")+r.substr(-20).replace(/\n/g,"")},upcomingInput:function(){var r=this.match;return r.length<20&&(r+=this._input.substr(0,20-r.length)),(r.substr(0,20)+(r.length>20?"...":"")).replace(/\n/g,"")},showPosition:function(){var r=this.pastInput(),l=new Array(r.length+1).join("-");return r+this.upcomingInput()+`
`+l+"^"},test_match:function(r,l){var f,c,g;if(this.options.backtrack_lexer&&(g={yylineno:this.yylineno,yylloc:{first_line:this.yylloc.first_line,last_line:this.last_line,first_column:this.yylloc.first_column,last_column:this.yylloc.last_column},yytext:this.yytext,match:this.match,matches:this.matches,matched:this.matched,yyleng:this.yyleng,offset:this.offset,_more:this._more,_input:this._input,yy:this.yy,conditionStack:this.conditionStack.slice(0),done:this.done},this.options.ranges&&(g.yylloc.range=this.yylloc.range.slice(0))),c=r[0].match(/(?:\r\n?|\n).*/g),c&&(this.yylineno+=c.length),this.yylloc={first_line:this.yylloc.last_line,last_line:this.yylineno+1,first_column:this.yylloc.last_column,last_column:c?c[c.length-1].length-c[c.length-1].match(/\r?\n?/)[0].length:this.yylloc.last_column+r[0].length},this.yytext+=r[0],this.match+=r[0],this.matches=r,this.yyleng=this.yytext.length,this.options.ranges&&(this.yylloc.range=[this.offset,this.offset+=this.yyleng]),this._more=!1,this._backtrack=!1,this._input=this._input.slice(r[0].length),this.matched+=r[0],f=this.performAction.call(this,this.yy,this,l,this.conditionStack[this.conditionStack.length-1]),this.done&&this._input&&(this.done=!1),f)return f;if(this._backtrack){for(var s in g)this[s]=g[s];return!1}return!1},next:function(){if(this.done)return this.EOF;this._input||(this.done=!0);var r,l,f,c;this._more||(this.yytext="",this.match="");for(var g=this._currentRules(),s=0;s<g.length;s++)if(f=this._input.match(this.rules[g[s]]),f&&(!l||f[0].length>l[0].length)){if(l=f,c=s,this.options.backtrack_lexer){if(r=this.test_match(f,g[s]),r!==!1)return r;if(this._backtrack){l=!1;continue}else return!1}else if(!this.options.flex)break}return l?(r=this.test_match(l,g[c]),r!==!1?r:!1):this._input===""?this.EOF:this.parseError("Lexical error on line "+(this.yylineno+1)+`. Unrecognized text.
`+this.showPosition(),{text:"",token:null,line:this.yylineno})},lex:function(){var l=this.next();return l||this.lex()},begin:function(l){this.conditionStack.push(l)},popState:function(){var l=this.conditionStack.length-1;return l>0?this.conditionStack.pop():this.conditionStack[0]},_currentRules:function(){return this.conditionStack.length&&this.conditionStack[this.conditionStack.length-1]?this.conditions[this.conditionStack[this.conditionStack.length-1]].rules:this.conditions.INITIAL.rules},topState:function(l){return l=this.conditionStack.length-1-Math.abs(l||0),l>=0?this.conditionStack[l]:"INITIAL"},pushState:function(l){this.begin(l)},stateStackSize:function(){return this.conditionStack.length},options:{"case-insensitive":!0},performAction:function(l,f,c,g){switch(c){case 0:return this.begin("open_directive"),"open_directive";case 1:return this.begin("acc_title"),28;case 2:return this.popState(),"acc_title_value";case 3:return this.begin("acc_descr"),30;case 4:return this.popState(),"acc_descr_value";case 5:this.begin("acc_descr_multiline");break;case 6:this.popState();break;case 7:return"acc_descr_multiline_value";case 8:break;case 9:break;case 10:break;case 11:return 10;case 12:break;case 13:break;case 14:this.begin("href");break;case 15:this.popState();break;case 16:return 40;case 17:this.begin("callbackname");break;case 18:this.popState();break;case 19:this.popState(),this.begin("callbackargs");break;case 20:return 38;case 21:this.popState();break;case 22:return 39;case 23:this.begin("click");break;case 24:this.popState();break;case 25:return 37;case 26:return 4;case 27:return 19;case 28:return 20;case 29:return 21;case 30:return 22;case 31:return 23;case 32:return 25;case 33:return 24;case 34:return 26;case 35:return 12;case 36:return 13;case 37:return 14;case 38:return 15;case 39:return 16;case 40:return 17;case 41:return 18;case 42:return"date";case 43:return 27;case 44:return"accDescription";case 45:return 33;case 46:return 35;case 47:return 36;case 48:return":";case 49:return 6;case 50:return"INVALID"}},rules:[/^(?:%%\{)/i,/^(?:accTitle\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*\{\s*)/i,/^(?:[\}])/i,/^(?:[^\}]*)/i,/^(?:%%(?!\{)*[^\n]*)/i,/^(?:[^\}]%%*[^\n]*)/i,/^(?:%%*[^\n]*[\n]*)/i,/^(?:[\n]+)/i,/^(?:\s+)/i,/^(?:%[^\n]*)/i,/^(?:href[\s]+["])/i,/^(?:["])/i,/^(?:[^"]*)/i,/^(?:call[\s]+)/i,/^(?:\([\s]*\))/i,/^(?:\()/i,/^(?:[^(]*)/i,/^(?:\))/i,/^(?:[^)]*)/i,/^(?:click[\s]+)/i,/^(?:[\s\n])/i,/^(?:[^\s\n]*)/i,/^(?:gantt\b)/i,/^(?:dateFormat\s[^#\n;]+)/i,/^(?:inclusiveEndDates\b)/i,/^(?:topAxis\b)/i,/^(?:axisFormat\s[^#\n;]+)/i,/^(?:tickInterval\s[^#\n;]+)/i,/^(?:includes\s[^#\n;]+)/i,/^(?:excludes\s[^#\n;]+)/i,/^(?:todayMarker\s[^\n;]+)/i,/^(?:weekday\s+monday\b)/i,/^(?:weekday\s+tuesday\b)/i,/^(?:weekday\s+wednesday\b)/i,/^(?:weekday\s+thursday\b)/i,/^(?:weekday\s+friday\b)/i,/^(?:weekday\s+saturday\b)/i,/^(?:weekday\s+sunday\b)/i,/^(?:\d\d\d\d-\d\d-\d\d\b)/i,/^(?:title\s[^\n]+)/i,/^(?:accDescription\s[^#\n;]+)/i,/^(?:section\s[^\n]+)/i,/^(?:[^:\n]+)/i,/^(?::[^#\n;]+)/i,/^(?::)/i,/^(?:$)/i,/^(?:.)/i],conditions:{acc_descr_multiline:{rules:[6,7],inclusive:!1},acc_descr:{rules:[4],inclusive:!1},acc_title:{rules:[2],inclusive:!1},callbackargs:{rules:[21,22],inclusive:!1},callbackname:{rules:[18,19,20],inclusive:!1},href:{rules:[15,16],inclusive:!1},click:{rules:[24,25],inclusive:!1},INITIAL:{rules:[0,1,3,5,8,9,10,11,12,13,14,17,23,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50],inclusive:!0}}};return k}();m.lexer=w;function v(){this.yy={}}return v.prototype=m,m.Parser=v,new v}();Ft.parser=Ft;const xn=Ft;Z.extend(yn);Z.extend(pn);Z.extend(vn);let Q="",Nt="",Rt,Bt="",ft=[],ht=[],Ht={},Xt=[],Dt=[],dt="",Gt="";const ve=["active","done","crit","milestone"];let Zt=[],mt=!1,jt=!1,qt="sunday",Wt=0;const Tn=function(){Xt=[],Dt=[],dt="",Zt=[],xt=0,zt=void 0,Tt=void 0,R=[],Q="",Nt="",Gt="",Rt=void 0,Bt="",ft=[],ht=[],mt=!1,jt=!1,Wt=0,Ht={},Ke(),qt="sunday"},wn=function(t){Nt=t},_n=function(){return Nt},Dn=function(t){Rt=t},Cn=function(){return Rt},Sn=function(t){Bt=t},En=function(){return Bt},Mn=function(t){Q=t},An=function(){mt=!0},In=function(){return mt},Ln=function(){jt=!0},Yn=function(){return jt},Fn=function(t){Gt=t},Wn=function(){return Gt},Vn=function(){return Q},zn=function(t){ft=t.toLowerCase().split(/[\s,]+/)},On=function(){return ft},Pn=function(t){ht=t.toLowerCase().split(/[\s,]+/)},Nn=function(){return ht},Rn=function(){return Ht},Bn=function(t){dt=t,Xt.push(t)},Hn=function(){return Xt},Xn=function(){let t=ie();const e=10;let n=0;for(;!t&&n<e;)t=ie(),n++;return Dt=R,Dt},xe=function(t,e,n,i){return i.includes(t.format(e.trim()))?!1:t.isoWeekday()>=6&&n.includes("weekends")||n.includes(t.format("dddd").toLowerCase())?!0:n.includes(t.format(e.trim()))},Gn=function(t){qt=t},Zn=function(){return qt},Te=function(t,e,n,i){if(!n.length||t.manualEndTime)return;let a;t.startTime instanceof Date?a=Z(t.startTime):a=Z(t.startTime,e,!0),a=a.add(1,"d");let h;t.endTime instanceof Date?h=Z(t.endTime):h=Z(t.endTime,e,!0);const[o,x]=jn(a,h,e,n,i);t.endTime=o.toDate(),t.renderEndTime=x},jn=function(t,e,n,i,a){let h=!1,o=null;for(;t<=e;)h||(o=e.toDate()),h=xe(t,n,i,a),h&&(e=e.add(1,"d")),t=t.add(1,"d");return[e,o]},Vt=function(t,e,n){n=n.trim();const a=/^after\s+(?<ids>[\d\w- ]+)/.exec(n);if(a!==null){let o=null;for(const C of a.groups.ids.split(" ")){let D=at(C);D!==void 0&&(!o||D.endTime>o.endTime)&&(o=D)}if(o)return o.endTime;const x=new Date;return x.setHours(0,0,0,0),x}let h=Z(n,e.trim(),!0);if(h.isValid())return h.toDate();{wt.debug("Invalid date:"+n),wt.debug("With date format:"+e.trim());const o=new Date(n);if(o===void 0||isNaN(o.getTime())||o.getFullYear()<-1e4||o.getFullYear()>1e4)throw new Error("Invalid date:"+n);return o}},we=function(t){const e=/^(\d+(?:\.\d+)?)([Mdhmswy]|ms)$/.exec(t.trim());return e!==null?[Number.parseFloat(e[1]),e[2]]:[NaN,"ms"]},_e=function(t,e,n,i=!1){n=n.trim();const h=/^until\s+(?<ids>[\d\w- ]+)/.exec(n);if(h!==null){let p=null;for(const _ of h.groups.ids.split(" ")){let b=at(_);b!==void 0&&(!p||b.startTime<p.startTime)&&(p=b)}if(p)return p.startTime;const M=new Date;return M.setHours(0,0,0,0),M}let o=Z(n,e.trim(),!0);if(o.isValid())return i&&(o=o.add(1,"d")),o.toDate();let x=Z(t);const[C,D]=we(n);if(!Number.isNaN(C)){const p=x.add(C,D);p.isValid()&&(x=p)}return x.toDate()};let xt=0;const ut=function(t){return t===void 0?(xt=xt+1,"task"+xt):t},qn=function(t,e){let n;e.substr(0,1)===":"?n=e.substr(1,e.length):n=e;const i=n.split(","),a={};Ee(i,a,ve);for(let o=0;o<i.length;o++)i[o]=i[o].trim();let h="";switch(i.length){case 1:a.id=ut(),a.startTime=t.endTime,h=i[0];break;case 2:a.id=ut(),a.startTime=Vt(void 0,Q,i[0]),h=i[1];break;case 3:a.id=ut(i[0]),a.startTime=Vt(void 0,Q,i[1]),h=i[2];break}return h&&(a.endTime=_e(a.startTime,Q,h,mt),a.manualEndTime=Z(h,"YYYY-MM-DD",!0).isValid(),Te(a,Q,ht,ft)),a},Un=function(t,e){let n;e.substr(0,1)===":"?n=e.substr(1,e.length):n=e;const i=n.split(","),a={};Ee(i,a,ve);for(let h=0;h<i.length;h++)i[h]=i[h].trim();switch(i.length){case 1:a.id=ut(),a.startTime={type:"prevTaskEnd",id:t},a.endTime={data:i[0]};break;case 2:a.id=ut(),a.startTime={type:"getStartDate",startData:i[0]},a.endTime={data:i[1]};break;case 3:a.id=ut(i[0]),a.startTime={type:"getStartDate",startData:i[1]},a.endTime={data:i[2]};break}return a};let zt,Tt,R=[];const De={},Qn=function(t,e){const n={section:dt,type:dt,processed:!1,manualEndTime:!1,renderEndTime:null,raw:{data:e},task:t,classes:[]},i=Un(Tt,e);n.raw.startTime=i.startTime,n.raw.endTime=i.endTime,n.id=i.id,n.prevTaskId=Tt,n.active=i.active,n.done=i.done,n.crit=i.crit,n.milestone=i.milestone,n.order=Wt,Wt++;const a=R.push(n);Tt=n.id,De[n.id]=a-1},at=function(t){const e=De[t];return R[e]},Kn=function(t,e){const n={section:dt,type:dt,description:t,task:t,classes:[]},i=qn(zt,e);n.startTime=i.startTime,n.endTime=i.endTime,n.id=i.id,n.active=i.active,n.done=i.done,n.crit=i.crit,n.milestone=i.milestone,zt=n,Dt.push(n)},ie=function(){const t=function(n){const i=R[n];let a="";switch(R[n].raw.startTime.type){case"prevTaskEnd":{const h=at(i.prevTaskId);i.startTime=h.endTime;break}case"getStartDate":a=Vt(void 0,Q,R[n].raw.startTime.startData),a&&(R[n].startTime=a);break}return R[n].startTime&&(R[n].endTime=_e(R[n].startTime,Q,R[n].raw.endTime.data,mt),R[n].endTime&&(R[n].processed=!0,R[n].manualEndTime=Z(R[n].raw.endTime.data,"YYYY-MM-DD",!0).isValid(),Te(R[n],Q,ht,ft))),R[n].processed};let e=!0;for(const[n,i]of R.entries())t(n),e=e&&i.processed;return e},$n=function(t,e){let n=e;ot().securityLevel!=="loose"&&(n=Qe.sanitizeUrl(e)),t.split(",").forEach(function(i){at(i)!==void 0&&(Se(i,()=>{window.open(n,"_self")}),Ht[i]=n)}),Ce(t,"clickable")},Ce=function(t,e){t.split(",").forEach(function(n){let i=at(n);i!==void 0&&i.classes.push(e)})},Jn=function(t,e,n){if(ot().securityLevel!=="loose"||e===void 0)return;let i=[];if(typeof n=="string"){i=n.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);for(let h=0;h<i.length;h++){let o=i[h].trim();o.charAt(0)==='"'&&o.charAt(o.length-1)==='"'&&(o=o.substr(1,o.length-2)),i[h]=o}}i.length===0&&i.push(t),at(t)!==void 0&&Se(t,()=>{$e.runFunc(e,...i)})},Se=function(t,e){Zt.push(function(){const n=document.querySelector(`[id="${t}"]`);n!==null&&n.addEventListener("click",function(){e()})},function(){const n=document.querySelector(`[id="${t}-text"]`);n!==null&&n.addEventListener("click",function(){e()})})},ti=function(t,e,n){t.split(",").forEach(function(i){Jn(i,e,n)}),Ce(t,"clickable")},ei=function(t){Zt.forEach(function(e){e(t)})},ni={getConfig:()=>ot().gantt,clear:Tn,setDateFormat:Mn,getDateFormat:Vn,enableInclusiveEndDates:An,endDatesAreInclusive:In,enableTopAxis:Ln,topAxisEnabled:Yn,setAxisFormat:wn,getAxisFormat:_n,setTickInterval:Dn,getTickInterval:Cn,setTodayMarker:Sn,getTodayMarker:En,setAccTitle:Ve,getAccTitle:We,setDiagramTitle:Fe,getDiagramTitle:Ye,setDisplayMode:Fn,getDisplayMode:Wn,setAccDescription:Le,getAccDescription:Ie,addSection:Bn,getSections:Hn,getTasks:Xn,addTask:Qn,findTaskById:at,addTaskOrg:Kn,setIncludes:zn,getIncludes:On,setExcludes:Pn,getExcludes:Nn,setClickEvent:ti,setLink:$n,getLinks:Rn,bindFunctions:ei,parseDuration:we,isInvalidDate:xe,setWeekday:Gn,getWeekday:Zn};function Ee(t,e,n){let i=!0;for(;i;)i=!1,n.forEach(function(a){const h="^\\s*"+a+"\\s*$",o=new RegExp(h);t[0].match(o)&&(e[a]=!0,t.shift(1),i=!0)})}const ii=function(){wt.debug("Something is calling, setConf, remove the call")},re={monday:qe,tuesday:je,wednesday:Ze,thursday:Ge,friday:Xe,saturday:He,sunday:Be},ri=(t,e)=>{let n=[...t].map(()=>-1/0),i=[...t].sort((h,o)=>h.startTime-o.startTime||h.order-o.order),a=0;for(const h of i)for(let o=0;o<n.length;o++)if(h.startTime>=n[o]){n[o]=h.endTime,h.order=o+e,o>a&&(a=o);break}return a};let J;const si=function(t,e,n,i){const a=ot().gantt,h=ot().securityLevel;let o;h==="sandbox"&&(o=pt("#i"+e));const x=h==="sandbox"?pt(o.nodes()[0].contentDocument.body):pt("body"),C=h==="sandbox"?o.nodes()[0].contentDocument:document,D=C.getElementById(e);J=D.parentElement.offsetWidth,J===void 0&&(J=1200),a.useWidth!==void 0&&(J=a.useWidth);const p=i.db.getTasks();let M=[];for(const m of p)M.push(m.type);M=O(M);const _={};let b=2*a.topPadding;if(i.db.getDisplayMode()==="compact"||a.displayMode==="compact"){const m={};for(const v of p)m[v.section]===void 0?m[v.section]=[v]:m[v.section].push(v);let w=0;for(const v of Object.keys(m)){const k=ri(m[v],w)+1;w+=k,b+=k*(a.barHeight+a.barGap),_[v]=k}}else{b+=p.length*(a.barHeight+a.barGap);for(const m of M)_[m]=p.filter(w=>w.type===m).length}D.setAttribute("viewBox","0 0 "+J+" "+b);const B=x.select(`[id="${e}"]`),A=ze().domain([Oe(p,function(m){return m.startTime}),Pe(p,function(m){return m.endTime})]).rangeRound([0,J-a.leftPadding-a.rightPadding]);function T(m,w){const v=m.startTime,k=w.startTime;let r=0;return v>k?r=1:v<k&&(r=-1),r}p.sort(T),S(p,J,b),Ne(B,b,J,a.useMaxWidth),B.append("text").text(i.db.getDiagramTitle()).attr("x",J/2).attr("y",a.titleTopMargin).attr("class","titleText");function S(m,w,v){const k=a.barHeight,r=k+a.barGap,l=a.topPadding,f=a.leftPadding,c=Re().domain([0,M.length]).range(["#00B9FA","#F95002"]).interpolate(an);Y(r,l,f,w,v,m,i.db.getExcludes(),i.db.getIncludes()),N(f,l,w,v),L(m,r,l,f,k,c,w),P(r,l),X(f,l,w,v)}function L(m,w,v,k,r,l,f){const g=[...new Set(m.map(u=>u.order))].map(u=>m.find(y=>y.order===u));B.append("g").selectAll("rect").data(g).enter().append("rect").attr("x",0).attr("y",function(u,y){return y=u.order,y*w+v-2}).attr("width",function(){return f-a.rightPadding/2}).attr("height",w).attr("class",function(u){for(const[y,V]of M.entries())if(u.type===V)return"section section"+y%a.numberSectionStyles;return"section section0"});const s=B.append("g").selectAll("rect").data(m).enter(),z=i.db.getLinks();if(s.append("rect").attr("id",function(u){return u.id}).attr("rx",3).attr("ry",3).attr("x",function(u){return u.milestone?A(u.startTime)+k+.5*(A(u.endTime)-A(u.startTime))-.5*r:A(u.startTime)+k}).attr("y",function(u,y){return y=u.order,y*w+v}).attr("width",function(u){return u.milestone?r:A(u.renderEndTime||u.endTime)-A(u.startTime)}).attr("height",r).attr("transform-origin",function(u,y){return y=u.order,(A(u.startTime)+k+.5*(A(u.endTime)-A(u.startTime))).toString()+"px "+(y*w+v+.5*r).toString()+"px"}).attr("class",function(u){const y="task";let V="";u.classes.length>0&&(V=u.classes.join(" "));let E=0;for(const[I,W]of M.entries())u.type===W&&(E=I%a.numberSectionStyles);let F="";return u.active?u.crit?F+=" activeCrit":F=" active":u.done?u.crit?F=" doneCrit":F=" done":u.crit&&(F+=" crit"),F.length===0&&(F=" task"),u.milestone&&(F=" milestone "+F),F+=E,F+=" "+V,y+F}),s.append("text").attr("id",function(u){return u.id+"-text"}).text(function(u){return u.task}).attr("font-size",a.fontSize).attr("x",function(u){let y=A(u.startTime),V=A(u.renderEndTime||u.endTime);u.milestone&&(y+=.5*(A(u.endTime)-A(u.startTime))-.5*r),u.milestone&&(V=y+r);const E=this.getBBox().width;return E>V-y?V+E+1.5*a.leftPadding>f?y+k-5:V+k+5:(V-y)/2+y+k}).attr("y",function(u,y){return y=u.order,y*w+a.barHeight/2+(a.fontSize/2-2)+v}).attr("text-height",r).attr("class",function(u){const y=A(u.startTime);let V=A(u.endTime);u.milestone&&(V=y+r);const E=this.getBBox().width;let F="";u.classes.length>0&&(F=u.classes.join(" "));let I=0;for(const[rt,st]of M.entries())u.type===st&&(I=rt%a.numberSectionStyles);let W="";return u.active&&(u.crit?W="activeCritText"+I:W="activeText"+I),u.done?u.crit?W=W+" doneCritText"+I:W=W+" doneText"+I:u.crit&&(W=W+" critText"+I),u.milestone&&(W+=" milestoneText"),E>V-y?V+E+1.5*a.leftPadding>f?F+" taskTextOutsideLeft taskTextOutside"+I+" "+W:F+" taskTextOutsideRight taskTextOutside"+I+" "+W+" width-"+E:F+" taskText taskText"+I+" "+W+" width-"+E}),ot().securityLevel==="sandbox"){let u;u=pt("#i"+e);const y=u.nodes()[0].contentDocument;s.filter(function(V){return z[V.id]!==void 0}).each(function(V){var E=y.querySelector("#"+V.id),F=y.querySelector("#"+V.id+"-text");const I=E.parentNode;var W=y.createElement("a");W.setAttribute("xlink:href",z[V.id]),W.setAttribute("target","_top"),I.appendChild(W),W.appendChild(E),W.appendChild(F)})}}function Y(m,w,v,k,r,l,f,c){if(f.length===0&&c.length===0)return;let g,s;for(const{startTime:E,endTime:F}of l)(g===void 0||E<g)&&(g=E),(s===void 0||F>s)&&(s=F);if(!g||!s)return;if(Z(s).diff(Z(g),"year")>5){wt.warn("The difference between the min and max time is more than 5 years. This will cause performance issues. Skipping drawing exclude days.");return}const z=i.db.getDateFormat(),d=[];let u=null,y=Z(g);for(;y.valueOf()<=s;)i.db.isInvalidDate(y,z,f,c)?u?u.end=y:u={start:y,end:y}:u&&(d.push(u),u=null),y=y.add(1,"d");B.append("g").selectAll("rect").data(d).enter().append("rect").attr("id",function(E){return"exclude-"+E.start.format("YYYY-MM-DD")}).attr("x",function(E){return A(E.start)+v}).attr("y",a.gridLineStartPadding).attr("width",function(E){const F=E.end.add(1,"day");return A(F)-A(E.start)}).attr("height",r-w-a.gridLineStartPadding).attr("transform-origin",function(E,F){return(A(E.start)+v+.5*(A(E.end)-A(E.start))).toString()+"px "+(F*m+.5*r).toString()+"px"}).attr("class","exclude-range")}function N(m,w,v,k){let r=mn(A).tickSize(-k+w+a.gridLineStartPadding).tickFormat(Ut(i.db.getAxisFormat()||a.axisFormat||"%Y-%m-%d"));const f=/^([1-9]\d*)(millisecond|second|minute|hour|day|week|month)$/.exec(i.db.getTickInterval()||a.tickInterval);if(f!==null){const c=f[1],g=f[2],s=i.db.getWeekday()||a.weekday;switch(g){case"millisecond":r.ticks(ee.every(c));break;case"second":r.ticks(te.every(c));break;case"minute":r.ticks(Jt.every(c));break;case"hour":r.ticks($t.every(c));break;case"day":r.ticks(Kt.every(c));break;case"week":r.ticks(re[s].every(c));break;case"month":r.ticks(Qt.every(c));break}}if(B.append("g").attr("class","grid").attr("transform","translate("+m+", "+(k-50)+")").call(r).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10).attr("dy","1em"),i.db.topAxisEnabled()||a.topAxis){let c=hn(A).tickSize(-k+w+a.gridLineStartPadding).tickFormat(Ut(i.db.getAxisFormat()||a.axisFormat||"%Y-%m-%d"));if(f!==null){const g=f[1],s=f[2],z=i.db.getWeekday()||a.weekday;switch(s){case"millisecond":c.ticks(ee.every(g));break;case"second":c.ticks(te.every(g));break;case"minute":c.ticks(Jt.every(g));break;case"hour":c.ticks($t.every(g));break;case"day":c.ticks(Kt.every(g));break;case"week":c.ticks(re[z].every(g));break;case"month":c.ticks(Qt.every(g));break}}B.append("g").attr("class","grid").attr("transform","translate("+m+", "+w+")").call(c).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10)}}function P(m,w){let v=0;const k=Object.keys(_).map(r=>[r,_[r]]);B.append("g").selectAll("text").data(k).enter().append(function(r){const l=r[0].split(Ue.lineBreakRegex),f=-(l.length-1)/2,c=C.createElementNS("http://www.w3.org/2000/svg","text");c.setAttribute("dy",f+"em");for(const[g,s]of l.entries()){const z=C.createElementNS("http://www.w3.org/2000/svg","tspan");z.setAttribute("alignment-baseline","central"),z.setAttribute("x","10"),g>0&&z.setAttribute("dy","1em"),z.textContent=s,c.appendChild(z)}return c}).attr("x",10).attr("y",function(r,l){if(l>0)for(let f=0;f<l;f++)return v+=k[l-1][1],r[1]*m/2+v*m+w;else return r[1]*m/2+w}).attr("font-size",a.sectionFontSize).attr("class",function(r){for(const[l,f]of M.entries())if(r[0]===f)return"sectionTitle sectionTitle"+l%a.numberSectionStyles;return"sectionTitle"})}function X(m,w,v,k){const r=i.db.getTodayMarker();if(r==="off")return;const l=B.append("g").attr("class","today"),f=new Date,c=l.append("line");c.attr("x1",A(f)+m).attr("x2",A(f)+m).attr("y1",a.titleTopMargin).attr("y2",k-a.titleTopMargin).attr("class","today"),r!==""&&c.attr("style",r.replace(/,/g,";"))}function O(m){const w={},v=[];for(let k=0,r=m.length;k<r;++k)Object.prototype.hasOwnProperty.call(w,m[k])||(w[m[k]]=!0,v.push(m[k]));return v}},ai={setConf:ii,draw:si},ci=t=>`
  .mermaid-main-font {
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }

  .exclude-range {
    fill: ${t.excludeBkgColor};
  }

  .section {
    stroke: none;
    opacity: 0.2;
  }

  .section0 {
    fill: ${t.sectionBkgColor};
  }

  .section2 {
    fill: ${t.sectionBkgColor2};
  }

  .section1,
  .section3 {
    fill: ${t.altSectionBkgColor};
    opacity: 0.2;
  }

  .sectionTitle0 {
    fill: ${t.titleColor};
  }

  .sectionTitle1 {
    fill: ${t.titleColor};
  }

  .sectionTitle2 {
    fill: ${t.titleColor};
  }

  .sectionTitle3 {
    fill: ${t.titleColor};
  }

  .sectionTitle {
    text-anchor: start;
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }


  /* Grid and axis */

  .grid .tick {
    stroke: ${t.gridColor};
    opacity: 0.8;
    shape-rendering: crispEdges;
  }

  .grid .tick text {
    font-family: ${t.fontFamily};
    fill: ${t.textColor};
  }

  .grid path {
    stroke-width: 0;
  }


  /* Today line */

  .today {
    fill: none;
    stroke: ${t.todayLineColor};
    stroke-width: 2px;
  }


  /* Task styling */

  /* Default task */

  .task {
    stroke-width: 2;
  }

  .taskText {
    text-anchor: middle;
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }

  .taskTextOutsideRight {
    fill: ${t.taskTextDarkColor};
    text-anchor: start;
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }

  .taskTextOutsideLeft {
    fill: ${t.taskTextDarkColor};
    text-anchor: end;
  }


  /* Special case clickable */

  .task.clickable {
    cursor: pointer;
  }

  .taskText.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideLeft.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideRight.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }


  /* Specific task settings for the sections*/

  .taskText0,
  .taskText1,
  .taskText2,
  .taskText3 {
    fill: ${t.taskTextColor};
  }

  .task0,
  .task1,
  .task2,
  .task3 {
    fill: ${t.taskBkgColor};
    stroke: ${t.taskBorderColor};
  }

  .taskTextOutside0,
  .taskTextOutside2
  {
    fill: ${t.taskTextOutsideColor};
  }

  .taskTextOutside1,
  .taskTextOutside3 {
    fill: ${t.taskTextOutsideColor};
  }


  /* Active task */

  .active0,
  .active1,
  .active2,
  .active3 {
    fill: ${t.activeTaskBkgColor};
    stroke: ${t.activeTaskBorderColor};
  }

  .activeText0,
  .activeText1,
  .activeText2,
  .activeText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Completed task */

  .done0,
  .done1,
  .done2,
  .done3 {
    stroke: ${t.doneTaskBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
  }

  .doneText0,
  .doneText1,
  .doneText2,
  .doneText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Tasks on the critical line */

  .crit0,
  .crit1,
  .crit2,
  .crit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.critBkgColor};
    stroke-width: 2;
  }

  .activeCrit0,
  .activeCrit1,
  .activeCrit2,
  .activeCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.activeTaskBkgColor};
    stroke-width: 2;
  }

  .doneCrit0,
  .doneCrit1,
  .doneCrit2,
  .doneCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
    cursor: pointer;
    shape-rendering: crispEdges;
  }

  .milestone {
    transform: rotate(45deg) scale(0.8,0.8);
  }

  .milestoneText {
    font-style: italic;
  }
  .doneCritText0,
  .doneCritText1,
  .doneCritText2,
  .doneCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .activeCritText0,
  .activeCritText1,
  .activeCritText2,
  .activeCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .titleText {
    text-anchor: middle;
    font-size: 18px;
    fill: ${t.titleColor||t.textColor};
    font-family: var(--mermaid-font-family, "trebuchet ms", verdana, arial, sans-serif);
  }
`,oi=ci,ui={parser:xn,db:ni,renderer:ai,styles:oi};export{ui as diagram};
//# sourceMappingURL=ganttDiagram-a2739b55-Cv2t3q3n.js.map
