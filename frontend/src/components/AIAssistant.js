// src/components/AIAssistant.js
import React, {useState,useEffect,useRef}from 'react'
import {api}from '../api'

// logged-in users get history; guests cannot
export default function AIAssistant(){

const[messages,setMessages]=useState([])
const[input, setInput]=useState('')
const[loading, setLoading]=useState(false)
  const [isAuth, setIsAuth] = useState(null)
// this one will scroll chat to bottom after each msg
  const chatEndRef=useRef(null)

  // fetch chat hist if loggin
  useEffect(()=>{
    api('/me', 'GET')

      .then(()=>{
        setIsAuth(true)     
        fetchHistory() 
      })
      .catch(()=>setIsAuth(false))
        },[])
  // if messages update, scroll to bottom
  useEffect(()=>{
    chatEndRef.current?.scrollIntoView({ behavior:'smooth'})// browser animates the scroll
  }, [messages])

  // Load message history from backend (only for logged-in users)
  const fetchHistory=async()=>{
    setLoading(true)
    try {
      const res=await api('/ai/history', 'GET')
    
      setMessages(res.history.map(m=>({
        sender: m.role === 'user'?'user':'assistant',
        text: m.content
      })))
    } catch (e) {
      console.log('fail history') // maybe api is down or session expired
      //forgot to export ds api caused the site crash
    }
    setLoading(false)

  }

  const clearHistory=async()=>{
    if (!window.confirm('Clear all?')) return
    await api('/ai/history/clear', 'POST')
    setMessages([])  // wipe local messages as weell
  }

//send suer api to backend
//多用 try catch！
  const sendMessage=async()=>{
    const text = input.trim()
    setMessages(msgs =>[...msgs,{ sender:'user',text}])
    setInput('')
    setLoading(true)
    
    try{
      const res=await api('/ai/suggest', 'POST', { message:text})

      setMessages(msgs=>[...msgs,{sender:'assistant',text:res.reply||'No reply'}])
    }catch (e) {
      setMessages(msgs=> [...msgs, {sender:'assistant',text:'Err.'}])
    }
    setLoading(false)
  }

  return (
    <div className="card h-100 d-flex flex-column">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">AI Assistant</h5>
        <div className="btn-group">
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={fetchHistory}
            disabled={loading}
          >
            {loading ? 'Loading…':'Reload'}
          </button>
          <button
            className="btn btn-outline-danger btn-sm"
            onClick={clearHistory}
            disabled= {loading}
          >
            Clear
          </button>
        </div>
      </div>
      <div className="card-body overflow-auto" style={{ flexGrow: 1, maxHeight: 500 }}>
        {/* remind user if not logged in */}
        {isAuth===false&&!loading && (
          <p className="text-center text-muted">Not logged in.</p >
        )}
      
        {messages.map((m, i)=>(
          <div
            key={i}
            className={`d-flex mb-2 ${m.sender==='user'?'justify-content-end':'justify-content-start'}`}
          >
            <div
              className={`p-2 rounded ${m.sender ==='user'?'bg-primary text-white':'bg-light text-dark'}`}
              style={{ maxWidth: '70%' }}
            >
              <small className="d-block text-muted mb-1">{m.sender==='user'?'You':'Assistant'}</small>
              <div>{m.text}</div>
            </div>
          </div>
        ))}

        {loading && <p className="text-center text-muted">Loading…</p >}
        <div ref={chatEndRef} />
      </div>
      {/* new msg here */}
      <div className="card-footer">
        <div className="input-group">
        <textarea
            className="form-control"
            rows={2}
            placeholder="Type here…"
            value={input}
            onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{
              if (e.key==='Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >


            {loading ? 'Sending…' : 'Send'}
          </button>
        </div>
      </div>
     </div>
  )
}
