import React, { useState } from 'react';

interface FeedbackWidgetProps {
  className?: string;
}

export default function FeedbackWidget({ className }: FeedbackWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    type: 'general',
    message: '',
    email: '',
    url: typeof window !== 'undefined' ? window.location.href : '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          url: window.location.href,
          user_agent: navigator.userAgent,
        }),
      });

      if (response.ok) {
        setIsSubmitted(true);
        setTimeout(() => {
          setIsOpen(false);
          setIsSubmitted(false);
          setFormData({
            type: 'general',
            message: '',
            email: '',
            url: window.location.href,
          });
        }, 2000);
      } else {
        throw new Error('Failed to submit feedback');
      }
    } catch (error) {
      console.error('Feedback submission error:', error);
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  if (isSubmitted) {
    return (
      <div className={`fixed right-4 bottom-4 z-50 ${className || ''}`}>
        <div className="bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3">
          <div className="w-5 h-5 rounded-full bg-green-400 flex items-center justify-center">
            <div className="w-2 h-2 bg-white rounded-full"></div>
          </div>
          <span className="font-medium">Thanks for your feedback!</span>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Feedback Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className={`fixed right-4 bottom-4 z-50 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg shadow-lg transition-colors font-medium ${className || ''}`}
          aria-label="Open feedback form"
        >
          💬 Feedback
        </button>
      )}

      {/* Slide-over Panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
          {/* Background overlay */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setIsOpen(false)}></div>
            
            <div className="fixed inset-y-0 right-0 pl-10 max-w-full flex">
              <div className="w-screen max-w-md">
                <div className="h-full flex flex-col bg-white shadow-xl">
                  {/* Header */}
                  <div className="px-4 py-6 bg-blue-600 sm:px-6">
                    <div className="flex items-center justify-between">
                      <h2 className="text-lg font-medium text-white" id="slide-over-title">
                        Send Feedback
                      </h2>
                      <button
                        type="button"
                        className="text-blue-200 hover:text-white transition-colors"
                        onClick={() => setIsOpen(false)}
                        aria-label="Close feedback form"
                      >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <div className="mt-1">
                      <p className="text-sm text-blue-100">
                        Help us improve CapSight. Your feedback is valuable!
                      </p>
                    </div>
                  </div>

                  {/* Form */}
                  <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
                    <div className="flex-1 px-4 py-6 sm:px-6 space-y-6 overflow-y-auto">
                      {/* Feedback Type */}
                      <div>
                        <label htmlFor="feedback-type" className="block text-sm font-medium text-gray-700 mb-2">
                          What type of feedback?
                        </label>
                        <select
                          id="feedback-type"
                          name="type"
                          value={formData.type}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="general">General Feedback</option>
                          <option value="bug">Bug Report</option>
                          <option value="feature">Feature Request</option>
                          <option value="accuracy">Valuation Accuracy</option>
                          <option value="ui">User Interface</option>
                          <option value="performance">Performance Issue</option>
                        </select>
                      </div>

                      {/* Message */}
                      <div>
                        <label htmlFor="feedback-message" className="block text-sm font-medium text-gray-700 mb-2">
                          Your feedback <span className="text-red-500">*</span>
                        </label>
                        <textarea
                          id="feedback-message"
                          name="message"
                          value={formData.message}
                          onChange={handleInputChange}
                          required
                          rows={6}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 resize-none"
                          placeholder="Tell us what you think, what's not working, or what we could improve..."
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          {formData.message.length}/1000 characters
                        </p>
                      </div>

                      {/* Email (optional) */}
                      <div>
                        <label htmlFor="feedback-email" className="block text-sm font-medium text-gray-700 mb-2">
                          Email (optional)
                        </label>
                        <input
                          type="email"
                          id="feedback-email"
                          name="email"
                          value={formData.email}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                          placeholder="your.email@example.com"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Provide your email if you'd like a response
                        </p>
                      </div>

                      {/* Context Info */}
                      <div className="bg-gray-50 px-3 py-2 rounded-md">
                        <p className="text-xs text-gray-600 mb-1">
                          <strong>Context included:</strong>
                        </p>
                        <ul className="text-xs text-gray-500 space-y-0.5">
                          <li>• Current page: {typeof window !== 'undefined' ? window.location.pathname : '/'}</li>
                          <li>• Timestamp: {new Date().toISOString()}</li>
                          <li>• User agent (browser info)</li>
                        </ul>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="px-4 py-4 sm:px-6 border-t border-gray-200 bg-gray-50">
                      <div className="flex justify-end space-x-3">
                        <button
                          type="button"
                          onClick={() => setIsOpen(false)}
                          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={isSubmitting || !formData.message.trim()}
                          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isSubmitting ? (
                            <>
                              <div className="inline-block w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                              Sending...
                            </>
                          ) : (
                            'Send Feedback'
                          )}
                        </button>
                      </div>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
