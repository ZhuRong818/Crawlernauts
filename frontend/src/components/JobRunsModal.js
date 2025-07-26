import React, { useEffect, useState } from 'react';
import { listRuns, getResult, downloadResult } from '../api';
import DataPreview from './DataPreview';
import { saveAs } from 'file-saver';

export default function JobRunsModal({ job, onClose }) {
  const [runs, setRuns]       = useState([]);
  const [activeId, setActive] = useState(null);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    listRuns(job.id).then(setRuns).catch(alert);
  }, [job.id]);

  const showRun = async id => {
    setActive(id);
    const rows = await getResult(id);
    const cols = [...new Set(rows.flatMap(Object.keys))];
    setPreview({
      headers: cols.map(c => c.toUpperCase()),
      rows: rows.map(r => cols.map(c => r[c] ?? ''))
    });
  };

  const dl = async (id, fmt) => {
    const blob = await downloadResult(id, fmt);
    saveAs(blob, `job${job.id}_run${id}.${fmt}`);
  };

  return (
    <div className="modal d-block" tabIndex="-1" style={{background:'rgba(0,0,0,.5)'}}>
      <div className="modal-dialog modal-lg modal-dialog-scrollable">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Runs – {job.name}</h5>
            <button className="btn-close" onClick={onClose}/>
          </div>
          <div className="modal-body">
            <ul className="list-group mb-3">
              {runs.map(r => (
                <li key={r.id}
                    className={`list-group-item d-flex justify-content-between align-items-center
                                ${r.id===activeId?'active':''}`}>
                  <span>{new Date(r.ranAt).toLocaleString()}</span>
                  <div>
                    <button className="btn btn-sm btn-outline-primary me-2"
                            onClick={() => showRun(r.id)}>
                      Preview
                    </button>
                    <button className="btn btn-sm btn-outline-success me-1"
                            onClick={() => dl(r.id,'csv')}>
                      CSV
                    </button>
                    <button className="btn btn-sm btn-outline-secondary"
                            onClick={() => dl(r.id,'json')}>
                      JSON
                    </button>
                  </div>
                </li>
              ))}
            </ul>

            {preview && (
              <>
                <h6>Preview of run #{activeId}</h6>
                <DataPreview data={preview}/>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
