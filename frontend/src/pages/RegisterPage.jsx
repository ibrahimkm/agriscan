import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Leaf, Lock, Mail, User as UserIcon, MapPin, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const RegisterPage = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
    farmName: '',
    region: 'Punjab, India',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const res = await register({
      name: formData.name,
      email: formData.email,
      phone: formData.phone,
      password: formData.password,
      location: {
        farmName: formData.farmName || 'Green Valley Farm',
        region: formData.region,
      },
    });

    setLoading(false);

    if (res?.success) {
      navigate('/home');
    } else {
      setError(res?.message || 'Registration failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col justify-center p-6 max-w-md mx-auto select-none">
      <div className="text-center space-y-2 mb-6">
        <div className="w-14 h-14 rounded-2xl bg-[#14382B] text-white flex items-center justify-center mx-auto shadow-md ring-4 ring-[#E8F5E9]">
          <Leaf className="w-7 h-7 stroke-[2]" />
        </div>
        <h1 className="text-xl md:text-2xl font-bold text-[#14382B]">Create AgriScan Account</h1>
        <p className="text-xs text-[#6B7280]">
          Join thousands of farmers protecting their harvest with AI
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs space-y-3.5">
        {error && (
          <div className="p-3 rounded-xl bg-[#FEE2E2] text-[#B91C1C] text-xs font-semibold">
            {error}
          </div>
        )}

        <div className="space-y-1">
          <label className="text-xs font-bold text-[#14382B]">Full Name</label>
          <div className="relative">
            <UserIcon className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
            <input
              type="text"
              required
              placeholder="e.g. Ravi Sharma"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full bg-[#FAF8F5] border border-[#EAE5DE] focus:border-[#14382B] rounded-2xl pl-10 pr-4 py-2 text-xs md:text-sm text-[#1F2937] outline-none"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-[#14382B]">Email</label>
          <div className="relative">
            <Mail className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
            <input
              type="email"
              required
              placeholder="farmer@domain.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full bg-[#FAF8F5] border border-[#EAE5DE] focus:border-[#14382B] rounded-2xl pl-10 pr-4 py-2 text-xs md:text-sm text-[#1F2937] outline-none"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-[#14382B]">Farm Name</label>
          <div className="relative">
            <MapPin className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
            <input
              type="text"
              placeholder="e.g. Surya Agro Farms"
              value={formData.farmName}
              onChange={(e) => setFormData({ ...formData, farmName: e.target.value })}
              className="w-full bg-[#FAF8F5] border border-[#EAE5DE] focus:border-[#14382B] rounded-2xl pl-10 pr-4 py-2 text-xs md:text-sm text-[#1F2937] outline-none"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-[#14382B]">Password</label>
          <div className="relative">
            <Lock className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
            <input
              type="password"
              required
              placeholder="••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full bg-[#FAF8F5] border border-[#EAE5DE] focus:border-[#14382B] rounded-2xl pl-10 pr-4 py-2 text-xs md:text-sm text-[#1F2937] outline-none"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 rounded-2xl bg-[#14382B] text-white font-bold text-xs md:text-sm shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
        >
          <span>{loading ? 'Registering...' : 'Create Account'}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <div className="pt-2 text-center text-xs text-[#6B7280]">
          <span>Already have an account? </span>
          <Link to="/login" className="font-bold text-[#14382B] hover:underline">
            Sign in
          </Link>
        </div>
      </form>
    </div>
  );
};

export default RegisterPage;
