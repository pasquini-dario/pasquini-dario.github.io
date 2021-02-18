
//-----------------------------------
function parseString(raw_psswd){
  var xid = []
  for(var i = 0; i < max_len; i++){
    if(i < raw_psswd.length){
      xid.push(CM[raw_psswd.charAt(i)])
    }else if(i == raw_psswd.length){
      xid.push(CM['<END>'])
    }else{
      xid.push(CM['<PAD>']);
    }
  }
  return xid;
}
//-----------------------------------
function makeHoles(s){
  const xid = parseString(s);
  var xids = []
  for(var i = 0; i < s.length; i++){
    x = [...xid];
    x[i] = CM['<NONE>'];
    xids.push(x)
  }
  return xids;
}
//-----------------------------------
function get_local_conditional_probabilities(raw_psswd, p){
  const xid = parseString(raw_psswd);
  var lcp = [];
  var G = 1;
  for(var i = 0; i < raw_psswd.length; i++){
      const cid = xid[i];
      g = get_g(p[i][i], cid);
      lcp.push( [raw_psswd.charAt(i), p[i][i][cid], g] );
      G = G * g;
  }
  return [lcp, G]
}
//-----------------------------------
function get_sc(lcp){
  var max = 0;
  var imax = 0;
  for(var i = 0; i < lcp.length; i++){
      if(lcp[i][1] >= max){
        max = lcp[i][1];
        imax = i;
      }
  }
  return imax;
}
//-----------------------------------
function get_g(p, xid){
  const tp = p[xid];
  var ltp = 1;
  for(var i = 0; i < p.length; i++){
      if(tp < p[i]){
        ltp = ltp+1;
      }
  }
  return ltp;
}
