import React, { useState } from 'react';
import { PhoneCall, Play, Pause, RotateCcw, AlertTriangle, ShieldCheck, CheckCircle } from 'lucide-react';

export const SimulatedLiveCall: React.FC = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStep, setCurrentStep] = useState(2);

  const turns = [
    { speaker: 'Caller', text: 'Main CBI Cyber Crime cell se Inspector Verma bol raha hoon.', stage: 'AUTHORITY' },
    { speaker: 'Caller', text: 'Aapke Aadhaar number par Mumbai Airport se contraband parcel seize hua hai.', stage: 'ALLEGATION' },
    { speaker: 'Caller', text: 'Yeh serious non-bailable offense hai. Supreme Court se arrest warrant issue ho chuka hai.', stage: 'THREAT' },
    { speaker: 'Caller', text: 'Aap kisi ko phone nahi karenge, room band kijiye aur skype video par aaiye.', stage: 'ISOLATION' },
    { speaker: 'Caller', text: 'Aapko abhi turant 30 minute ke andar verification amount deposit karni hogi.', stage: 'URGENCY' },
    { speaker: 'Caller', text: 'Transfer 50,000 INR to UPI handle verify-court@sbi or police team is en route.', stage: 'DEMAND' }
  ];

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      {/* Simulation Disclaimer Banner (§10, §12.4) */}
      <div className="bg-risk-high/10 border-2 border-risk-high/40 rounded-lg p-4 flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 text-risk-high shrink-0" />
        <div className="text-xs text-text-primary font-medium">
          <strong>SIMULATION NOTICE:</strong> This is a scripted transcript playback demonstration. VIGIL does <span className="underline font-bold">NOT</span> intercept, tap, or listen to real-world telephone calls.
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Simulated Live Call Analysis</h1>
          <p className="text-sm text-text-secondary mt-1">
            Progressive conversational stream inspection, stage tracking, and immediate protective guidance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-2 bg-accent-primary text-bg-main font-semibold px-4 py-2 rounded-md text-xs transition-colors"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{isPlaying ? 'Pause' : 'Play Script'}</span>
          </button>
          <button
            onClick={() => setCurrentStep(0)}
            className="p-2 bg-bg-card hover:bg-bg-elevated border border-border-subtle rounded-md text-text-secondary transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stage Tracker Chips */}
      <div className="bg-bg-card border border-border-subtle rounded-lg p-4 space-y-2">
        <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Live Stage Tracker (§6.6)
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
          {['AUTHORITY', 'ALLEGATION', 'THREAT', 'ISOLATION', 'URGENCY', 'DEMAND'].map((stg, idx) => {
            const active = idx <= currentStep;
            return (
              <div
                key={stg}
                className={`p-3 rounded-md border text-center text-xs font-mono transition-all ${
                  active 
                    ? 'bg-accent-primary/20 border-accent-primary text-accent-primary font-bold shadow-sm' 
                    : 'bg-bg-main border-border-subtle text-text-muted opacity-40'
                }`}
              >
                <div>Stage {idx + 1}</div>
                <div className="text-[11px] mt-0.5">{stg}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Layout: Transcript Feed & Real-Time Guidance */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Transcript Streaming */}
        <div className="lg:col-span-8 bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
          <h3 className="text-sm font-semibold text-text-primary">Transcript Stream</h3>
          <div className="space-y-3 font-mono text-xs">
            {turns.slice(0, currentStep + 1).map((turn, idx) => (
              <div key={idx} className="bg-bg-main p-3.5 rounded border border-border-subtle space-y-1">
                <div className="flex justify-between items-center text-[10px] text-text-muted">
                  <span className="font-bold text-accent-primary">{turn.speaker}</span>
                  <span className="bg-bg-elevated px-1.5 py-0.5 rounded text-accent-secondary">
                    {turn.stage}
                  </span>
                </div>
                <p className="text-text-primary text-sm font-sans">{turn.text}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Protective Guidance Card */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-bg-card border border-border-subtle rounded-lg p-5 space-y-3">
            <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Protective Guidance (EN & HI)
            </div>
            <div className="bg-risk-high/15 border border-risk-high/30 p-4 rounded-lg space-y-2">
              <div className="text-xs font-bold text-risk-high uppercase font-mono">
                High Risk Impersonation Pattern Detected
              </div>
              <p className="text-xs text-text-primary leading-relaxed">
                <strong>English:</strong> Law enforcement never conducts "digital arrests" or demands verification fees over video call. Hang up immediately.
              </p>
              <p className="text-xs text-text-secondary leading-relaxed pt-1 border-t border-risk-high/20">
                <strong>हिंदी:</strong> पुलिस या सीबीआई कभी भी वीडियो कॉल पर गिरफ़्तारी या पैसे की माँग नहीं करती। तुरंत कॉल काटें और 1930 पर शिकायत दर्ज करें।
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
