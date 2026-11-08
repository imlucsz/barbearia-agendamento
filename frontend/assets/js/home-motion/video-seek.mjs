// Event-driven latest-target queue. No ticker, RAF, autoplay or competing seeks.
export function progressToTime(progress,duration,fps=24) {
  if(!Number.isFinite(duration)||duration<=0)return 0;
  const last=Math.max(0,duration-1/fps);
  return Math.min(last,Math.max(0,Math.round(Math.max(0,Math.min(1,progress))*duration*fps)/fps));
}

export function createVideoSeeker(video,{runtime,source,onFrame=()=>{},onMetadata=()=>{},onFailure=()=>{},fps=24}) {
  const offs=[],latencies=[],frameLatencies=[];
  let closed=false,attached=false,visible=false,failed=false,inFlight=false,metadataAt=null;
  let desiredProgress=0,desiredTime=0,presentedTime=0,seekStarted=0,attachStarted=0;
  let seeks=0,completed=0,targets=0,coalesced=0,frameCallback=null,seekTimer=0,metadataTimer=0,presentTimer=0;
  let generation=0;
  const listen=(type,fn)=>offs.push(runtime.listen(video,type,fn));
  function cancelFrame(){if(frameCallback!==null){video.cancelVideoFrameCallback?.(frameCallback);frameCallback=null;}clearTimeout(presentTimer);}
  function publish(time) {
    if(closed||failed||!visible||document.hidden)return;
    presentedTime=Math.max(0,Math.min(video.duration||10,time));
    onFrame(presentedTime);
  }
  function fail(reason) {
    if(closed||failed)return;
    failed=true;inFlight=false;cancelFrame();clearTimeout(seekTimer);clearTimeout(metadataTimer);video.pause();
    onFailure(reason);
  }
  function pump() {
    if(closed||failed||!attached||!visible||document.hidden||video.readyState<1||!Number.isFinite(video.duration)||video.duration<=0)return;
    desiredTime=progressToTime(desiredProgress,video.duration,fps);
    if(inFlight||video.seeking){coalesced++;return;}
    if(Math.abs(video.currentTime-desiredTime)<.5/fps&&video.readyState>=2){publish(video.currentTime);return;}
    inFlight=true;seekStarted=performance.now();seeks++;const token=++generation;
    cancelFrame();
    if(video.requestVideoFrameCallback){
      frameCallback=video.requestVideoFrameCallback((_now,metadata)=>{
        frameCallback=null;if(closed||token!==generation)return;
        frameLatencies.push(performance.now()-seekStarted);if(frameLatencies.length>200)frameLatencies.shift();
        publish(metadata.mediaTime);
      });
    }
    try{video.currentTime=desiredTime;}catch{inFlight=false;fail('seek-rejected');return;}
    clearTimeout(seekTimer);
    seekTimer=setTimeout(()=>{
      if(closed||failed)return;
      if(video.seeking){fail('seek-timeout');return;}
      inFlight=false;publish(video.currentTime);pump();
    },1500);
  }
  function metadata() {
    if(closed||failed||!Number.isFinite(video.duration)||video.duration<=0)return;
    if(metadataAt===null){metadataAt=performance.now()-attachStarted;clearTimeout(metadataTimer);onMetadata(video.duration);}
    pump();
  }
  listen('loadedmetadata',metadata);
  listen('durationchange',()=>{if(attached)metadata();});
  listen('loadeddata',()=>{if(!video.seeking&&!inFlight)publish(video.currentTime);pump();});
  listen('seeked',()=>{
    if(closed||failed)return;
    if(inFlight){latencies.push(performance.now()-seekStarted);if(latencies.length>200)latencies.shift();completed++;}
    inFlight=false;clearTimeout(seekTimer);
    if(!video.requestVideoFrameCallback)publish(video.currentTime);
    else {const token=generation;presentTimer=setTimeout(()=>{if(token===generation)publish(video.currentTime);},120);}
    pump();
  });
  listen('error',()=>fail(`media-error-${video.error?.code||'unknown'}`));
  offs.push(runtime.listen(document,'visibilitychange',()=>{if(document.hidden)cancelFrame();else pump();}));
  function attach() {
    if(closed||failed||attached)return;
    attached=true;attachStarted=performance.now();video.muted=true;video.playsInline=true;
    video.preload='auto';video.src=source;video.load();
    metadataTimer=setTimeout(()=>fail('metadata-timeout'),10000);
  }
  return {
    prepare:attach,
    setVisible(value){visible=value;if(value){attach();pump();}else{cancelFrame();video.pause();}},
    seekProgress(value){if(!Number.isFinite(value))return;desiredProgress=Math.max(0,Math.min(1,value));targets++;pump();},
    snapshot(){
      const quantile=(values,p)=>{if(!values.length)return null;const a=[...values].sort((x,y)=>x-y);return Math.round(a[Math.min(a.length-1,Math.floor(a.length*p))]*10)/10;};
      return {attached,visible,failed,closed,metadataMs:metadataAt===null?null:Math.round(metadataAt*10)/10,duration:Number.isFinite(video.duration)?video.duration:null,readyState:video.readyState,seeking:video.seeking,inFlight,desiredProgress,desiredTime,presentedTime,currentTime:video.currentTime,seeks,completed,targets,coalesced,seekMedianMs:quantile(latencies,.5),seekP95Ms:quantile(latencies,.95),presentP95Ms:quantile(frameLatencies,.95),pendingFrameCallbacks:frameCallback===null?0:1,additionalRAFLoops:0,paused:video.paused};
    },
    destroy(){if(closed)return;closed=true;generation++;cancelFrame();clearTimeout(seekTimer);clearTimeout(metadataTimer);for(const off of offs)off();video.pause();video.removeAttribute('src');video.load();inFlight=false;visible=false;}
  };
}
