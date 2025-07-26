import React, { useState } from 'react';

function RegisterForm({ onRegister, switchToLogin }) {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const errMsg = await onRegister(email, password);
    if (errMsg) {
      setError(errMsg);
    }
  };

  return (
    <div className="card shadow-sm p-4 mx-auto" style={{ maxWidth: 400 }}>
      <h2 className="text-center mb-4">Register</h2>
      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-3">
          <label htmlFor="regEmail" className="form-label">Email</label>
          <input 
            type="email" 
            id="regEmail" 
            className="form-control"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required 
          />
        </div>
        <div className="mb-3">
          <label htmlFor="regPassword" className="form-label">Password</label>
          <input 
            type="password" 
            id="regPassword" 
            className="form-control"
            placeholder="Create a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
        </div>
        {error && <div className="alert alert-danger py-2">{error}</div>}
        <button type="submit" className="btn btn-success w-100">Create Account</button>
      </form>
      <div className="text-center mt-3">
        <button type="button" onClick={switchToLogin} className="btn btn-link p-0">
          <small>Already have an account? <span className="text-primary">Login</span></small>
        </button>
      </div>
    </div>
  );
}

export default RegisterForm;
