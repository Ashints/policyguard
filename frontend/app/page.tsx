"use client";

import {useEffect, useState } from "react";

type Source = {
  article: string;
  file: string;
};

export default function Home() {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState("");
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    setAccessToken(token);
  }, []);

  const handleSubmit = async () => {
    if (!question.trim()) return;

     if (!accessToken) {
      setError("You must be logged in to ask questions.");
      return;
    }
    
    setIsLoading(true);
    setError("");
    setAnswer("");
    setSources([]);

    try {
      const response = await fetch(
        process.env.NEXT_PUBLIC_API_URL as string,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`,

          },
          body: JSON.stringify({ question }),
        }
      );

      if (!response.ok) {
        throw new Error("Request failed");
      }

      const data = await response.json();
      const fullAnswer = data.answer;

      setIsTyping(true);
      let currentText = "";
      
      for (let i = 0; i < fullAnswer.length; i++) {
        currentText += fullAnswer[i];
        setAnswer(currentText);
        await new Promise((resolve) => setTimeout(resolve, 5));
      }

      setSources(data.sources || []);
    } catch (err) {
      setError("Failed to retrieve answer. Please try again.");
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col bg-gradient-to-r from-blue-800 to-purple-800">
      {/* Header */}
      <div className=" p-6 border-b border-gray-200 bg-black w-full fixed top-0 left-0 w-full z-10 ">
        <h1 className="text-3xl font-bold text-center text-white-800">PolicyGuard</h1>
      </div>

      {/* Content Area - Scrollable */}
      <div className="flex-1 overflow-y-auto p-4 pb-32 mt-24">
        <div className="max-w-2xl mx-auto space-y-6">
          {error && (
            <p className="text-red-600 text-sm bg-red-50 p-3 rounded">{error}</p>
          )}

          {answer && (
            <div className="border border-gray-200 rounded-lg p-5 space-y-4 bg-white animate-in fade-in duration-500">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-2">Answer</h2>
                <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                  {answer}
                  {(isLoading || isTyping) && <span className="cursor-blink" />}
                </p>
              </div>

              {sources.length > 0 && !isTyping && (
                <div className="pt-4 border-t border-gray-100">
                  <h3 className="text-sm font-semibold text-gray-500 mb-2">Sources</h3>
                  <ul className="grid grid-cols-1 gap-2">
                    {sources.map((s, idx) => (
                      <li key={idx} className="text-xs bg-gray-100 p-2 rounded text-gray-600">
                        <span className="font-bold">{s.article}</span> — {s.file}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Area - Fixed at Bottom */}
      <div className="fixed bottom-0 left-0 right-0 bg-black border-t border-white-200 shadow-lg ">
        <div className="max-w-2xl mx-auto p-4 space-y-2">
          <input
            type="text"
            placeholder="Ask a GDPR question..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-black outline-none transition-all text-white"
          />

          <button
            onClick={handleSubmit}
            disabled={isLoading || isTyping}
            className="cursor-pointer w-full bg-black text-white rounded-lg p-3 font-medium transition-all hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Consulting GDPR..." : isTyping ? "Typing..." : "Ask Question"}
          </button>
        </div>
      </div>

      <style jsx>{`
        .cursor-blink {
          display: inline-block;
          width: 8px;
          height: 18px;
          background-color: #000;
          margin-left: 4px;
          vertical-align: middle;
          animation: blink 1s step-end infinite;
        }

        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </main>
  );
}