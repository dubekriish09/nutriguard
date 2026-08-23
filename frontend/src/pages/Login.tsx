import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/services';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);
      const res = await authApi.login(params);
      localStorage.setItem('ng_token', res.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError('Invalid credentials or network error.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={handleLogin} className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 max-w-sm w-full">
        <h1 className="text-2xl font-bold text-slate-900 mb-6 text-center">NutriGuard</h1>
        {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg mb-4 text-sm">{error}</div>}
        <input 
          type="email" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          placeholder="Email (e.g. user@nutriguard.com)" 
          className="w-full mb-4 px-4 py-2.5 border rounded-xl"
          required 
        />
        <input 
          type="password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          placeholder="Password" 
          className="w-full mb-6 px-4 py-2.5 border rounded-xl"
          required 
        />
        <button type="submit" className="w-full bg-green-600 text-white rounded-xl py-2.5 font-medium hover:bg-green-700 transition">
          Sign In
        </button>
      </form>
    </div>
  );
}
