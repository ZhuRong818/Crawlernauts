import React, { useState } from 'react';

export default function VerifyEmailModal({ username, onClose, onVerified }) {
  const [code, setCode] = useState('');

  return (
    <div className="modal d-block" tabIndex="-1" style={{ background: '#0008' }}>
      <div className="modal-dialog">
        <div className="modal-content p-3">
          <h5>Verify {username}</h5>
          <p>Enter the 6-digit code we just emailed you.</p>
          <input
            className="form-control mb-2"
            value={code}
            onChange={e => setCode(e.target.value)}
            placeholder="Enter code"
          />
          <button
            className="btn btn-primary me-2"
            disabled={!code.trim()}
            onClick={() => onVerified(code.trim())}
          >
            Verify
          </button>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
