import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Leaf, Lock, Mail, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';

export const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const { t } = useLanguage();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const from = location.state?.from?.pathname || '/home';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const res = await login(email, password);
    setLoading(false);

    if (res?.success) {
      navigate(from, { replace: true });
    } else {
      setError(res?.message || 'Invalid email or password');
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col justify-center p-4 md:p-6 max-w-md mx-auto select-none">
      {/* Brand Header */}
      <div className="text-center space-y-2 mb-6">
        <div className="w-16 h-16 rounded-3xl bg-[#14382B] text-white flex items-center justify-center mx-auto shadow-lg ring-8 ring-[#E8F5E9]/70">
          <Leaf className="w-8 h-8 stroke-[2]" />
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-[#14382B] tracking-tight">
          {t('farmerSignIn')}
        </h1>
        <p className="text-xs text-[#6B7280]">
          {t('signInSub')}
        </p>
      </div>

      {/* Clean Custom Login Form (Account suggestions removed) */}
      <form onSubmit={handleSubmit} className="bg-white border border-[#EAE5DE] rounded-3xl p-6 shadow-xs space-y-4">
        {error && (
          <div className="p-3 rounded-xl bg-[#FEE2E2] text-[#B91C1C] text-xs font-semibold">
            {error}
          </div>
        )}

        <div className="space-y-1">
          <label className="text-xs font-bold text-[#14382B]">{t('email')}</label>
          <div className="relative">
            <Mail className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="farmer@agriscan.io"
              className="w-full bg-[#FAF8F5] border border-[#EAE5DE] focus:border-[#14382B] rounded-2xl pl-10 pr-4 py-2.5 text-xs md:text-sm text-[#1F2937] outline-none"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-[#14382B]">{t('password')}</label>
          <div className="relative">
            <Lock className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full bg-[#FAF8F5] border border-[#EAE5DE] focus:border-[#14382B] rounded-2xl pl-10 pr-4 py-2.5 text-xs md:text-sm text-[#1F2937] outline-none"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 rounded-2xl bg-[#14382B] text-white font-bold text-xs md:text-sm shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
        >
          <span>{loading ? t('syncing') : t('signInBtn')}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <div className="pt-2 text-center text-xs text-[#6B7280]">
          <span>{t('newFarmer')} </span>
          <Link to="/register" className="font-bold text-[#14382B] hover:underline">
            {t('createAccount')}
          </Link>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
