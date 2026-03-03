import React, { useEffect, useState } from 'react';

interface SessionInfo {
  valid: boolean;
  status: string;
  time_remaining_minutes: number | null;
  grace_remaining_minutes?: number;
}

export const SessionWarning: React.FC = () => {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch('/api/session/status');
        const data = await response.json();
        setSession(data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to check session:', error);
        setLoading(false);
      }
    };

    checkSession();
    const interval = setInterval(checkSession, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  if (loading || !session) {
    return null;
  }

  if (!session.valid && session.status === 'grace_period') {
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              ⏱️ Your session expired. You have <strong>{session.grace_remaining_minutes} minutes</strong> to refresh it before positions are paused.
              <button 
                onClick={() => {
                  fetch('/api/session/refresh', { method: 'POST' });
                  window.location.reload();
                }}
                className="ml-2 font-medium underline hover:text-yellow-900"
              >
                Refresh Now
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!session.valid && session.status === 'grace_period_ended') {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-red-700">
              🔴 Session expired and grace period ended. Bot positions have been paused to protect your account. Please login to resume trading.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Show warning if less than 1 hour remaining
  if (session.valid && session.time_remaining_minutes && session.time_remaining_minutes < 60) {
    return (
      <div className="bg-orange-50 border-l-4 border-orange-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-orange-700">
              ⏰ Your session expires in <strong>{session.time_remaining_minutes} minutes</strong>.
              <button 
                onClick={() => {
                  fetch('/api/session/refresh', { method: 'POST' });
                  window.location.reload();
                }}
                className="ml-2 font-medium underline hover:text-orange-900"
              >
                Extend Session
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default SessionWarning;
