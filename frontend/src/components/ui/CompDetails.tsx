import React from 'react'

interface CompDetailsProps {
  top_comps: Array<{
    address_masked: string
    sale_date: string
    adjusted_cap_rate: number
    weight: number
    distance_mi: number
  }>
  methodology: string
}

export default function CompDetails({ top_comps, methodology }: CompDetailsProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Supporting Comparables</h3>
        <p className="text-sm text-gray-500 mt-1">
          Top 5 weighted comps used in {methodology} calculation
        </p>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Address
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sale Date
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cap Rate
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Weight
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Distance
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {top_comps.map((comp, index) => (
              <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="px-4 py-2 text-sm text-gray-900 font-medium">
                  {comp.address_masked}
                </td>
                <td className="px-4 py-2 text-sm text-gray-600">
                  {new Date(comp.sale_date).toLocaleDateString()}
                </td>
                <td className="px-4 py-2 text-sm text-gray-900">
                  {comp.adjusted_cap_rate.toFixed(2)}%
                </td>
                <td className="px-4 py-2 text-sm text-gray-600">
                  <div className="flex items-center">
                    <div 
                      className="h-2 bg-blue-500 rounded mr-2" 
                      style={{ width: `${Math.min(comp.weight * 50, 100)}px` }}
                    ></div>
                    {comp.weight.toFixed(2)}
                  </div>
                </td>
                <td className="px-4 py-2 text-sm text-gray-600">
                  {comp.distance_mi.toFixed(1)} mi
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
        <p>
          <strong>Methodology:</strong> {methodology} - Weights based on recency (12m half-life), 
          distance (15mi decay), and size similarity (log-normal kernel).
        </p>
        <p className="mt-1">
          Addresses are masked for privacy while maintaining audit trail for internal review.
        </p>
      </div>
    </div>
  )
}
