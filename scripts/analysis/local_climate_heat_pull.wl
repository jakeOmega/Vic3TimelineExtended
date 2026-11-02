(* Local Climate, heat v2: the Wolfram Language pull behind local_climate.csv's hot_day_c and heat_index
   (docs/superpowers/specs/2026-11-01-local-climate-design.md § 11.2; docs/systems/mod_systems/local_climate.md).

   Set ROWS to a list of {csv_row_number, query, latitude}: the query is the reference place as
   "City, Country" (or {lat, lon} where the name won't resolve), the latitude the CSV's. Each row prints
     id|query|resolved city|city latitude|station|km|years|hot day|heat index|dew point on that day|summer dew point|flags
   from the first of the six stations nearest the place with six years of daily maximum and dew point
   (each year with 300 days of both) in 2010-2020, or 2000-2020 where none had. The hot day is the mean
   over years of each year's highest daily maximum; the heat index the mean over years of each year's
   highest 0.7 x wet-bulb (Stull) + 0.3 x maximum. Flags: far_station (over 150 km), elevation<dz>m (over
   300 m from the place), win2000, few_years (under 8), no_dew, lat_mismatch, no_city, no_data. The loop
   stops after about 15 s, the Wolfram tool's budget per call; resume from the id it names.
   A flagged row whose figures differ from the fit on the record's other fields by 2.5 or more took the fit. *)

T0=AbsoluteTime[];
S[t_,r_]:=t ArcTan[0.151977 Sqrt[r+8.313659]]+ArcTan[t+r]-ArcTan[r-1.676331]+0.00391838 r^1.5 ArcTan[0.023101 r]-4.686035;
H[t_,d_]:=Min[99.,100 Exp[17.625 d/(243.04+d)]/Exp[17.625 t/(243.04+t)]];
V[q_]:=If[Head[q]===Quantity,With[{m=If[QuantityUnit[q]==="DegreesCelsius",QuantityMagnitude[q],Quiet@QuantityMagnitude[UnitConvert[q,"DegreesCelsius"]]]},If[NumberQ[m],m,Missing[]]],Missing[]];
Y[k_]:=First[DateList[k*86400]];
P[e_,p_,g_,y_]:=With[{ts=Quiet@WeatherData[e,p,{{y,1,1},{2020,12,31},g}]},If[Head[ts]===TimeSeries,Association[(Round[#[[1]]/86400]->V[#[[2]]])&/@ts["Path"]],<||>]];
Q[e_,y0_]:=Module[{tx,td,txr,bt,nT,hT,ks,rw,by,hd,hi,hw,sw,mo},tx=P[e,"MaxTemperature","Day",y0];If[Length[tx]==0,Return[{0,0,0,0,0,0,0}]];txr={Y[#[[1]]],#[[2]]}&/@Select[Normal[tx],NumberQ[#[[2]]]&];bt=Select[GroupBy[txr,First,Map[Last]],Length[#]>=300&];nT=Length[bt];hT=If[nT>0,Mean[Max/@Values[bt]],0];td=P[e,"DewPoint","Day",y0];ks=Select[Keys[tx],NumberQ[tx[#]]&&NumberQ[Lookup[td,#,Missing[]]]&];rw={Y[#],tx[#],td[#]}&/@ks;by=Select[GroupBy[rw,First],Length[#]>=300&];If[Length[by]<6,Return[{Length[by],0,0,0,0,nT,hT}]];{hd,hi,hw}=Transpose[Table[Module[{t=r[[All,2]],d=r[[All,3]],s,p},s=MapThread[0.7 S[#1,H[#1,#2]]+0.3 #1&,{t,d}];p=First[Ordering[s,-1]];{Max[t],s[[p]],d[[p]]}],{r,Values[by]}]];mo=GroupBy[Select[Normal[P[e,"DewPoint","Month",y0]],NumberQ[#[[2]]]&],Y[#[[1]]]&,Map[Last]];sw=Cases[Lookup[mo,Keys[by],{}],l_List/;Length[l]>0:>Max[l]];{Length[by],Mean[hd],Mean[hi],Mean[hw],If[sw==={},Missing[],Mean[sw]],nT,hT}];
F[x_]:=If[NumberQ[x],ToString[NumberForm[Round[x,0.1],{5,1}]],""];
R[id_,q_,lat_]:=Module[{en,pos,cl,g,rs,e,st,km,fl={},ce,se,ft=None,nm,i,y0,B},B[n_,c_,x_]:=StringRiffle[{id,q,n,c,"","","","","","",x},"|"];en=If[ListQ[q],GeoPosition[q],Quiet@Interpreter["City"][q]];If[ListQ[q],pos=en;nm="coords";cl=q[[1]],If[Head[en]=!=Entity,Return[B["no_city","","no_city"]]];pos=GeoPosition[en];nm=StringRiffle[en[[2]],"/"];cl=pos[[1,1]]];If[Abs[cl-lat]>1.5,Return[B[nm,ToString[Round[cl,0.1]],"lat_mismatch"]]];g=Quiet@GeoNearest["WeatherStation",pos,6];rs=None;Do[e=g[[i]];Do[st=Q[e,y0];If[st[[1]]>=6,rs={i,e,y0,st};Break[]],{y0,{2010,2000}}];If[rs=!=None,Break[]];If[ft===None&&st[[6]]>=6,ft={i,e,y0,st}],{i,Length[g]}];If[rs===None&&ft=!=None,rs=ft;fl={"no_dew"}];If[rs===None,Return[B[nm,ToString[Round[cl,0.1]],"no_data"]]];{i,e,y0,st}=rs;km=Quiet@QuantityMagnitude[UnitConvert[GeoDistance[pos,GeoPosition[e]],"Kilometers"]];If[NumberQ[km]&&km>150,AppendTo[fl,"far_station"]];If[y0==2000,AppendTo[fl,"win2000"]];If[i>1,AppendTo[fl,"stn"<>ToString[i]]];If[st[[1]]<8&&fl=!={"no_dew"},AppendTo[fl,"few_years"]];ce=If[ListQ[q],None,Quiet@EntityValue[en,"Elevation"]];se=Quiet@WeatherData[e,"Elevation"];If[Head[ce]===Quantity&&Head[se]===Quantity,With[{dz=QuantityMagnitude[UnitConvert[se,"Meters"]]-QuantityMagnitude[UnitConvert[ce,"Meters"]]},If[Abs[dz]>300,AppendTo[fl,"elevation"<>ToString[Round[dz]]<>"m"]]]];If[fl==={"no_dew"},st={st[[6]],st[[7]],Missing[],Missing[],Missing[]},st=st[[1;;5]]];StringRiffle[{id,q,nm,ToString[Round[cl,0.1]],e[[2]],F[km],ToString[st[[1]]],F[st[[2]]],F[st[[3]]],F[st[[4]]],F[st[[5]]],StringRiffle[fl,";"]},"|"]];
Do[If[AbsoluteTime[]-T0>15,Print["STOPPED before id ",r[[1]]];Break[]];Print[R@@r],{r,ROWS}];Print["ELAPSED ",Round[AbsoluteTime[]-T0,0.1]]
