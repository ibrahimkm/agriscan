import React, { useState } from 'react';
import { Send, Bot, User, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';

export const QAChatThread = ({ qaThread = [], onAskQuestion, loading = false, cropName = 'Tomato' }) => {
  const [inputQuery, setInputQuery] = useState('');

  const samplePrompts = [
    'How quickly will this spread to adjacent crops?',
    'What fungicide dosage is safest right now?',
    'Are healthy-looking fruits safe to harvest?',
    'Should I prune affected branches immediately?',
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || loading) return;
    onAskQuestion(inputQuery.trim());
    setInputQuery('');
  };

  const handleQuickPrompt = (prompt) => {
    if (loading) return;
    onAskQuestion(prompt);
  };

  return (
    <div className="space-y-4">
      {/* Quick Suggestion Chips */}
      <div>
        <p className="text-xs font-semibold text-[#6B7280] mb-2 flex items-center space-x-1">
          <Sparkles className="w-3.5 h-3.5 text-[#D4A373]" />
          <span>Recommended Agronomist Inquiries:</span>
        </p>
        <div className="flex flex-wrap gap-1.5">
          {samplePrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleQuickPrompt(prompt)}
              disabled={loading}
              className="text-xs text-[#14382B] bg-[#FAF8F5] hover:bg-[#EAE5DE] border border-[#EAE5DE] px-3 py-1.5 rounded-full font-medium transition-colors text-left"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Message Thread */}
      <div className="space-y-3 pt-2">
        {qaThread.map((item, idx) => (
          <div key={idx} className="space-y-2">
            {/* User Question */}
            <div className="flex items-start justify-end space-x-2">
              <div className="bg-[#14382B] text-white p-3 rounded-2xl rounded-tr-xs text-xs md:text-sm max-w-[85%] shadow-xs">
                {item.question}
              </div>
              <div className="w-6 h-6 rounded-full bg-[#1B4332] text-white flex items-center justify-center shrink-0 mt-1">
                <User className="w-3.5 h-3.5" />
              </div>
            </div>

            {/* AI Agronomist Answer */}
            <div className="flex items-start space-x-2">
              <div className="w-6 h-6 rounded-full bg-[#2D6A4F] text-white flex items-center justify-center shrink-0 mt-1 shadow-xs">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="bg-white border border-[#EAE5DE] p-3.5 rounded-2xl rounded-tl-xs text-xs md:text-sm text-[#1F2937] max-w-[90%] shadow-xs space-y-2">
                <p className="leading-relaxed">{item.answer}</p>

                {item.suggestedActions && item.suggestedActions.length > 0 && (
                  <div className="pt-2 border-t border-[#F3F4F6] space-y-1">
                    <p className="text-[11px] font-bold text-[#14382B] uppercase tracking-wider">
                      Prescribed Action Checklist:
                    </p>
                    {item.suggestedActions.map((act, aIdx) => (
                      <div key={aIdx} className="flex items-start space-x-1.5 text-xs text-[#374151]">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#22C55E] shrink-0 mt-0.5" />
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-full bg-[#2D6A4F] text-white flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-white border border-[#EAE5DE] px-4 py-2.5 rounded-2xl text-xs text-[#6B7280] flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#2D6A4F] animate-ping" />
              <span>Analyzing pathology data & generating agronomic response...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSubmit} className="relative pt-2">
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder={`Ask a question about this ${cropName} detection...`}
          disabled={loading}
          className="w-full bg-white border border-[#D4A373]/60 focus:border-[#14382B] focus:ring-2 focus:ring-[#14382B]/10 rounded-2xl pl-4 pr-12 py-3 text-xs md:text-sm text-[#1F2937] placeholder-[#9CA3AF] transition-all outline-none shadow-xs"
        />
        <button
          type="submit"
          disabled={!inputQuery.trim() || loading}
          className="absolute right-2 top-3.5 p-2 bg-[#14382B] text-white rounded-xl disabled:opacity-40 hover:bg-[#1B4332] transition-colors shadow-xs"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};

export default QAChatThread;
