/**
 * App.js 
 *
 *  Auth– on first load call/api/me to see if the
 * browser  holds a valid session cookie.
 
 * guest vs registered
 * guest cannot havemutating endpoints like schedule and history 

 *data model–need convert array of objects from the backend to {headers, rows} so it can be fed to
 * DataPreview && ResultModal 
 */
//命名一定要标准，千万别乱简写!!!!
// 2030 style 
import React, { useState, useEffect } from "react";
import "bootstrap/dist/css/bootstrap.min.css";

import LoginForm from "./components/LoginForm";
import RegisterForm from "./components/RegisterForm";
import NewCrawlJobForm from "./components/NewCrawlJobForm";
import ScheduledJobsTable from "./components/ScheduledJobsTable";
import APIAccess  from "./components/APIAccess";
import DataPreview from "./components/DataPreview";
import AIAssistant from "./components/AIAssistant";
import VerifyEmailModal from "./components/VerifyEmailModal";
import ResultModal from "./components/ResultModal";


import {
  api,
  fetchJobs,
  fetchJobRuns,
  fetchRunData,
  downloadRun
} from "./api";

export default function App() {

// Auth/session state
//  verification modal state
// Crawl preview && job list
// Result‑details modal state
//state is initialised to null

  const [checkingAuth, setCheckingAuth] =useState(true);
  const [authMode,setAuthMode] = useState("login");   //Login vs Register form
  const [tab,setTab] = useState("crawl");
  const [currentUser, setCurrentUser]= useState(null); //username,apiKey or null
  const [isGuest,setIsGuest]=useState(false); 

  // email verification 
  const [needsVerify,setNeedsVerify] = useState(false);
  const [pendingUsername, setPendingUsername] =useState(null);

  //Job && preview table
  const [scheduledJobs,setScheduledJobs]= useState([]);
  const [previewData,setPreviewData]=useState(null);
  const [previewJobName,setPreviewJobName] = useState("");
  const [previewLoading,setPreviewLoading] =useState(false);

  //history
  const [detailsJob,setDetailsJob]= useState(null); // selected job object
  const [detailsData,setDetailsData]= useState(null); 
  const [detailsRunId,setDetailsRunId] = useState(null); // id for downloads used for scheduled crawl

  const [crawlCtx, setCrawlCtx] =useState({ url: "",mode: "",value:""});


//is user logged in success means we already have a session
//注意前段开发多来try catch use whenever possible
// network issue and 500 server error and break UI can crach web

useEffect(()=>{
  (async ()=>{
    const me=await api("/me");
    setCurrentUser({username: me.username, apiKey: me.apiKey});
    window.localStorage.setItem("apiKey", me.apiKey);// to keep curre apu key
    setCheckingAuth(false);
  })();
}, []);

//keep shceduled table frech for registerd user
  useEffect(()=>{
    if (currentUser &&!isGuest) {
      fetchJobs().then(setScheduledJobs).catch(console.error);
    }
  },[currentUser, isGuest]);
// tranform arr to table
  const toTable = (arr = [])=>{
    const headers = Array.from(
      arr.reduce((set, obj) =>{ //gather keys from all objects into Set:
        Object.keys(obj).forEach(k => set.add(k));
        return  set;
      },new Set())
    );
    const rows=arr.map(obj =>headers.map(h => obj[h]??""));// ?? returns "" fro null or undefined.
//above line for each object builds a row array in header order
    return { headers,rows};
  };

  const runCrawlNow =async(url,mode,value,jobName)=> {
    setCrawlCtx({ url, mode, value });
    setPreviewLoading(true);
    setPreviewData(null);
    try{
      const{ data =[]}=
        await api("/crawl", "POST",{ url, mode, value, name: jobName });
      setPreviewJobName(jobName);
      setPreviewData(toTable(data));
      if (!isGuest) { // guests dun have jobs
        const jobs =await fetchJobs();
        setScheduledJobs(jobs);
        setTab("scheduled");
     
    }
    }catch(e){
      alert(e.message||"crawl failed");
    } finally {

      setPreviewLoading(false);
}
};
const scheduleCrawl = async (url,mode,value,name,iso) => {
    if(isGuest) return null; 
    //这里可能会有奇奇怪怪的错，需要catch
    try {const r=await api("/schedule","POST",
        {url,mode,value,name,dateTime: iso });
      if (r.msg !== "scheduled") return r.msg;
      setScheduledJobs(await fetchJobs());
      return null;
    } catch (e){
      return e.message;
    }
  };//should delete this one if scheduled crawl still not work


//目前只有email register
//以后加其他的（大概）
  const handleLogin =async (email,pw)=>{
    try {const r= await api("/login", "POST",{username:email,password: pw });

      if (r.msg === "unverified email") {
        setPendingUsername(email);
        setNeedsVerify(true);
        return "Please enter correct verification code.";
      }
      if (r.msg!=="logged_in") return r.msg || "Login failed";
      const me=await api("/me");
      setCurrentUser({username: me.username, apiKey: me.apiKey });
      window.localStorage.setItem("apiKey", me.apiKey);
      setIsGuest(false);
      return null;

    } catch (e) {
      return e.message;
    }
  };}
  

  const handleLogout =async()=>{
    if(!isGuest) await api("/logout","POST").catch(()=>{});
    setCurrentUser(null);
    setIsGuest(false);
    setScheduledJobs([]);
    window.localStorage.removeItem("apiKey");
  };

  const handleGuest=()=>{
    setIsGuest(true);
    setCurrentUser(null);
  };

