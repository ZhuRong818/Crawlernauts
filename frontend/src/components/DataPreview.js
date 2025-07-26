// src/components/DataPreview.js
// client‑side only; 

import React,{useCallback}from"react";
import JSZip from "jszip";
export default function DataPreview({
  jobName="Untitled",
  data:{headers,rows},
  onClose,
}) {

  const srcIdx =headers.findIndex((h) => h.toLowerCase()==="src");
  const hasImages=srcIdx!==-1;

  // turn Blob into a download
  const triggerDownload = (blob, filename)=>{
    const url =URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href=url;
    a.download=filename;
    a.click();
    URL.revokeObjectURL(url);
  };
//下边的别乱动，目前没问题 7.11
  const downloadCSV = useCallback(()=>{
    const csvLines =[
      headers.join(","),
      ...rows.map((r) =>
        r.map((v) => `"${String(v).replace(/"/g,'""')}"`).join(",")
      ),
    ];
    triggerDownload(
      new Blob([csvLines.join("\n")],{type:"text/csv" }),
      `${jobName}.csv`
    );
  },[headers,rows,jobName]);
// need rebuild arr of obj frm arr of arr for json
  const downloadJSON =useCallback(()=>{
    const objs=rows.map((r)=>
      headers.reduce((o, h, i)=>({...o,[h]:r[i]}),{})
    );
    triggerDownload(
      new Blob([JSON.stringify(objs, null, 2)], {
        type: "application/json",
      }),
      `${jobName}.json`
    );
  }, [headers, rows, jobName]);

  // fetch img url and download zip
  const downloadImages=useCallback(async()=>{
    if (!hasImages) return alert("No Src column found");
    const zip=new JSZip();
    let count=0;

    for (const row of rows) {
      const url = row[srcIdx];
     const resp=await fetch(url);
        if (!resp.ok) throw new Error();
        const blob = await resp.blob();
        const ext = (url.split(".").pop()||"img").split(/\#|\?/)[0];
        zip.file(`img_${++count}.${ext}`, blob);
    }

    if (count===0) return alert("No images downloaded");
    const zipBlob = await zip.generateAsync({ type: "blob" });
    triggerDownload(zipBlob, `${jobName}_images.zip`);
  }, [rows, srcIdx, hasImages, jobName]);

  return (
    <div className="data-preview">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <strong>Data Preview – {jobName}</strong>
        <button className="btn btn-sm btn-secondary" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="mb-2">
        <button
          onClick={downloadCSV}

          className="btn btn-sm btn-outline-secondary me-2"
        >
          
          CSV
        </button>
        <button
          onClick={downloadJSON}
          className="btn btn-sm btn-outline-secondary me-2"
        >

          JSON
        </button>
        {hasImages && (
          <button
            onClick={downloadImages}
            className="btn btn-sm btn-outline-secondary"
          >
        Images (ZIP)
          </button>
        )}
      </div>
      <div
        className="table-responsive"
        style={{ maxHeight: 300, overflowY: "auto" }}
      >
        {rows.length===0?(
          <p className="text-muted">No data found.</p >
        ) : (
          <table className="table table-bordered table-sm m-0">
            <thead className="table-light">
              <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>
                      {j === srcIdx ? (
                        <a href= "_blank" rel="noreferrer">
                          {cell}
                        </a >
                      ) : (
                        cell
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
