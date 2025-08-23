import React from 'react';

interface FeedbackTableProps {
  feedback: Array<{
    id: string;
    type: string;
    message: string;
    email?: string;
    url?: string;
    user_agent?: string;
    ip_address?: string;
    created_at: string;
    status: 'new' | 'reviewed' | 'resolved' | 'closed';
  }>;
  onStatusUpdate: (id: string, status: string) => Promise<void>;
}

const typeColors = {
  general: 'bg-blue-100 text-blue-800',
  bug: 'bg-red-100 text-red-800',
  feature: 'bg-green-100 text-green-800',
  accuracy: 'bg-yellow-100 text-yellow-800',
  ui: 'bg-purple-100 text-purple-800',
  performance: 'bg-orange-100 text-orange-800',
};

const statusColors = {
  new: 'bg-gray-100 text-gray-800',
  reviewed: 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-red-100 text-red-800',
};

export default function FeedbackTable({ feedback, onStatusUpdate }: FeedbackTableProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const createGitHubIssue = (item: FeedbackTableProps['feedback'][0]) => {
    const title = `[${item.type.toUpperCase()}] ${item.message.slice(0, 50)}${item.message.length > 50 ? '...' : ''}`;
    const body = `**Feedback Type:** ${item.type}

**Message:**
${item.message}

**Context:**
- **URL:** ${item.url || 'Not provided'}
- **User Agent:** ${item.user_agent || 'Not provided'}
- **Email:** ${item.email || 'Not provided'}
- **IP Address:** ${item.ip_address || 'Not provided'}
- **Submitted:** ${formatDate(item.created_at)}
- **Feedback ID:** ${item.id}

---
*This issue was automatically created from user feedback.*`;

    const encodedTitle = encodeURIComponent(title);
    const encodedBody = encodeURIComponent(body);
    const labels = `feedback,${item.type}`;
    
    const gitHubUrl = `https://github.com/your-org/capsight/issues/new?title=${encodedTitle}&body=${encodedBody}&labels=${labels}`;
    
    window.open(gitHubUrl, '_blank');
  };

  if (feedback.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10m0 0V6a2 2 0 00-2-2H9a2 2 0 00-2 2v2m0 0v10a2 2 0 002 2h6a2 2 0 002-2V8M7 8v10a2 2 0 002 2h6a2 2 0 002-2V8" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No feedback yet</h3>
        <p className="text-gray-500">User feedback will appear here once submitted.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
      <table className="min-w-full divide-y divide-gray-300">
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type & Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Message
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Contact
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Context
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {feedback.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="space-y-1">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${typeColors[item.type as keyof typeof typeColors] || 'bg-gray-100 text-gray-800'}`}>
                    {item.type}
                  </span>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusColors[item.status as keyof typeof statusColors]}`}>
                    {item.status}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="text-sm text-gray-900">
                  <p className="line-clamp-3 max-w-md">
                    {item.message}
                  </p>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {item.email ? (
                  <a href={`mailto:${item.email}`} className="text-blue-600 hover:text-blue-800">
                    {item.email}
                  </a>
                ) : (
                  <span className="text-gray-400">No email</span>
                )}
              </td>
              <td className="px-6 py-4 text-sm text-gray-500">
                <div className="space-y-1">
                  {item.url && (
                    <div>
                      <span className="font-medium">Page:</span>{' '}
                      <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 truncate block max-w-xs">
                        {new URL(item.url).pathname}
                      </a>
                    </div>
                  )}
                  {item.ip_address && (
                    <div>
                      <span className="font-medium">IP:</span> {item.ip_address}
                    </div>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(item.created_at)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm space-y-2">
                <div className="space-y-1">
                  <select
                    value={item.status}
                    onChange={(e) => onStatusUpdate(item.id, e.target.value)}
                    className="block w-full text-xs border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="new">New</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </select>
                  <button
                    onClick={() => createGitHubIssue(item)}
                    className="w-full px-2 py-1 text-xs bg-gray-800 text-white rounded hover:bg-gray-700 transition-colors"
                  >
                    Create Issue
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
