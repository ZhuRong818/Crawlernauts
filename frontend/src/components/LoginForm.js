import React,{useState}from 'react';

function LoginForm({ onLogin, switchToRegister,onGuest}){
  const[email,setEmail]= useState('');
  const[password,setPassword]= useState('');
  const[error,setError]=useState('');
  const handleSubmit =async(e)=>{
    e.preventDefault();
    setError('');
    const errMsg=await onLogin(email, password);
    if (errMsg){
      setError(errMsg);
    }
  };



  return (
    <div className="card shadow-sm p-4 mx-auto" style={{maxWidth: 400}}>
      <h2 className="text-center mb-4">Login</h2>
      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-3">
          <label htmlFor="loginEmail" className="form-label">Email</label>
          <input 
            type="email" 
            id="loginEmail" 
            className="form-control"
            placeholder="name@example.com"
            value={email}
            onChange={(e)=>setEmail(e.target.value)}
            required 
          />
        </div>
        <div className="mb-3">
          <label htmlFor="loginPassword" className="form-label">Password</label>
          <input 
            type="password" 
            id="loginPassword" 
            className="form-control"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
        </div>
        {/* linkto registration form */}
        {error && <div className="alert alert-danger py-2">{error}</div>}
        <button type="submit" className="btn btn-primary w-100">Sign In</button>
      </form>
      <div className="text-center mt-3">
        <button type="button" onClick={switchToRegister} className="btn btn-link p-0">
          <small>Don’t have an account? <span className="text-primary">Register</span></small>
        </button>
      </div>
      <div className="text-center mt-2">
        <button type="button" onClick={onGuest} className="btn btn-outline-secondary w-100">
          Continue as Guest
        </button>
      </div>
    </div>
  );
}

export default LoginForm;