// delete scheduled job or finished job
  const deleteJob=async id=>{
    if(isGuest) return;// guest dun have this 
    if(!window.confirm("Delete this job?")) return;
    try {
      await api(`/jobs/${id}`, "DELETE");
      setScheduledJobs(js =>js.filter(j => j.id!==id));
    } catch (e) {
      alert("Delete failed: "+ e.message);
    }//这里似乎不用 try catch 至少目前没见过err
  };


// Open modal with last run details for a job.
// need migrate old db to iclude jobid
  const showDetails=async jobId =>{
    try {
      const runs=await fetchJobRuns(jobId);
      if (!runs.length){alert("No runs yet for this job.");return;}
      const latestRunId=runs[0].id;

      const data=await fetchRunData(latestRunId);
      const job =scheduledJobs.find(j =>j.id===jobId)|| { id: jobId };

      setDetailsJob(job);
      setDetailsData(toTable(data));
      setDetailsRunId(latestRunId);
    } catch (e) {
      alert(e.message||"Failed to load job details");
    }
  };

// handle CSV && JSON download
  const handleDownload = async (runId, fmt ="csv")=>{
    try{
      const url = await downloadRun(runId, fmt);
      window.open(url, "_blank");
      // revoke objt URL later to free memory
      setTimeout(()=>URL.revokeObjectURL(url), 5000);
    } catch (e) {
      alert(e.message || "Download failed");
    }
  };

  const closeDetails = () => {
    setDetailsJob(null);
    setDetailsData(null);
    setDetailsRunId(null);
  };


  // Early exits (auth check && verification modal)
  if (checkingAuth) return <p className="text-center mt-5">Loading…</p >;

  if (needsVerify&&pendingUsername) {
    //Show Verify‑Email modal; everything else is prevented until done. */
    return (
       <VerifyEmailModal
        username={pendingUsername}
        onClose={()=> 
            {setNeedsVerify(false); setPendingUsername(null); }}
        
            onVerified={async code => {

          try {
            const r = await api("/verify","POST",{ code });
            if (r.msg==="verified") {
              setCurrentUser({ username: pendingUsername, apiKey: r.apiKey});
              window.localStorage.setItem("apiKey", r.apiKey);
              setNeedsVerify(false);
              setPendingUsername(null);
            } else {
              alert("Verification failed:"+r.msg);
            }
          } catch (e) { alert(e.message); }
        }}
      />
    );
  }
//login
  if (!currentUser&& !isGuest) {
    return (
      <div className="container mt-5">
        <h1 className="text-center mb-4">Crawlernaut</h1>
        {authMode === "login" ? (
          <LoginForm

            onLogin={handleLogin}
            onGuest={handleGuest}
            switchToRegister={()=>setAuthMode("register")}
          />
        ):(
          <RegisterForm
            onRegister={handleRegister}
            switchToLogin={()=>setAuthMode("login")}
          />
        )}
      </div>
    );
  }

  // webpage 
  return (
    <div className="container my-4">

      {/* Header – welcome + logout */}
      <header className="d-flex justify-content-between align-items-center mb-3">
        <h4>
          Welcome, {isGuest ?"Guest":currentUser.username}
          {isGuest &&<small className="text-muted ms-2">(visitor)</small>}
        </h4>
        <button className="btn btn-link"onClick={handleLogout}>
          {isGuest ? "Exit Visitor" :"Logout"}
        </button>
      </header>

      {/* Nav tabs */}
      <ul className="nav nav-tabs mb-3">
        {[
          ["crawl","New Crawl"],
          ["scheduled","Scheduled Jobs"],
          ["api", "API Access"],
          ["ai","AI Assistant"]
        ].map(([key, label]) => (
          <li className="nav-item" key={key}>
            <button
              className={`nav-link ${tab===key? "active":""}`}
              onClick={() => setTab(key)}
            >
              {label}
              </button>
          </li>
        ))}
      </ul>

      {/* panels */}
      {tab==="crawl" &&(
<>
          <NewCrawlJobForm
        onRunNow={runCrawlNow}
        onSchedule={scheduleCrawl}
          />
        {previewLoading && <p>Running crawl…</p >}
        {previewData && !previewLoading && (
        <div className="mt-4">
              <h5>Preview – {previewJobName}</h5>
              <DataPreview
            data={previewData}
            onClose={() => setPreviewData(null)}
            />
            </div>
          )}
        </>
      )}


      {tab ==="api"&& !isGuest && (
        <APIAccess
          apiKey={currentUser.apiKey}
          onKeyUpdate={k =>{
        setCurrentUser(u =>({...u, apiKey:k}));
            window.localStorage.setItem("apiKey", k);
          }}
        />
      )}
      {tab === "ai"&& (
        <AIAssistant
          url={crawlCtx.url}
          mode={crawlCtx.mode}
          value={crawlCtx.value}
        />
      )}

      {detailsJob &&detailsData && (
        <ResultModal
          job={detailsJob}
          data={detailsData}
          onClose={closeDetails}
          onDownloadCSV={() => handleDownload(detailsRunId, "csv")}
          onDownloadJSON={() => handleDownload(detailsRunId, "json")}
        />
      )}
    </div>
  );
}
//这个不用export了
