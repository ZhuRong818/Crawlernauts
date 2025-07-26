// src/components/APIAccess.js
// logged in user can view api key for crawling
import React,{useRef,useState}from"react";
import {api}from "../api";

function APIAccess({apiKey,onKeyUpdate}){
  // disable button when waiting
  // this is important on nrender as it can take a few seconds to generate
  const[busy,setBusy]=useState(false);

  const[copied,setCopied]=useState(false);
  const inputRef = useRef(null);

  const regenerate=async()=>{
    setBusy(true);
    try {
      const res=await api("/regenerate_key", "POST");
      onKeyUpdate(res.apiKey);  // need upadate on app.js
      setTimeout(() => inputRef.current?.select(), 100);
    }catch(err){
      alert("Unable to regenerate key. Please check console message.");
     }finally{
      setBusy(false);
    }
  };

  const copyToClipboard=()=>{
    navigator.clipboard
      .writeText(apiKey)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000); // reset after 2 s
      })
      .catch(() => alert("Failed to copy API key"));
  };


  return(
    <div style={{ maxWidth: 500 }}>
      <label className="form-label">API Key</label>
      <div className="input-group mb-2">
        <input
          type="text"
          ref={inputRef}
          className="form-control font-monospace"
          value={apiKey||""}
          readOnly
        />
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={regenerate}
          disabled={busy}
        >

          {busy ? "Regenerating…" : "Regenerate"}
        </button>
        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={copyToClipboard}
        >
          Copy
        </button>
      </div>

      {copied && (
        <div className="text-success">
          <small>API key copied to clipboard ✔</small>
        </div>
      )}

      <p className="text-muted small mt-2">
        Use this key to call the crawl API directly. Keep it secret – regenerating
        will invalidate the previous key.
      </p >
    </div>
  );
}
export default APIAccess;
