// src/components/NewCrawlJobForm.js
import React,{useState}from'react';
export default function NewCrawlJobForm({onRunNow,onSchedule }) {

  const[jobName,setJobName]=useState('');          
  const[url,setUrl]= useState('');          
  const[mode,setMode]=useState('tag'); // extraction mode-- tag css img
  const[value,setValue]=useState('a');     
  const[schedule,setSchedule]= useState('Run Once');  // cahnge to shcedule
  const[dateTime,setDateTime]= useState('');         
  const[error,setError]= useState('');    

// curr sg time
  const sgTime=()=>{
    const nowUtc=Date.now();
    const sgMs=nowUtc + 8 * 60 * 60 * 1000;
    const d=new Date(sgMs);
    d.setSeconds(0, 0);
    return d.toISOString().slice(0, 16); 
  };
  const MAX_ISO ='2035-12-31T23:59';

  const handleSubmit =async(e)=>{
    e.preventDefault();
    setError(''); // clear previous errors

    if (!jobName.trim()) {
      return setError('please give your crawl job a name.');
    }
    if (!url.trim()) {
      return setError('please enter a valid URL.');
    }
    if ((mode ==='tag'||mode=== 'css')&&!value.trim()) {
      return setError('please enter extraction value');
    }

    try {
      let errMsg=null;

      if(schedule==='Run Once') {
    
        errMsg=await onRunNow(url,mode,value,jobName);
      }else {
        const raw = dateTime || sgTime();         
        const [d,t] = raw.split('T');                       
        const sgString = `${d}T${t}:00+08:00`;           
        const isoUtc= new Date(sgString).toISOString();    
// no past time or >206 1.1 is allowed
        const nowSg=new Date(new Date().toISOString().split('.')[0]+'+08:00');
        if(new Date(sgString) < nowSg) {
          return setError('start time must be in the future (SG time).');
        }
        if(isoUtc > MAX_ISO) {
          return setError('start time must be before 2035‑12‑31 23:59.');
        }
        // finally can scheduled
        errMsg=await onSchedule(
          url, mode, value,jobName,
          isoUtc,        
          true,  
          schedule  )
      }
     // err caused by api issue
      if (errMsg) {
        setError(errMsg);
      } else {
        // reset form after submission    
        setJobName('');
        setUrl('');
        setValue(mode==='tag'?'a':'');
        setDateTime('');
      }
    }catch(err){
      // unexpected err prevent site crach
      setError(err.message||'something went wrong.Please check console for more information');
    }
  };

  const needsDateTime = schedule !== 'Run Once';

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      {/* jobname */}
      <div className="mb-3">
        <label htmlFor="jobName"className="form-label">Crawl Job Name</label>
        <input

          id="jobName"
          className="form-control"
          maxLength={80}
          value={jobName}
          onChange={e=>setJobName(e.target.value)}
          placeholder="e.g. Daily Headlines"
        />
      </div>

      {/* target URL */}

      <div className="mb-3">
        <label htmlFor="url"className="form-label">Target URL</label>
        <input
          id="url"
          type="url"
          className="form-control"
          placeholder="https://example.com"
          value={url}
          onChange={e => setUrl(e.target.value)}
        />
      </div>

      <div className="mb-3">
        <label className="form-label">Extraction Mode</label><br />
        {[['tag','By Tag Name'],
          ['css', 'By CSS Selector'],
          ['text', 'First Paragraph'],
          ['image','Images'],
        ].map(([val, label])=>(
          <div className="form-check form-check-inline" key={val}>
            <input
              id={`mode-${val}`}
              name="mode"
              type="radio"
              className="form-check-input"
              value={val}
              checked={mode===val}
              onChange={() => {
                setMode(val);
                setValue(val ==='tag'?'a':'');
              }}
            />
            <label htmlFor={`mode-${val}`} className="form-check-label">
                {label}
            </label>
           </div>
        ))}
      </div>

      {/* extraction value for tag/css */}
      {(mode==='tag'||mode==='css') && (
        <div className="mb-3">
          <label htmlFor="value" className="form-label">
            {mode==='tag'?'Tag Name':'CSS Selector'}
          </label>
          <input
            id="value"
            className="form-control"
            value={value}
            onChange={e => setValue(e.target.value)}
            placeholder={mode ==='tag'?'e.g.a,p,h1':'e.g. #main .content'}
           />
        </div>
      )}
      <div className="mb-3">
        <label htmlFor="schedule" className="form-label">Schedule</label>
        <select
          id="schedule"
          className="form-select"
          value={schedule}
          onChange={e =>setSchedule(e.target.value)}
        >

          <option>Run Once</option>
          <option>Daily</option>
          <option>Weekly</option>
        </select>
      </div>

      {/*set time for scheduled job */}
      {needsDateTime&&(
        <div className="mb-3">
          <label htmlFor="dateTime"className="form-label">
            Start Date &amp; Time (SGT)
          </label>
          <input
            id="dateTime"
            type="datetime-local"
            className="form-control"
            min={sgTime()}
            max={MAX_ISO}
            value={dateTime}
            onChange={e => setDateTime(e.target.value)}
          />
          <div className="form-text">
            Must be &gt; now and &lt; 2035-12-31 23:59(SG time).
          </div>
        </div>
      )}

      {/* show validation / API errors */}
      {error && (
        <div className="alert alert-danger py-2">
          {error}
        </div>
      )}

      <button className="btn btn-primary">
        {schedule==='Run Once'?'Run Now':'Schedule Crawl'}
      </button>
    </form>
  );
}
