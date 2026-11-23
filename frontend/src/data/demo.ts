export type Transaction={id:string;date:string;description:string;vendor:string;category:string;amount:number;type:'income'|'expense';status:'normal'|'review'|'flagged'};
export const transactions:Transaction[]=[
{id:'TX-1048',date:'2026-11-22',description:'Cloud infrastructure',vendor:'CloudSphere',category:'Technology',amount:1840,type:'expense',status:'normal'},
{id:'TX-1047',date:'2026-11-22',description:'Enterprise subscription',vendor:'WorkSuite Pro',category:'Software',amount:899,type:'expense',status:'review'},
{id:'TX-1046',date:'2026-11-21',description:'Client payment — Northstar',vendor:'Northstar Co.',category:'Sales',amount:12500,type:'income',status:'normal'},
{id:'TX-1045',date:'2026-11-20',description:'Office supplies',vendor:'Paper & Co.',category:'Operations',amount:426,type:'expense',status:'normal'},
{id:'TX-1044',date:'2026-11-19',description:'Digital campaign',vendor:'AdCurrent',category:'Marketing',amount:3280,type:'expense',status:'flagged'},
{id:'TX-1043',date:'2026-11-18',description:'Client payment — Verity',vendor:'Verity Labs',category:'Sales',amount:9200,type:'income',status:'normal'},
{id:'TX-1042',date:'2026-11-17',description:'Workspace license renewal',vendor:'WorkSuite Pro',category:'Software',amount:899,type:'expense',status:'review'},
{id:'TX-1041',date:'2026-11-15',description:'Consulting services',vendor:'Morrow Consulting',category:'Professional services',amount:2150,type:'expense',status:'normal'}];
export const cashFlow=[{month:'Jun',income:32,expenses:23},{month:'Jul',income:36,expenses:25},{month:'Aug',income:34,expenses:27},{month:'Sep',income:42,expenses:29},{month:'Oct',income:39,expenses:31},{month:'Nov',income:48,expenses:30}];
export const expenseMix=[{name:'People',value:34,color:'#C6F432'},{name:'Technology',value:26,color:'#FFFFFF'},{name:'Marketing',value:18,color:'#8B8F82'},{name:'Operations',value:13,color:'#55585A'},{name:'Other',value:9,color:'#FFB84D'}];
export const alerts=[{id:1,severity:'high',title:'Marketing spend spike',detail:'AdCurrent is 38% above its 90-day average.',impact:1240,time:'2 hours ago'},{id:2,severity:'medium',title:'Recurring subscription review',detail:'WorkSuite Pro renewed twice within 5 days.',impact:899,time:'Yesterday'},{id:3,severity:'low',title:'Vendor concentration',detail:'Technology spend is concentrated across 2 vendors.',impact:0,time:'Nov 20'}];